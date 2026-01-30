"""Conversation agent for Rohlik Voice Assistant."""

from __future__ import annotations

import json
import logging
from typing import Any, Literal

import aiohttp

from homeassistant.components import conversation
from homeassistant.components.conversation import ConversationInput, ConversationResult
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid

from .const import DOMAIN, CONF_OPENAI_API_KEY, OPENAI_CHAT_URL, OPENAI_CHAT_MODEL
from .mcp_client import RohlikMCPClient
from .tools import ROHLIK_TOOLS, SYSTEM_PROMPT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Rohlik Voice conversation agent."""
    agent = RohlikConversationAgent(hass, config_entry)
    async_add_entities([agent])


class RohlikConversationAgent(conversation.ConversationEntity):
    """Rohlik Voice Conversation Agent."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the agent."""
        self.hass = hass
        self.config_entry = config_entry
        self._attr_unique_id = f"{config_entry.entry_id}_conversation"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, config_entry.entry_id)},
            "name": "Rohlik Voice Assistant",
            "manufacturer": "Rohlik.cz",
            "model": "Voice Shopping Assistant",
        }
        self._conversation_history: dict[str, list[dict]] = {}

    @property
    def supported_languages(self) -> list[str] | Literal["*"]:
        """Return supported languages."""
        return ["cs", "sk", "en"]

    async def async_process(
        self, user_input: ConversationInput
    ) -> ConversationResult:
        """Process a conversation turn."""
        _LOGGER.debug("Processing input: %s", user_input.text)

        # Get MCP client and API key from hass.data
        data = self.hass.data[DOMAIN][self.config_entry.entry_id]
        mcp_client: RohlikMCPClient = data["mcp_client"]
        api_key: str = data["openai_api_key"]

        # Get or create conversation history
        conversation_id = user_input.conversation_id or ulid.ulid()
        if conversation_id not in self._conversation_history:
            self._conversation_history[conversation_id] = []

        history = self._conversation_history[conversation_id]

        # Build messages for OpenAI
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_input.text})

        try:
            # Call OpenAI with function calling
            response_text = await self._call_openai(
                api_key, messages, mcp_client
            )

            # Update history
            history.append({"role": "user", "content": user_input.text})
            history.append({"role": "assistant", "content": response_text})

            # Keep history limited to last 10 exchanges
            if len(history) > 20:
                history[:] = history[-20:]

            # Return result
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_speech(response_text)

            return ConversationResult(
                response=intent_response,
                conversation_id=conversation_id,
            )

        except Exception as err:
            _LOGGER.error("Error processing conversation: %s", err)
            intent_response = intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                intent.IntentResponseErrorCode.UNKNOWN,
                f"Omlouvám se, došlo k chybě: {err}",
            )
            return ConversationResult(
                response=intent_response,
                conversation_id=conversation_id,
            )

    async def _call_openai(
        self,
        api_key: str,
        messages: list[dict],
        mcp_client: RohlikMCPClient,
    ) -> str:
        """Call OpenAI Chat API with function calling."""
        
        # Convert tools to OpenAI format
        tools = []
        for tool in ROHLIK_TOOLS:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            })

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": OPENAI_CHAT_MODEL,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENAI_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")

                result = await response.json()

        # Process response
        choice = result["choices"][0]
        message = choice["message"]

        # Check if there are tool calls
        if "tool_calls" in message and message["tool_calls"]:
            # Execute tool calls
            tool_results = []
            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])

                _LOGGER.info("Executing tool: %s with args: %s", function_name, function_args)

                # Execute the function
                tool_result = await self._execute_function(
                    mcp_client, function_name, function_args
                )

                tool_results.append({
                    "tool_call_id": tool_call["id"],
                    "role": "tool",
                    "content": json.dumps(tool_result, ensure_ascii=False),
                })

            # Add assistant message with tool calls and tool results
            messages.append(message)
            messages.extend(tool_results)

            # Call OpenAI again to get final response
            payload["messages"] = messages
            del payload["tools"]
            del payload["tool_choice"]

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    OPENAI_CHAT_URL,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"OpenAI API error: {response.status} - {error_text}")

                    result = await response.json()

            return result["choices"][0]["message"]["content"]

        # No tool calls, return direct response
        return message.get("content", "Omlouvám se, nemám odpověď.")

    async def _execute_function(
        self,
        mcp_client: RohlikMCPClient,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a function and return the result."""
        try:
            if name == "search_products":
                return await mcp_client.search_products(
                    keyword=arguments.get("keyword", ""),
                )
            elif name == "add_to_cart":
                return await mcp_client.add_to_cart(
                    product_id=int(arguments.get("product_id", 0)),
                    quantity=int(arguments.get("quantity", 1)),
                )
            elif name == "get_cart":
                return await mcp_client.get_cart()
            elif name == "remove_from_cart":
                return await mcp_client.remove_from_cart(
                    product_id=int(arguments.get("product_id", 0)),
                )
            elif name == "update_cart_item":
                return await mcp_client.update_cart_item(
                    product_id=int(arguments.get("product_id", 0)),
                    quantity=int(arguments.get("quantity", 0)),
                )
            elif name == "clear_cart":
                return await mcp_client.clear_cart()
            else:
                return {"error": f"Neznámá funkce: {name}"}
        except Exception as err:
            _LOGGER.error("Error executing function %s: %s", name, err)
            return {"error": str(err)}

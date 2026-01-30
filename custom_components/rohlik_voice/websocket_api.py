"""WebSocket API for Rohlik Voice Assistant."""

import asyncio
import logging
from typing import Any

from aiohttp import web
import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, WS_PATH
from .mcp_client import RohlikMCPClient
from .realtime_api import RealtimeAPIHandler

_LOGGER = logging.getLogger(__name__)


class RohlikVoiceWebSocketView(HomeAssistantView):
    """WebSocket view for audio streaming."""

    url = WS_PATH
    name = "api:rohlik_voice:ws"
    # TODO: Re-enable auth with proper token handling
    # For now, disabled for local network testing
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the WebSocket view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.WebSocketResponse:
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        # Get the integration data
        entry_id = list(self.hass.data[DOMAIN].keys())[0]
        data = self.hass.data[DOMAIN][entry_id]
        
        mcp_client: RohlikMCPClient = data["mcp_client"]
        api_key: str = data["openai_api_key"]

        # Audio buffer for collecting chunks
        audio_buffer = bytearray()

        async def on_audio_delta(audio_data: bytes) -> None:
            """Handle audio response from OpenAI."""
            try:
                await ws.send_bytes(audio_data)
            except Exception as err:
                _LOGGER.error("Failed to send audio: %s", err)

        async def on_transcript(text: str) -> None:
            """Handle transcript updates."""
            try:
                await ws.send_json({"type": "transcript", "text": text})
            except Exception as err:
                _LOGGER.error("Failed to send transcript: %s", err)

        async def on_function_call(name: str, arguments: dict) -> Any:
            """Handle function calls from the AI."""
            _LOGGER.info("Executing function: %s with args: %s", name, arguments)
            
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
                return {"error": f"Unknown function: {name}"}

        # Create Realtime API handler
        realtime = RealtimeAPIHandler(
            api_key=api_key,
            on_audio_delta=on_audio_delta,
            on_transcript=on_transcript,
            on_function_call=on_function_call,
        )

        try:
            # Connect to OpenAI Realtime API
            connected = await realtime.connect()
            if not connected:
                await ws.send_json({"type": "error", "message": "Failed to connect to OpenAI"})
                await ws.close()
                return ws

            await ws.send_json({"type": "connected"})

            # Handle incoming messages
            async for msg in ws:
                if msg.type == web.WSMsgType.BINARY:
                    # Audio data from client
                    await realtime.send_audio(msg.data)
                    
                elif msg.type == web.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                        msg_type = data.get("type", "")
                        
                        if msg_type == "audio_commit":
                            # Client finished sending audio
                            await realtime.commit_audio()
                            
                        elif msg_type == "text":
                            # Text message instead of audio
                            await realtime.send_text(data.get("text", ""))
                            
                        elif msg_type == "ping":
                            await ws.send_json({"type": "pong"})
                            
                    except Exception as err:
                        _LOGGER.error("Error processing message: %s", err)
                        
                elif msg.type == web.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", ws.exception())
                    break

        except Exception as err:
            _LOGGER.error("WebSocket handler error: %s", err)
        finally:
            await realtime.disconnect()

        return ws


@callback
def async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register WebSocket API endpoints."""
    
    @websocket_api.websocket_command(
        {
            vol.Required("type"): "rohlik_voice/get_cart",
        }
    )
    @websocket_api.async_response
    async def websocket_get_cart(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Get current cart contents."""
        entry_id = list(hass.data[DOMAIN].keys())[0]
        mcp_client: RohlikMCPClient = hass.data[DOMAIN][entry_id]["mcp_client"]
        
        result = await mcp_client.get_cart()
        connection.send_result(msg["id"], result)

    @websocket_api.websocket_command(
        {
            vol.Required("type"): "rohlik_voice/search",
            vol.Required("keyword"): str,
        }
    )
    @websocket_api.async_response
    async def websocket_search(
        hass: HomeAssistant,
        connection: websocket_api.ActiveConnection,
        msg: dict[str, Any],
    ) -> None:
        """Search for products."""
        entry_id = list(hass.data[DOMAIN].keys())[0]
        mcp_client: RohlikMCPClient = hass.data[DOMAIN][entry_id]["mcp_client"]
        
        result = await mcp_client.search_products(
            keyword=msg["keyword"],
        )
        connection.send_result(msg["id"], result)

    # Register the commands
    websocket_api.async_register_command(hass, websocket_get_cart)
    websocket_api.async_register_command(hass, websocket_search)

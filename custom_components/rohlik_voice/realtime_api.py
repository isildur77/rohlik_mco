"""OpenAI Realtime API handler for voice conversations."""

import asyncio
import base64
import json
import logging
from typing import Any, Callable

import aiohttp

from .const import OPENAI_REALTIME_URL, OPENAI_REALTIME_MODEL
from .tools import ROHLIK_TOOLS, SYSTEM_PROMPT

_LOGGER = logging.getLogger(__name__)


class RealtimeAPIHandler:
    """Handler for OpenAI Realtime API WebSocket connection."""

    def __init__(
        self,
        api_key: str,
        on_audio_delta: Callable[[bytes], None] | None = None,
        on_transcript: Callable[[str], None] | None = None,
        on_function_call: Callable[[str, dict], Any] | None = None,
    ) -> None:
        """Initialize the Realtime API handler."""
        self._api_key = api_key
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._session: aiohttp.ClientSession | None = None
        self._on_audio_delta = on_audio_delta
        self._on_transcript = on_transcript
        self._on_function_call = on_function_call
        self._connected = False
        self._receive_task: asyncio.Task | None = None

    @property
    def connected(self) -> bool:
        """Return True if connected to the API."""
        return self._connected and self._ws is not None and not self._ws.closed

    async def connect(self) -> bool:
        """Connect to the OpenAI Realtime API."""
        try:
            self._session = aiohttp.ClientSession()
            
            url = f"{OPENAI_REALTIME_URL}?model={OPENAI_REALTIME_MODEL}"
            headers = {
                "Authorization": f"Bearer {self._api_key}",
                "OpenAI-Beta": "realtime=v1",
            }
            
            self._ws = await self._session.ws_connect(url, headers=headers)
            self._connected = True
            
            # Configure the session
            await self._configure_session()
            
            # Start receiving messages
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            _LOGGER.info("Connected to OpenAI Realtime API")
            return True
            
        except Exception as err:
            _LOGGER.error("Failed to connect to Realtime API: %s", err)
            self._connected = False
            return False

    async def _configure_session(self) -> None:
        """Configure the Realtime session with tools and instructions."""
        if not self._ws:
            return
            
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": SYSTEM_PROMPT,
                "voice": "alloy",  # Options: alloy, echo, shimmer
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500,
                },
                "tools": ROHLIK_TOOLS,
                "tool_choice": "auto",
            },
        }
        
        await self._ws.send_json(config)
        _LOGGER.debug("Session configured")

    async def disconnect(self) -> None:
        """Disconnect from the API."""
        self._connected = False
        
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None
        
        if self._ws and not self._ws.closed:
            await self._ws.close()
            self._ws = None
        
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
        
        _LOGGER.info("Disconnected from OpenAI Realtime API")

    async def send_audio(self, audio_data: bytes) -> None:
        """Send audio data to the API."""
        if not self.connected:
            _LOGGER.warning("Cannot send audio: not connected")
            return
        
        # Encode audio as base64
        audio_base64 = base64.b64encode(audio_data).decode("utf-8")
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64,
        }
        
        await self._ws.send_json(message)

    async def commit_audio(self) -> None:
        """Commit the audio buffer and trigger response."""
        if not self.connected:
            return
        
        # Commit the audio buffer
        await self._ws.send_json({"type": "input_audio_buffer.commit"})
        
        # Create a response
        await self._ws.send_json({"type": "response.create"})

    async def send_text(self, text: str) -> None:
        """Send a text message to the API."""
        if not self.connected:
            _LOGGER.warning("Cannot send text: not connected")
            return
        
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text,
                    }
                ],
            },
        }
        
        await self._ws.send_json(message)
        await self._ws.send_json({"type": "response.create"})

    async def _receive_loop(self) -> None:
        """Receive and process messages from the API."""
        if not self._ws:
            return
        
        try:
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._handle_message(json.loads(msg.data))
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    _LOGGER.error("WebSocket error: %s", self._ws.exception())
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSED:
                    _LOGGER.info("WebSocket closed")
                    break
        except asyncio.CancelledError:
            pass
        except Exception as err:
            _LOGGER.error("Error in receive loop: %s", err)
        finally:
            self._connected = False

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Handle a message from the API."""
        msg_type = message.get("type", "")
        
        if msg_type == "error":
            _LOGGER.error("API error: %s", message.get("error"))
            
        elif msg_type == "session.created":
            _LOGGER.debug("Session created: %s", message.get("session", {}).get("id"))
            
        elif msg_type == "session.updated":
            _LOGGER.debug("Session updated")
            
        elif msg_type == "response.audio.delta":
            # Audio response chunk
            audio_base64 = message.get("delta", "")
            if audio_base64 and self._on_audio_delta:
                audio_data = base64.b64decode(audio_base64)
                self._on_audio_delta(audio_data)
                
        elif msg_type == "response.audio_transcript.delta":
            # Transcript of the assistant's response
            transcript = message.get("delta", "")
            if transcript and self._on_transcript:
                self._on_transcript(transcript)
                
        elif msg_type == "conversation.item.input_audio_transcription.completed":
            # User's speech transcription
            transcript = message.get("transcript", "")
            _LOGGER.debug("User said: %s", transcript)
            
        elif msg_type == "response.function_call_arguments.done":
            # Function call completed
            await self._handle_function_call(message)
            
        elif msg_type == "response.done":
            _LOGGER.debug("Response completed")

    async def _handle_function_call(self, message: dict[str, Any]) -> None:
        """Handle a function call from the API."""
        call_id = message.get("call_id", "")
        name = message.get("name", "")
        arguments_str = message.get("arguments", "{}")
        
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}
        
        _LOGGER.info("Function call: %s(%s)", name, arguments)
        
        # Execute the function if handler is provided
        result = None
        if self._on_function_call:
            try:
                result = await self._on_function_call(name, arguments)
            except Exception as err:
                _LOGGER.error("Function call error: %s", err)
                result = {"error": str(err)}
        
        # Send the result back to the API
        if result is not None:
            await self._send_function_result(call_id, result)

    async def _send_function_result(self, call_id: str, result: Any) -> None:
        """Send function call result back to the API."""
        if not self.connected:
            return
        
        # Convert result to string if needed
        if isinstance(result, dict):
            result_str = json.dumps(result, ensure_ascii=False)
        else:
            result_str = str(result)
        
        # Send the function output
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "function_call_output",
                "call_id": call_id,
                "output": result_str,
            },
        }
        
        await self._ws.send_json(message)
        
        # Trigger a new response based on the function result
        await self._ws.send_json({"type": "response.create"})

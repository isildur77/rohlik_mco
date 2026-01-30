"""Rohlik MCP Client for communicating with Rohlik.cz MCP server."""

import asyncio
import logging
from typing import Any

import aiohttp

from .const import ROHLIK_MCP_URL, MCP_TIMEOUT

_LOGGER = logging.getLogger(__name__)


class RohlikMCPClient:
    """Client for Rohlik MCP Server."""

    def __init__(self, email: str, password: str) -> None:
        """Initialize the MCP client."""
        self._email = email
        self._password = password
        self._session: aiohttp.ClientSession | None = None
        self._headers = {
            "Content-Type": "application/json",
            "rhl-email": email,
            "rhl-pass": password,
        }

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure we have an active session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=MCP_TIMEOUT)
            )
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool on the MCP server."""
        session = await self._ensure_session()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        try:
            async with session.post(
                ROHLIK_MCP_URL,
                json=payload,
                headers=self._headers,
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    _LOGGER.error(
                        "MCP call failed: %s - %s", response.status, error_text
                    )
                    return {"error": f"HTTP {response.status}: {error_text}"}
                
                result = await response.json()
                
                if "error" in result:
                    _LOGGER.error("MCP error: %s", result["error"])
                    return {"error": result["error"]}
                
                return result.get("result", {})
                
        except asyncio.TimeoutError:
            _LOGGER.error("MCP call timed out")
            return {"error": "Request timed out"}
        except aiohttp.ClientError as err:
            _LOGGER.error("MCP client error: %s", err)
            return {"error": str(err)}

    async def list_tools(self) -> dict[str, Any]:
        """List available tools from the MCP server."""
        session = await self._ensure_session()
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
        }

        try:
            async with session.post(
                ROHLIK_MCP_URL,
                json=payload,
                headers=self._headers,
            ) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}"}
                return await response.json()
        except Exception as err:
            _LOGGER.error("Failed to list tools: %s", err)
            return {"error": str(err)}

    async def search_products(
        self,
        query: str,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Search for products on Rohlik."""
        return await self._call_tool(
            "search_products",
            {"query": query, "limit": limit},
        )

    async def add_to_cart(
        self,
        product_id: str,
        quantity: int = 1,
    ) -> dict[str, Any]:
        """Add a product to the cart."""
        return await self._call_tool(
            "add_to_cart",
            {"productId": product_id, "quantity": quantity},
        )

    async def get_cart(self) -> dict[str, Any]:
        """Get the current cart contents."""
        return await self._call_tool("get_cart_content", {})

    async def remove_from_cart(self, product_id: str) -> dict[str, Any]:
        """Remove a product from the cart."""
        return await self._call_tool(
            "remove_from_cart",
            {"productId": product_id},
        )

    async def test_connection(self) -> bool:
        """Test if the connection to Rohlik MCP server works."""
        try:
            result = await self.list_tools()
            return "error" not in result
        except Exception as err:
            _LOGGER.error("Connection test failed: %s", err)
            return False

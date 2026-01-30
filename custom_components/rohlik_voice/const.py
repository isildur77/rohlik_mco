"""Constants for the Rohlik Voice integration."""

DOMAIN = "rohlik_voice"

# Configuration keys
CONF_ROHLIK_EMAIL = "rohlik_email"
CONF_ROHLIK_PASSWORD = "rohlik_password"
CONF_OPENAI_API_KEY = "openai_api_key"

# Rohlik MCP Server
ROHLIK_MCP_URL = "https://mcp.rohlik.cz/mcp"

# OpenAI Chat API (for Conversation Agent)
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_CHAT_MODEL = "gpt-4o-mini"

# OpenAI Realtime API (kept for future use)
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"
OPENAI_REALTIME_MODEL = "gpt-4o-mini-realtime-preview"

# WebSocket (kept for future use)
WS_PATH = "/api/rohlik_voice/ws"

# Timeouts
MCP_TIMEOUT = 30
CHAT_TIMEOUT = 60
REALTIME_TIMEOUT = 60

# Platforms
PLATFORMS = ["conversation"]

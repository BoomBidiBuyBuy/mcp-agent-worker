import os

MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = os.getenv("MCP_PORT", "8000")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

MCP_REGISTRY_ENDPOINT = os.getenv("MCP_REGISTRY_ENDPOINT")

MCP_SERVERS_FILE_PATH = os.environ.get("MCP_SERVERS_FILE_PATH", "assets/mcp-servers.json")

DEFAULT_ROLE = os.getenv("DEFAULT_ROLE", "unknown")

## mcp-agent-worker

LangChain-based agent served via FastMCP (HTTP transport). The agent integrates MCP tools from a registry (or a local JSON file) and exposes:

- An MCP tool to execute a plan: `execute_plan(user_id, str_json_plan)`
- HTTP endpoints for messaging, health checks, and refreshing the cached tool list

### Features

- FastMCP server hosting an in-process LangChain agent
- Role-based tool filtering via MCP Registry
- Dynamic MCP endpoint discovery via MCP Registry, with a local fallback JSON file
- `uv` for dependency management, `ruff` for linting

### Quickstart

1) Install `uv` — see `https://github.com/astral-sh/uv`

2) Install dependencies:

```bash
uv sync
```

3) Run the server:

```bash
uv run src/main.py
```

The server listens on `MCP_HOST:MCP_PORT` and exposes FastMCP over HTTP.

### Configuration

Set environment variables before running (defaults in parentheses):

- `MCP_HOST` ("0.0.0.0"): Bind address
- `MCP_PORT` ("8000"): Port
- `OPENAI_API_KEY` (required): OpenAI API key
- `OPENAI_MODEL` ("gpt-4o-mini"): Chat model
- `MCP_REGISTRY_ENDPOINT` (unset): URL of MCP Registry service; if unset, local file is used
- `MCP_SERVERS_FILE_PATH` ("assets/mcp-servers.json"): Fallback JSON with MCP servers
- `DEFAULT_ROLE` ("unknown"): Role used when registry does not provide one

The code reads variables from the process environment. If you prefer a `.env` file, ensure your process loads it prior to start.

### HTTP endpoints

- `GET /health` — health check
- `GET /reread_tools` — refresh the cached tool list from the MCP Registry/local file
- `POST /message` — send a user message to the agent

Example:

```bash
curl -sS -X POST "http://localhost:8000/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "user_id": "user-123"}'
```

Response:

```json
{
  "status": "message received",
  "message": "...agent reply..."
}
```

### MCP tool: execute_plan

The MCP tool `execute_plan(user_id: str, str_json_plan: str)` executes a plan/pipeline silently and returns a concise result. See `docs/execute_plan.md` for the expected JSON plan structure and `docs/tools_availability.md` for how tools are discovered and cached.

### Development

Lint:

```bash
uv run ruff check .
uv run ruff format .
```

### License

MIT

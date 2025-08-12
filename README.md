# mcp-agent-worker

LangChain-based agent exposed via FastMCP. The agent can dynamically integrate MCP endpoints from a JSON registry, and exposes its own MCP tools to:

- Execute a prompt-based plan
- Add an MCP endpoint to the agent (by name)
- Remove an MCP endpoint from the agent (by name)

## Features

- FastMCP server hosting an in-process LangChain agent
- Dynamic MCP endpoint registry backed by JSON file
- OpenAI model configuration via environment variables (supports `.env`)
- `uv` for dependency management
- `ruff` for linting with GitHub Actions CI

## Quickstart

1. Install `uv` if you don't have it: see `https://github.com/astral-sh/uv`
2. Create and populate your environment variables:

   - Copy `.env.example` to `.env` and fill in values

3. Install dependencies:

```bash
uv sync
```

4. Run the MCP server:

```bash
uv run mcp-agent-worker
```

The server will start and expose MCP tools as defined in `mcp_agent_worker/mcp_server.py`.

## Configuration

The agent reads configuration from environment variables. See `.env.example` for all available options.

- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: Chat model (e.g. `gpt-4o-mini`)
- `AGENT_NAME`: A display name for the agent
- `MCP_REGISTRY_PATH`: Path to the JSON file that stores dynamic MCP endpoints

## MCP Tools

The service exposes three tools:

1. `execute_plan(prompt: str)` — Ask the agent to execute a prompt-based plan.
2. `add_endpoint(name: str, endpoint: str)` — Add/register an MCP endpoint by name.
3. `remove_endpoint(name: str)` — Remove a registered MCP endpoint by name.

The registry persists in the JSON file defined by `MCP_REGISTRY_PATH`.

## Development

- Lint:

```bash
uv run ruff check .
uv run ruff format .
```

## CI

GitHub Actions runs lint checks on pushes and pull requests.

## License

MIT

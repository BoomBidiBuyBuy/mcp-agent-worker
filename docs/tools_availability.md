## Tools availability

The service caches available MCP tools in memory to speed up execution. This avoids repeatedly querying every MCP service, which would be slow when multiple services and endpoints are present.

### How tools are loaded

1. On first agent initialization, the service loads MCP services from the MCP Registry (or from `assets/mcp-servers.json` if no registry is configured)
2. It builds a `MultiServerMCPClient` and fetches the combined tool list
3. The tool list is kept in memory

### Keeping tools up to date

- The service exposes `GET /reread_tools` to refresh the tool list
- When invoked, it fetches the latest service list from the MCP Registry and rebuilds the `MultiServerMCPClient`
- The MCP Registry can call this endpoint whenever services are added or removed

### Role-based tool filtering

Before each model invocation, the agent asks the MCP Registry for the user's role and the tools allowed for that role. Only those tools are bound to the model for the current request.
## Execute plan

The `execute_plan` MCP tool executes a predefined plan (pipeline) using the agent. Typical use cases:

- Scheduler runs plans asynchronously by calling the MCP tool from a separate service
- Admins/operators trigger a plan manually for testing

The tool is designed to execute work silently in the background and return a concise status/result.

### Parameters

- `user_id` (string): Used as the `thread_id` to preserve user context across messages
- `str_json_plan` (string): A JSON string describing the plan/pipeline to execute

The plan should include MCP service endpoints, tool names, arguments, and optional execution conditions. The agent reads and executes this plan.

### Plan JSON structure

```json
{
  "unique_action_id_1": {
    "mcp-service-endpoint": "https://service-1.example.com/mcp",
    "mcp-tool-name": "tool_name_to_call",
    "mcp-tool-arguments": {
      "arg-name": "arg-value"
    },
    "condition": "executes first"
  },
  "unique_action_id_2": {
    "mcp-service-endpoint": "https://service-2.example.com/mcp",
    "mcp-tool-name": "another_tool",
    "mcp-tool-arguments": {},
    "condition": "executes only if unique_action_id_1 was successful"
  }
}
```

Action IDs are arbitrary strings that let you reference dependencies/conditions between actions.

### Execution flow

1. `user_id` is required
2. The service queries the MCP Registry for the user's `role`
3. The agent is created/bound with the `user_id` and `role`
4. The agent retrieves the list of allowed tools for the `role` and binds them
5. The agent invokes the model and executes the plan using only the allowed tools

### Notes

- Prompts used for plan execution and regular message processing are different, but the same agent is used under the hood
- The plan execution prompt focuses on silently and efficiently executing the pipeline
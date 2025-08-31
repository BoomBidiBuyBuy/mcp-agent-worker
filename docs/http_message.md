## `/message` HTTP endpoint

Endpoint for sending a user message to the agent.

### Primary purposes

- Perform an immediate action or generate a helpful reply
- Optionally propose a plan/pipeline that can be handed off to a scheduler

### Request

Method: POST

Body (JSON):

```json
{
  "message": "string — user message",
  "user_id": "string — unique user identifier"
}
```

### Response

```json
{
  "status": "message received",
  "message": "string — agent reply"
}
```

### Processing flow

1. `user_id` is required
2. The service queries the MCP Registry for the user's `role`
3. The agent is bound to the `user_id` and `role`
4. The agent fetches allowed tools for the `role` and binds only those tools
5. The agent invokes the model and returns a user-friendly response

### Notes

- Prompts for message processing and plan execution are different, but the same agent is used
- Message handling prioritizes non-technical output suitable for end users

import asyncio
import logging

from fastmcp import FastMCP
from langchain_core.messages import HumanMessage, SystemMessage

import agent
import envs

mcp = FastMCP(name="mcp-agent-worker")


# Configure logging
logger = logging.getLogger("mcp_agent_worker")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
logger.info("MCP Agent Worker initialized")


@mcp.tool
def execute_plan(str_json_plan: str) -> str:
    """
    Execute a plan using the agent help.

    Args:
        str_json_plan: A JSON string representing the plan to execute.
        Plan contains list / sequence actions.
        Action is an MCP tool call that contains endpoint of MCP service to call, tool name to call,
        arguments, and condition when the call to execute.

        The JSON has the following structure:
        {
            "unique_action_id_1": {
                "mcp-service-name": "name-of-the-mcp-service-to-call",
                "mcp-tool-name": "name-of-the-mcp-tool-to-call",
                "mcp-tool-arguments": {
                    "arg-name": "arg-value"
                },
                "condition": "executes first"
            },
            "unique_action_id_2": {
                ...
                "condition": "executes only if unique_action_id_1 was successful"
            },
            ...
        }

    Returns:
        The result of the plan execution.
    """
    logger.info("Executing plan", extra={"str_json_plan": str_json_plan})

    agent_obj = agent.build_agent()
    result = agent_obj.invoke(
        {
            "messages": [
                SystemMessage(
                    content="You are a helpful assistant that can execute plans. "
                    "You are given a plan to execute. "
                ),
                HumanMessage(content=str_json_plan),
            ]
        }
    )

    logger.info("Plan executed", extra={"result": result})

    return result.content


if __name__ == "__main__":
    host = envs.MCP_HOST
    port = int(envs.MCP_PORT)
    logger.info("Starting MCP server", extra={"host": host, "port": port})
    asyncio.run(mcp.run_async(transport="http", host=host, port=port))

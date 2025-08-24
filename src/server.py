import json
import logging
from typing import Annotated

from starlette.responses import JSONResponse

from fastmcp import FastMCP
from langchain_core.messages import HumanMessage, SystemMessage

from envs import MCP_HOST, MCP_PORT

import agent


mcp_server = FastMCP(name="mcp-agent-worker")


logger = logging.getLogger(__name__)
# Configure logging
logger.info("MCP Agent Worker initialized")


@mcp_server.tool
async def execute_plan(
    str_json_plan: Annotated[str, "A JSON string representing the plan to execute."]
    ) -> Annotated[str, "The result of the plan execution."]:
    """Execute a plan using the agent help."""
    logger.info(f"Executing plan ={str_json_plan}")

    # retrieve MCP service addresses from the plan
    # with goal to connect agent to them to get proper tools
    parsed_json = json.loads(str_json_plan)
    thread_id = parsed_json.get("thread_id")
    #ext_mcp_servers = {record["mcp-service-endpoint"] for record in parsed_json.values()}
    #
    #dict_ext_mcp_servers = dict()
    #for inx, value in enumerate(ext_mcp_servers):
    #    dict_ext_mcp_servers[f"name{inx}"] = {"transport": "streamable_http", "url": value}

    agent_obj = await agent.get_agent()
    result = await agent_obj.ainvoke(
        {
            "messages": [
                SystemMessage(
                    content="""You are a helpful assistant that can execute plans.
                    You are given a plan to execute. You are connected to the MCP registry where you
                    can find possible MCP services and their tools to use in plan."""
                ),
                HumanMessage(content=str_json_plan),
            ]
        },
        config={"configurable": {"thread_id": thread_id}}
    )

    logger.info(f"\n\nPlan executed, result={result}\n\n")

    reply_message = result.get("messages")[-1].content

    return reply_message


@mcp_server.custom_route("/health", methods=["GET"])
async def http_health_check(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy", "service": "mcp-agent-worker"})


@mcp_server.custom_route("/message", methods=["POST"])
async def http_message(request):
    """ Endpoint to process message from the client with agent."""
    data = await request.json()
    message = data.get("message")
    thread_id = data.get("thread_id")
    agent_obj = await agent.get_agent()
    result = await agent_obj.ainvoke(
        {
            "messages": [
                SystemMessage(
                    content="""You are a helpful assistant that joined to MCP tools.
                    You can either execute something instantly or to schedule execution
                    for later / periodically using the scheduler.
                    If you are not sure about any parameter for any tool then you have
                    to ask the user for it.
                    """
                ),
                HumanMessage(content=message),
            ],
        },
        config={"configurable": {"thread_id": thread_id}}
    )
    logger.info(f"\n\nMessage received, result={result}\n\n")
    
    reply_message = result.get("messages")[-1].content

    return JSONResponse({"status": "message received", "message": reply_message})


if __name__ == "__main__":
    logger.info(f"Starting MCP server on {MCP_HOST}:{MCP_PORT}")
    mcp_server.run(transport="http", host=MCP_HOST, port=MCP_PORT)

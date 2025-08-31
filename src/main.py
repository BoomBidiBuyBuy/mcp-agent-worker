import asyncio
import logging
from typing import Annotated, Any

import httpx
from fastmcp import FastMCP
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import HumanMessage, SystemMessage
from starlette.responses import JSONResponse

import agent
from envs import DEFAULT_ROLE, MCP_HOST, MCP_PORT, MCP_REGISTRY_ENDPOINT

mcp_server = FastMCP(name="mcp-agent-worker")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


class LogHandler(BaseCallbackHandler):
    def on_tool_start(self, serialized: dict, input_str: str, **kwargs: Any):
        print("\n\n>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
        print(f"[TOOL start] {serialized.get('name')} args={input_str}")


def get_role_for_user(user_id: str) -> str:
    if MCP_REGISTRY_ENDPOINT:
        response = httpx.post(f"{MCP_REGISTRY_ENDPOINT}/role_for_user", json={"user_id": user_id})
        response.raise_for_status()
        response_data = response.json()
        role = response_data.get("role")
        if role:
            logger.info(f"MCP Registry say that for user={user_id} role is {role}")
        else:
            logger.info(f"MCP Registry return EMPTY role for the user={user_id}")
        return role
    return DEFAULT_ROLE


def get_default_system_prompt(role: str) -> str:
    if MCP_REGISTRY_ENDPOINT:
        response = httpx.post(f"{MCP_REGISTRY_ENDPOINT}/system_prompt_for_role", json={"role": role})
        response.raise_for_status()
        response_data = response.json()
        system_prompt = response_data.get("system_prompt")
        if system_prompt:
            logger.info(f"MCP Registry say that for role={role} system prompt is {system_prompt}")
        else:
            logger.info(f"MCP Registry return EMPTY system prompt for the role={role}")
        return system_prompt
    return ""


@mcp_server.tool
async def execute_plan(
    user_id: Annotated[str, "The user that is executing the plan"],
    str_json_plan: Annotated[str, "A JSON string representing the plan to execute."],
) -> Annotated[str, "The result of the plan execution."]:
    """Execute a plan using the agent help."""
    logger.info(f"Executing plan {str_json_plan}")
    logger.info(f"Executing plan for user {user_id}")
    # retrieve MCP service addresses from the plan
    # with goal to connect agent to them to get proper tools
    # parsed_json = json.loads(str_json_plan)
    # ext_mcp_servers = {record["mcp-service-endpoint"] for record in parsed_json.values()}
    #
    # dict_ext_mcp_servers = dict()
    # for inx, value in enumerate(ext_mcp_servers):
    #    dict_ext_mcp_servers[f"name{inx}"] = {"transport": "streamable_http", "url": value}

    agent_obj = await agent.get_agent()
    result = await agent_obj.ainvoke(
        {
            "messages": [
                SystemMessage(
                    content="You are silent plan executor."
                    "You are given a plan to execute."
                    "You are connected to the MCP registry where you "
                    "can find possible MCP services and their tools to use in plan."
                    "You have silently and efficiently to execute passed plan."
                ),
                SystemMessage(content=f"The user that is executing the plan is {user_id}"),
                HumanMessage(
                    content=str_json_plan,
                    user_id=user_id,
                    role=get_role_for_user(user_id),
                ),
            ]
        },
        config={"configurable": {"thread_id": user_id}, "callbacks": [LogHandler()]},
        tool_choice="required",  # push to not generate output, just execute tools
    )

    logger.info(f"\n\nPlan executed, result={result}\n\n")

    reply_message = result.get("messages")[-1].content

    return reply_message


@mcp_server.custom_route("/health", methods=["GET"])
async def http_health_check(request):
    """Health check endpoint."""
    logger.info("Health check endpoint")
    return JSONResponse({"status": "healthy", "service": "mcp-agent-worker"})


@mcp_server.custom_route("/reread_tools", methods=["GET"])
async def http_reread_tools(request):
    """Endpoint to reread tools from MCP registry."""
    logger.info("Rereading tools from MCP registry")
    await agent.read_tools_from_mcp()
    return JSONResponse({"status": "tools reread"})


@mcp_server.custom_route("/message", methods=["POST"])
async def http_message(request):
    """Endpoint to process message from the client with agent."""

    logger.info(f"\n\nRecieved to process /message, result={request}\n\n")

    data = await request.json()
    message = data.get("message")
    user_id = data.get("user_id")
    agent_obj = await agent.get_agent()

    role = get_role_for_user(user_id)
    default_system_prompt = get_default_system_prompt(role)

    system_messaegs = [
                SystemMessage(
                    content="You are a helpful assistant that joined to MCP tools."
                    "There are might be no tools, in that case do not say to user "
                    "what you can do."
                ),
                SystemMessage(
                    content="Your users are non technical, do not expose technical details like "
                    "JSON, ids, any MCP mention, etc. "
                    "If you want to list something for a user and there are ids in list then "
                    "enumerate items and print description instead of ids."
                ),
                SystemMessage(
                    content="Do not ask confirmation if everything is clear, "
                    "just do that and report status"
                ),
                SystemMessage(content=f"user has id='{user_id}'"),
    ]

    if default_system_prompt:
        system_messaegs.append(SystemMessage(content=default_system_prompt))

    result = await agent_obj.ainvoke(
        {
            "messages": [
                *system_messaegs,
                HumanMessage(
                    content=message,
                    user_id=user_id,
                    role=role,
                ),
            ],
        },
        config={
            "configurable": {"thread_id": user_id},
            "callbacks": [LogHandler()],
        },
    )
    logger.info(f"\n\nMessage received, result={result}\n\n")

    reply_message = result.get("messages")[-1].content

    return JSONResponse({"status": "message received", "message": reply_message})


async def run_server():
    logger.info(f"Starting MCP server on {MCP_HOST}:{MCP_PORT}")
    await mcp_server.run_async(transport="http", host=MCP_HOST, port=int(MCP_PORT))


if __name__ == "__main__":
    asyncio.run(run_server())

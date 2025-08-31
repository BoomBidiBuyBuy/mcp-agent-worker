import asyncio
import json
import logging
import os

import httpx
from langchain_core.messages import HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from envs import MCP_REGISTRY_ENDPOINT, MCP_SERVERS_FILE_PATH, OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger("mcp_agent_worker")


logger = logging.getLogger(__name__)

# Global agent instance
agent = None
agent_initializing = False
tools = []

llm = ChatOpenAI(
    temperature=1,
    streaming=False,
    model=OPENAI_MODEL,
    api_key=OPENAI_API_KEY,
)


async def read_tools_from_mcp():
    global tools

    try:  # Create client to connect to our MCP server
        logger.info("Connecting to MCP servers...")

        mcp_servers = load_mcp_servers()

        client = MultiServerMCPClient(mcp_servers)
        tools = await client.get_tools()
        # TODO: implement fetching roles from the MCP registry
        logger.info("Connected to MCP servers")
        logger.info(f"Loaded {len(tools)} tools: {[tool.name for tool in tools]}")

    except Exception as e:
        logger.exception("Failed to connect to MCP server: %s", e)
        # Return empty tools if MCP server is not available
        tools = []


def get_allowed_tools_for_role(role: str):
    if MCP_REGISTRY_ENDPOINT:
        logger.info(f"Getting allowed tools for role: {role}")
        response = httpx.post(f"{MCP_REGISTRY_ENDPOINT}/tools_for_role", json={"role": role})
        response.raise_for_status()

        response_data = response.json()
        logger.info(f"Allowed tools: {response_data}")
        return response_data.get("tools", [])

    return []


def filter_tools_for_role(tools, role: str):
    if role == "admin":
        logger.info("Role 'admin' allows to use all tools, no filtering")
        return tools
    if role == "":
        logger.info("Empty role does not allow to use any tools, return empty list")
        return []

    allowed_tools = get_allowed_tools_for_role(role)

    return [tool for tool in tools if tool.name in [allowed_tool["name"] for allowed_tool in allowed_tools]]


def call_model(state: MessagesState):
    global tools, llm

    try:
        logger.info("\n\n      [ Call model ]\n")
        logger.debug(f"State messages: {state['messages']}")

        user_id = None
        role = None
        for message in reversed(state["messages"]):
            # Get the last human message since his role
            # can change during the conversation
            if isinstance(message, HumanMessage):
                role = message.role
                user_id = message.user_id
                break
        logger.info(f"\nUser {user_id} initiated a call has role = {role}")
        logger.info(f"All tools: {tools}")

        allowed_tools = filter_tools_for_role(tools, role)

        logger.info(f"Allowed tools for role {role}: {allowed_tools}")

        if allowed_tools:
            response = llm.bind_tools(allowed_tools).invoke(state["messages"])
            logger.debug(f"LLM response: {response}")
        else:
            logger.info("Using LLM without tools")
            response = llm.invoke(state["messages"])
            logger.debug(f"LLM response without tools: {response}")
        return {"messages": response}
    except Exception as e:
        logger.exception(f"Error in call_model: {e}")
        # Return a simple error message
        from langchain_core.messages import AIMessage

        return {
            "messages": [
                AIMessage(content="Sorry, I encountered an error processing your request.")
            ]
        }


async def build_agent():
    """
    Builds an OpenAI-based agent using the LangChain framework,
    integrated with a simple FastMCP server for local development.

    The agent uses InMemorySaver to persist conversation history.
    """
    await read_tools_from_mcp()

    builder = StateGraph(MessagesState)
    builder.add_node(call_model)

    if tools:
        builder.add_node(ToolNode(tools))
        builder.add_edge(START, "call_model")
        builder.add_conditional_edges(
            "call_model",
            tools_condition,
        )
        builder.add_edge("tools", "call_model")
    else:
        builder.add_edge(START, "call_model")

    # Use InMemorySaver to persist conversation history
    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)


async def get_agent():
    """Get or initialize the agent (lazy initialization)"""
    global agent, agent_initializing

    if agent is not None:
        return agent

    if agent_initializing:
        # Wait for initialization to complete
        while agent_initializing:
            await asyncio.sleep(0.1)
        return agent

    agent_initializing = True
    try:
        logger.info("Initializing agent...")
        agent = await build_agent()
        logger.info("Agent initialized successfully")
        return agent
    finally:
        agent_initializing = False


def _expand_env_vars(value):
    """Recursively expand ${VAR} or $VAR in strings inside dict/list structures."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars(v) for v in value]
    return value


def load_mcp_servers():
    if MCP_REGISTRY_ENDPOINT:
        # Read MCP servers from the MCP registry
        logger.info(f"Loading MCP servers from registry endpoint: {MCP_REGISTRY_ENDPOINT}")
        response = httpx.get(f"{MCP_REGISTRY_ENDPOINT}/list_services")
        response.raise_for_status()
        response_data = response.json()

        mcp_servers = response_data.get("services", {})
        logger.info(f"Loaded MCP servers: {mcp_servers}")
        return mcp_servers
    else:
        with open(MCP_SERVERS_FILE_PATH) as f:
            permanent_servers = json.load(f)
        mcp_servers = permanent_servers.get("mcpServers", {})
        mcp_servers = _expand_env_vars(mcp_servers)
        logger.info(f"Loaded MCP servers: {mcp_servers}")
        return mcp_servers

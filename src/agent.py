import asyncio
import json
import logging
import os
from collections.abc import Sequence
from typing import Annotated

import httpx
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from envs import MCP_REGISTRY_ENDPOINT, MCP_SERVERS_FILE_PATH, OPENAI_API_KEY, OPENAI_MODEL

logger = logging.getLogger("mcp_agent_worker")


logger = logging.getLogger(__name__)

# Global agent instance
agent = None
agent_initializing = False
tools = []


async def read_tools_from_mcp():
    global tools

    try:  # Create client to connect to our MCP server
        logger.info("Connecting to MCP servers...")

        mcp_servers = load_mcp_servers()

        client = MultiServerMCPClient(mcp_servers)
        tools = await client.get_tools()
        logger.info("Connected to MCP servers")
        logger.info(f"Loaded {len(tools)} tools: {[tool.name for tool in tools]}")

    except Exception as e:
        logger.exception("Failed to connect to MCP server: %s", e)
        # Return empty tools if MCP server is not available
        tools = []



async def build_agent():
    """
    Builds an OpenAI-based agent using the LangChain framework,
    integrated with a simple FastMCP server for local development.

    The agent uses InMemorySaver to persist conversation history.
    """
    llm = ChatOpenAI(
        temperature=1,
        streaming=False,
        model=OPENAI_MODEL,
        api_key=OPENAI_API_KEY,
    )

    await read_tools_from_mcp()

    def call_model(state: MessagesState):
        global tools

        try:
            logger.info("\n\n      [ Call model ]\n")
            logger.debug("State messages: %s", state["messages"])

            logger.info(f"\nstate = {state}")
            user_id = None
            role = None
            for message in state["messages"]:
                if isinstance(message, HumanMessage):
                    user_id = message.user_id
                    role = message.role
            logger.info(f"\nrole = {role}")
            logger.info(f"\nuser_id = {user_id}")

            if tools:
                logger.info(f"Using {len(tools)} tools: {[tool.name for tool in tools]}")
                response = llm.bind_tools(tools).invoke(state["messages"])
                logger.debug("LLM response with tools: %s", response)
            else:
                logger.info("Using LLM without tools")
                response = llm.invoke(state["messages"])
                logger.debug("LLM response without tools: %s", response)
            return {"messages": response}
        except Exception as e:
            logger.exception("Error in call_model: %s", e)
            # Return a simple error message
            from langchain_core.messages import AIMessage

            return {
                "messages": [
                    AIMessage(content="Sorry, I encountered an error processing your request.")
                ]
            }

    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    #builder.add_node(filter_tools)

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

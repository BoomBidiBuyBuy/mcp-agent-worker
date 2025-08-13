import asyncio
import json

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

import envs


def load_mcp_servers(custom_mcp_servers):
    with open("mcp-servers.json") as f:
        permanent_servers = json.load(f)

    mcp_servers = permanent_servers.get("mcpServers", {})
    if custom_mcp_servers:
        mcp_servers.update(custom_mcp_servers)

    return mcp_servers


async def build_agent(custom_mcp_servers: dict = None):
    """
    Builds an OpenAI-based agent using the LangChain framework,
    integrated with MCP servers listed in the `mcp-servers.json` file.

    The agent uses an in-memory saver to retain the history
    of the conversation during runtime.
    """
    llm = ChatOpenAI(
        temperature=0, streaming=False, model=envs.OPENAI_MODEL, api_key=envs.OPENAI_API_KEY
    )

    mcp_servers = load_mcp_servers(custom_mcp_servers)

    print(f"Connected the following MCP servers {mcp_servers}")

    client = MultiServerMCPClient(mcp_servers)

    # get tools
    tools = await client.get_tools()

    def call_model(state: MessagesState):
        response = llm.bind_tools(tools).invoke(state["messages"])
        return {"messages": response}

    checkpointer = InMemorySaver()
    builder = StateGraph(MessagesState)
    builder.add_node(call_model)
    builder.add_node(ToolNode(tools))
    builder.add_edge(START, "call_model")
    builder.add_conditional_edges(
        "call_model",
        tools_condition,
    )
    builder.add_edge("tools", "call_model")

    return builder.compile() #checkpointer=checkpointer)

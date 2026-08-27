
import os

from langchain_mcp_adapters.client import MultiServerMCPClient


SERVER_PATH = os.path.abspath(
    "/content/hw3_mas/mcp_server.py"
)


async def get_mcp_tools():
    """
    Завантажити MCP tools через MultiServerMCPClient.
    """

    client = MultiServerMCPClient({
        "support": {
            "command": "python",
            "args": [SERVER_PATH],
            "transport": "stdio",
        }
    })

    tools = await client.get_tools()

    return {
        tool.name: tool
        for tool in tools
    }


async def call_mcp_tool(
    tool_name: str,
    args: dict,
):
    """
    Виклик MCP tool за ім'ям.
    """

    tools = await get_mcp_tools()

    if tool_name not in tools:
        raise ValueError(
            f"MCP tool not found: {tool_name}"
        )

    return await tools[tool_name].ainvoke(args)

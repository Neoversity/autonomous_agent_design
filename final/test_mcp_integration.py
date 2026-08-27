
import os
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():

    server_path = os.path.abspath(
        "/content/hw3_mas/mcp_server.py"
    )

    client = MultiServerMCPClient({
        "support": {
            "command": "python",
            "args": [server_path],
            "transport": "stdio",
        }
    })

    tools = await client.get_tools()

    print("=== MCP → LANGGRAPH INTEGRATION ===")
    print(f"Loaded {len(tools)} MCP tools:")

    for tool in tools:
        print(" -", tool.name)

    expected = {
        "get_ticket",
        "get_customer",
        "search_tickets",
        "get_summary",
        "update_ticket_status",
    }

    tool_names = {tool.name for tool in tools}

    assert expected.issubset(tool_names)

    print("\n✅ MCP tools loaded through MultiServerMCPClient")


if __name__ == "__main__":
    asyncio.run(main())

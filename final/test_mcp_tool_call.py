
import os
import asyncio

from langchain_mcp_adapters.client import MultiServerMCPClient


async def main():

    client = MultiServerMCPClient({
        "support": {
            "command": "python",
            "args": [
                os.path.abspath(
                    "/content/hw3_mas/mcp_server.py"
                )
            ],
            "transport": "stdio",
        }
    })

    tools = await client.get_tools()

    tools_by_name = {
        tool.name: tool
        for tool in tools
    }

    # --------------------------------------------------------
    # MCP CALL 1 — get_ticket
    # --------------------------------------------------------

    get_ticket = tools_by_name["get_ticket"]

    result = await get_ticket.ainvoke({
        "ticket_id": "TKT-001"
    })

    print("=== MCP TOOL CALL ===")
    print("Tool: get_ticket")
    print("Result:")
    print(result)

    assert "TKT-001" in str(result)

    # --------------------------------------------------------
    # MCP CALL 2 — get_summary
    # --------------------------------------------------------

    get_summary = tools_by_name["get_summary"]

    summary = await get_summary.ainvoke({})

    print("\n=== MCP TOOL CALL 2 ===")
    print("Tool: get_summary")
    print("Result:")
    print(summary)

    assert "total_tickets" in str(summary)

    print("\n✅ MCP tool calls through adapter PASSED")


if __name__ == "__main__":
    asyncio.run(main())

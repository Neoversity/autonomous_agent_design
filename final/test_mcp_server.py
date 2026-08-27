
import asyncio
import json

from mcp_server import mcp


async def call_tool(name: str, args: dict) -> str:
    """
    Helper для виклику MCP tool.
    Повертає текст першого content block.
    """
    result = await mcp.call_tool(name, args)

    if isinstance(result, tuple):
        blocks = result[0]
    else:
        blocks = result

    return blocks[0].text


async def main():
    print("=== MCP UNIT TESTS ===\n")

    # --------------------------------------------------------
    # TEST 1 — list_tools
    # --------------------------------------------------------

    tools = await mcp.list_tools()
    tool_names = {tool.name for tool in tools}

    expected_tools = {
        "get_ticket",
        "get_customer",
        "search_tickets",
        "get_summary",
        "update_ticket_status",
    }

    assert expected_tools.issubset(tool_names)

    print("✅ TEST 1 PASS — list_tools")


    # --------------------------------------------------------
    # TEST 2 — get_ticket found
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "get_ticket",
            {"ticket_id": "TKT-001"},
        )
    )

    assert data["id"] == "TKT-001"
    assert "subject" in data

    print("✅ TEST 2 PASS — get_ticket(TKT-001)")


    # --------------------------------------------------------
    # TEST 3 — get_ticket not found
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "get_ticket",
            {"ticket_id": "TKT-999"},
        )
    )

    assert "error" in data

    print("✅ TEST 3 PASS — get_ticket(TKT-999) → error")


    # --------------------------------------------------------
    # TEST 4 — get_customer
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "get_customer",
            {"customer_id": "C-100"},
        )
    )

    assert data["id"] == "C-100"
    assert data["tier"] == "gold"

    print("✅ TEST 4 PASS — get_customer(C-100)")


    # --------------------------------------------------------
    # TEST 5 — search_tickets
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "search_tickets",
            {"category": "billing"},
        )
    )

    assert data["count"] >= 1

    for ticket in data["tickets"]:
        assert ticket["category"] == "billing"

    print("✅ TEST 5 PASS — search_tickets(category=billing)")


    # --------------------------------------------------------
    # TEST 6 — get_summary
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "get_summary",
            {},
        )
    )

    assert data["total_tickets"] >= 3
    assert data["total_customers"] >= 3

    print("✅ TEST 6 PASS — get_summary")


    # --------------------------------------------------------
    # TEST 7 — update_ticket_status valid
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "update_ticket_status",
            {
                "ticket_id": "TKT-001",
                "new_status": "in_progress",
                "reason": "unit test",
            },
        )
    )

    assert data["updated"] == "TKT-001"
    assert data["new_status"] == "in_progress"

    print("✅ TEST 7 PASS — update_ticket_status(valid)")


    # --------------------------------------------------------
    # TEST 8 — update_ticket_status invalid
    # --------------------------------------------------------

    data = json.loads(
        await call_tool(
            "update_ticket_status",
            {
                "ticket_id": "TKT-001",
                "new_status": "BOGUS",
            },
        )
    )

    assert "error" in data

    print("✅ TEST 8 PASS — update_ticket_status(invalid)")


    # --------------------------------------------------------
    # TEST 9 — list_resources
    # --------------------------------------------------------

    resources = await mcp.list_resources()

    resource_uris = [
        str(resource.uri)
        for resource in resources
    ]

    assert any(
        "faq://general" in uri
        for uri in resource_uris
    )

    print("✅ TEST 9 PASS — list_resources contains faq://general")


    # --------------------------------------------------------
    # TEST 10 — list_prompts
    # --------------------------------------------------------

    prompts = await mcp.list_prompts()

    prompt_names = [
        prompt.name
        for prompt in prompts
    ]

    assert "support_reply" in prompt_names

    print("✅ TEST 10 PASS — list_prompts contains support_reply")


    print("\n================================")
    print("✅ ALL MCP UNIT TESTS PASSED!")
    print("================================")


if __name__ == "__main__":
    asyncio.run(main())


import asyncio
import json

from mcp_client import get_mcp_tools


async def main():
    print("=== MAS + MCP DEMO ===")

    tools = await get_mcp_tools()

    # ========================================================
    # STEP 1 — supervisor decision
    # ========================================================

    query = "Не списано платіж за тариф у вересні"

    current_agent = "billing"

    print("\n[Supervisor]")
    print("Query:", query)
    print("Route →", current_agent)

    # ========================================================
    # STEP 2 — billing agent через MCP
    # ========================================================

    print("\n[Billing Agent]")
    print("Using MCP tools...")

    search_result = await tools["search_tickets"].ainvoke({
        "category": "billing",
        "status": "",
        "priority": "",
    })

    print("\nMCP tool: search_tickets")
    print(search_result)

    search_data = json.loads(str(search_result))

    tickets = search_data.get("tickets", [])

    if not tickets:
        print("No billing tickets found.")
        return

    ticket_id = tickets[0]["id"]

    # ========================================================
    # STEP 3 — get_ticket через MCP
    # ========================================================

    ticket_result = await tools["get_ticket"].ainvoke({
        "ticket_id": ticket_id
    })

    print("\nMCP tool: get_ticket")
    print(ticket_result)

    ticket_data = json.loads(str(ticket_result))

    customer_id = ticket_data.get("customer_id")

    # ========================================================
    # STEP 4 — get_customer через MCP
    # ========================================================

    customer_result = await tools["get_customer"].ainvoke({
        "customer_id": customer_id
    })

    print("\nMCP tool: get_customer")
    print(customer_result)

    # ========================================================
    # RESULT
    # ========================================================

    print("\n=== FINAL MAS MCP RESULT ===")
    print("Agent:", current_agent)
    print("Ticket:", ticket_id)
    print("Customer:", customer_id)

    print("\n✅ MAS billing flow used MCP tools successfully")


if __name__ == "__main__":
    asyncio.run(main())

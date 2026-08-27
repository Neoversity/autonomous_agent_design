
import os
import json
import asyncio
import operator
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import StateGraph, START, END

from langchain_mcp_adapters.client import MultiServerMCPClient


# ============================================================
# STATE
# ============================================================

class MCPMASState(TypedDict):
    messages: Annotated[list, operator.add]
    current_agent: str
    tools_called: list[str]
    completed: bool


# ============================================================
# LOAD MCP TOOLS
# ============================================================

async def load_tools():

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

    return {
        tool.name: tool
        for tool in tools
    }


# ============================================================
# LANGGRAPH NODES
# ============================================================

def supervisor_node(state: MCPMASState):

    query = state["messages"][-1].content.lower()

    # Для integration demo достатньо deterministic routing,
    # щоб не витрачати додатковий LLM API call.
    if any(
        word in query
        for word in [
            "платіж",
            "оплат",
            "рахунок",
            "billing",
            "тариф",
        ]
    ):
        agent = "billing"
    else:
        agent = "general"

    return {
        "current_agent": agent
    }


async def billing_node(state: MCPMASState):

    tools = await load_tools()

    called = []

    # --------------------------------------------------------
    # MCP TOOL 1 — search_tickets
    # --------------------------------------------------------

    search_raw = await tools["search_tickets"].ainvoke({
        "category": "billing",
        "status": "",
        "priority": "",
    })

    called.append("search_tickets")

    search_data = json.loads(str(search_raw))

    tickets = search_data.get("tickets", [])

    if not tickets:

        return {
            "messages": [
                AIMessage(
                    content="Billing tickets не знайдено."
                )
            ],
            "tools_called": called,
            "completed": True,
        }

    ticket_id = tickets[0]["id"]

    # --------------------------------------------------------
    # MCP TOOL 2 — get_ticket
    # --------------------------------------------------------

    ticket_raw = await tools["get_ticket"].ainvoke({
        "ticket_id": ticket_id
    })

    called.append("get_ticket")

    ticket_data = json.loads(str(ticket_raw))

    customer_id = ticket_data.get("customer_id")

    # --------------------------------------------------------
    # MCP TOOL 3 — get_customer
    # --------------------------------------------------------

    customer_raw = await tools["get_customer"].ainvoke({
        "customer_id": customer_id
    })

    called.append("get_customer")

    customer_data = json.loads(str(customer_raw))

    answer = (
        f"Знайдено billing ticket {ticket_id}. "
        f"Клієнт: {customer_data.get('name')} "
        f"({customer_id}). "
        f"Статус тікета: {ticket_data.get('status')}. "
        f"Тема: {ticket_data.get('subject')}."
    )

    return {
        "messages": [
            AIMessage(content=answer)
        ],
        "tools_called": called,
        "completed": True,
    }


def general_node(state: MCPMASState):

    return {
        "messages": [
            AIMessage(
                content="Запит не належить до billing demo."
            )
        ],
        "tools_called": [],
        "completed": True,
    }


# ============================================================
# ROUTER
# ============================================================

def route(state: MCPMASState):

    return state.get(
        "current_agent",
        "general",
    )


# ============================================================
# GRAPH
# ============================================================

graph = StateGraph(MCPMASState)

graph.add_node(
    "supervisor",
    supervisor_node,
)

graph.add_node(
    "billing",
    billing_node,
)

graph.add_node(
    "general",
    general_node,
)

graph.add_edge(
    START,
    "supervisor",
)

graph.add_conditional_edges(
    "supervisor",
    route,
    {
        "billing": "billing",
        "general": "general",
    },
)

graph.add_edge(
    "billing",
    END,
)

graph.add_edge(
    "general",
    END,
)

app = graph.compile()


# ============================================================
# DEMO
# ============================================================

async def main():

    query = "Не списано платіж за тариф у вересні"

    initial_state = {
        "messages": [
            HumanMessage(content=query)
        ],
        "current_agent": "",
        "tools_called": [],
        "completed": False,
    }

    result = await app.ainvoke(
        initial_state
    )

    print("=== LANGGRAPH + MCP MAS ===")

    print(
        "Agent:",
        result["current_agent"]
    )

    print(
        "Completed:",
        result["completed"]
    )

    print(
        "Tools called:",
        result["tools_called"]
    )

    print("\n=== ANSWER ===")

    print(
        result["messages"][-1].content
    )

    assert result["current_agent"] == "billing"

    assert {
        "search_tickets",
        "get_ticket",
        "get_customer",
    }.issubset(
        set(result["tools_called"])
    )

    print(
        "\n✅ LangGraph MAS used MCP tools successfully"
    )


if __name__ == "__main__":
    asyncio.run(main())


import json

from pydantic import BaseModel, Field
from langchain_core.tools import tool


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class TicketInput(BaseModel):
    ticket_id: str = Field(
        description="Ticket ID in format TKT-XXX"
    )


class CustomerInput(BaseModel):
    customer_id: str = Field(
        description="Customer ID in format C-XXX"
    )


class SearchTicketsInput(BaseModel):
    category: str = Field(
        default="",
        description="billing | tech | empty string"
    )
    status: str = Field(
        default="",
        description="open | in_progress | resolved | closed | empty string"
    )


# ============================================================
# MOCK DATA
# ============================================================

TICKETS = {
    "TKT-001": {
        "customer_id": "C-100",
        "subject": "Не списано платіж",
        "status": "open",
        "priority": "high",
        "category": "billing",
    },
    "TKT-002": {
        "customer_id": "C-101",
        "subject": "Пристрій не вмикається після оновлення",
        "status": "in_progress",
        "priority": "medium",
        "category": "tech",
    },
    "TKT-003": {
        "customer_id": "C-102",
        "subject": "Повернення коштів",
        "status": "open",
        "priority": "low",
        "category": "billing",
    },
}


CUSTOMERS = {
    "C-100": {
        "name": "Олег Петренко",
        "tier": "gold",
        "email": "oleh@example.com",
    },
    "C-101": {
        "name": "Марія Коваленко",
        "tier": "silver",
        "email": "maria@example.com",
    },
    "C-102": {
        "name": "Іван Бондар",
        "tier": "standard",
        "email": "ivan@example.com",
    },
}


# ============================================================
# LANGCHAIN TOOLS
# ============================================================

@tool(args_schema=TicketInput)
def get_ticket(ticket_id: str) -> str:
    """
    Отримати інформацію про support ticket.
    """

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        return json.dumps(
            {"error": f"Ticket {ticket_id} not found"},
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "id": ticket_id,
            **ticket,
        },
        ensure_ascii=False,
    )


@tool(args_schema=CustomerInput)
def get_customer(customer_id: str) -> str:
    """
    Отримати інформацію про клієнта.
    """

    customer = CUSTOMERS.get(customer_id)

    if not customer:
        return json.dumps(
            {"error": f"Customer {customer_id} not found"},
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "id": customer_id,
            **customer,
        },
        ensure_ascii=False,
    )


@tool(args_schema=SearchTicketsInput)
def search_tickets(
    category: str = "",
    status: str = "",
) -> str:
    """
    Пошук support tickets за категорією та статусом.
    """

    results = []

    for ticket_id, ticket in TICKETS.items():

        if category and ticket["category"] != category:
            continue

        if status and ticket["status"] != status:
            continue

        results.append(
            {
                "id": ticket_id,
                **ticket,
            }
        )

    return json.dumps(
        {
            "count": len(results),
            "tickets": results,
        },
        ensure_ascii=False,
    )


ALL_TOOLS = [
    get_ticket,
    get_customer,
    search_tickets,
]

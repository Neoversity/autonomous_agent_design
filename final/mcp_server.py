
import json
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    name="support_domain_server",
    instructions=(
        "Customer support MCP server with tickets, customers, "
        "FAQ resources and support prompts."
    ),
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
        "subject": "Питання щодо повернення коштів",
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
# TOOLS
# ============================================================

@mcp.tool()
def get_ticket(ticket_id: str) -> str:
    """
    Отримати тікет за його ID.

    Args:
        ticket_id: Ідентифікатор тікета у форматі TKT-XXX.

    Returns:
        JSON з деталями тікета або повідомленням про помилку.
    """

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        return json.dumps(
            {"error": f"Ticket {ticket_id} not found"},
            ensure_ascii=False,
        )

    return json.dumps(
        {"id": ticket_id, **ticket},
        ensure_ascii=False,
    )


@mcp.tool()
def get_customer(customer_id: str) -> str:
    """
    Отримати інформацію про клієнта.

    Args:
        customer_id: Ідентифікатор клієнта у форматі C-XXX.

    Returns:
        JSON з даними клієнта або повідомленням про помилку.
    """

    customer = CUSTOMERS.get(customer_id)

    if not customer:
        return json.dumps(
            {"error": f"Customer {customer_id} not found"},
            ensure_ascii=False,
        )

    return json.dumps(
        {"id": customer_id, **customer},
        ensure_ascii=False,
    )


@mcp.tool()
def search_tickets(
    category: str = "",
    status: str = "",
    priority: str = "",
) -> str:
    """
    Пошук тікетів за категорією, статусом або пріоритетом.

    Args:
        category: billing | tech або порожній рядок.
        status: open | in_progress | resolved | closed або порожній рядок.
        priority: low | medium | high або порожній рядок.

    Returns:
        JSON зі списком знайдених тікетів.
    """

    results = []

    for ticket_id, ticket in TICKETS.items():

        if category and ticket["category"] != category:
            continue

        if status and ticket["status"] != status:
            continue

        if priority and ticket["priority"] != priority:
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


@mcp.tool()
def get_summary() -> str:
    """
    Отримати коротку статистику customer-support системи.

    Returns:
        JSON із кількістю тікетів за статусами та категоріями.
    """

    by_status = {}
    by_category = {}

    for ticket in TICKETS.values():

        status = ticket["status"]
        category = ticket["category"]

        by_status[status] = by_status.get(status, 0) + 1
        by_category[category] = by_category.get(category, 0) + 1

    return json.dumps(
        {
            "total_tickets": len(TICKETS),
            "total_customers": len(CUSTOMERS),
            "by_status": by_status,
            "by_category": by_category,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def update_ticket_status(
    ticket_id: str,
    new_status: str,
    reason: str = "",
) -> str:
    """
    Оновити статус тікета.

    РИЗИКОВА ДІЯ:
    у MAS ця операція повинна проходити через HITL approval.

    Args:
        ticket_id: ID тікета у форматі TKT-XXX.
        new_status: open | in_progress | resolved | closed.
        reason: Причина зміни статусу.

    Returns:
        JSON з результатом зміни статусу.
    """

    valid_statuses = {
        "open",
        "in_progress",
        "resolved",
        "closed",
    }

    if ticket_id not in TICKETS:
        return json.dumps(
            {"error": f"Ticket {ticket_id} not found"},
            ensure_ascii=False,
        )

    if new_status not in valid_statuses:
        return json.dumps(
            {
                "error": "Invalid status",
                "valid_statuses": sorted(valid_statuses),
            },
            ensure_ascii=False,
        )

    old_status = TICKETS[ticket_id]["status"]

    TICKETS[ticket_id]["status"] = new_status

    return json.dumps(
        {
            "updated": ticket_id,
            "old_status": old_status,
            "new_status": new_status,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        ensure_ascii=False,
    )


# ============================================================
# RESOURCES
# ============================================================

@mcp.resource("faq://general")
def faq_general() -> str:
    """
    Загальний FAQ customer-support системи.
    Read-only resource.
    """

    faq = [
        {
            "question": "Як скинути пароль?",
            "answer": (
                'На сторінці входу натисніть "Забули пароль?" '
                "та введіть email."
            ),
        },
        {
            "question": "Як повернути кошти?",
            "answer": (
                "Зверніться до billing-відділу. "
                "Стандартний строк повернення — 3–5 робочих днів."
            ),
        },
        {
            "question": "Який час відповіді підтримки?",
            "answer": (
                "Gold — до 1 години, Silver — до 4 годин, "
                "Standard — до 24 годин."
            ),
        },
    ]

    return json.dumps(
        faq,
        ensure_ascii=False,
    )


@mcp.resource("ticket://{ticket_id}")
def ticket_resource(ticket_id: str) -> str:
    """
    Read-only resource для конкретного тікета.
    """

    ticket = TICKETS.get(ticket_id)

    if not ticket:
        return json.dumps(
            {"error": f"Ticket {ticket_id} not found"},
            ensure_ascii=False,
        )

    return json.dumps(
        {"id": ticket_id, **ticket},
        ensure_ascii=False,
    )


# ============================================================
# PROMPT
# ============================================================

@mcp.prompt()
def support_reply(
    customer_name: str,
    issue_summary: str,
    tone: str = "professional",
) -> str:
    """
    Шаблон відповіді клієнту.

    Args:
        customer_name: Ім'я клієнта.
        issue_summary: Короткий опис проблеми.
        tone: professional | empathetic | concise.
    """

    tones = {
        "professional": "Сформулюй формальну та чітку відповідь",
        "empathetic": (
            "Сформулюй теплу відповідь із визнанням "
            "труднощів клієнта"
        ),
        "concise": "Сформулюй коротку відповідь без зайвих фраз",
    }

    instruction = tones.get(
        tone,
        tones["professional"],
    )

    return (
        f"{instruction} клієнту {customer_name}. "
        f"Проблема: {issue_summary}. "
        "Запропонуй наступний крок та орієнтовні строки."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    mcp.run(transport="stdio")

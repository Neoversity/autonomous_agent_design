
# ============================================================
# MCP SERVER — DevOps Assistant
# Варіант 3: Infrastructure Monitoring
# ============================================================

import json
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("infra_monitor")


# ------------------------------------------------------------
# Mock-дані сервісів
# ------------------------------------------------------------

SERVICES = {
    "api-gateway": {
        "cpu": 85,
        "memory": 72,
        "status": "degraded",
        "uptime_hours": 128,
        "response_time_ms": 6200,
        "replicas": 2,
    },
    "auth-service": {
        "cpu": 42,
        "memory": 51,
        "status": "healthy",
        "uptime_hours": 240,
        "response_time_ms": 220,
        "replicas": 2,
    },
}


LOGS = {
    "api-gateway": [
        {
            "level": "ERROR",
            "message": "Upstream timeout while calling auth-service",
            "minutes_ago": 2,
        },
        {
            "level": "WARNING",
            "message": "High request queue detected",
            "minutes_ago": 4,
        },
        {
            "level": "INFO",
            "message": "Traffic increased by 70 percent",
            "minutes_ago": 7,
        },
    ]
}


# ============================================================
# TOOL 1 — check_service
# ============================================================

@mcp.tool()
def check_service(name: str) -> str:
    """
    Перевірити поточний стан сервісу.

    Args:
        name: Назва сервісу.

    Returns:
        JSON зі статусом, CPU, memory, uptime,
        response time та кількістю replicas.
    """

    service = SERVICES.get(name)

    if not service:
        return json.dumps(
            {
                "status": "error",
                "error": f"Service '{name}' not found",
            }
        )

    return json.dumps(
        {
            "status": "success",
            "data": {
                "name": name,
                **service,
            },
        }
    )


# ============================================================
# TOOL 2 — search_logs
# ============================================================

@mcp.tool()
def search_logs(
    service: str,
    level: str,
    minutes: int,
) -> str:
    """
    Пошук записів у логах сервісу.

    Args:
        service: Назва сервісу.
        level: Рівень логів: INFO, WARNING або ERROR.
        minutes: Глибина пошуку у хвилинах (1-60).

    Returns:
        JSON зі знайденими записами.
    """

    if minutes < 1 or minutes > 60:
        return json.dumps(
            {
                "status": "error",
                "error": "minutes must be between 1 and 60",
            }
        )

    level = level.upper()

    if level not in {"INFO", "WARNING", "ERROR"}:
        return json.dumps(
            {
                "status": "error",
                "error": "level must be INFO, WARNING or ERROR",
            }
        )

    service_logs = LOGS.get(service, [])

    results = [
        item
        for item in service_logs
        if item["minutes_ago"] <= minutes
        and item["level"] == level
    ]

    return json.dumps(
        {
            "status": "success",
            "data": {
                "service": service,
                "level": level,
                "minutes": minutes,
                "logs": results,
            },
        }
    )


# ============================================================
# TOOL 3 — restart_service
# РИЗИКОВИЙ TOOL — потребує HITL
# ============================================================

@mcp.tool()
def restart_service(name: str) -> str:
    """
    Перезапустити сервіс.

    УВАГА:
    ризикова операція. У MAS вона повинна виконуватися
    тільки після підтвердження людиною.
    """

    if name not in SERVICES:
        return json.dumps(
            {
                "status": "error",
                "error": f"Service '{name}' not found",
            }
        )

    SERVICES[name]["status"] = "healthy"
    SERVICES[name]["response_time_ms"] = 450
    SERVICES[name]["uptime_hours"] = 0

    return json.dumps(
        {
            "status": "success",
            "data": {
                "name": name,
                "action": "restarted",
            },
        }
    )


# ============================================================
# TOOL 4 — scale_service
# РИЗИКОВИЙ TOOL — потребує HITL
# ============================================================

@mcp.tool()
def scale_service(
    name: str,
    replicas: int,
) -> str:
    """
    Змінити кількість replicas сервісу.

    Args:
        name: Назва сервісу.
        replicas: Кількість replicas від 1 до 10.

    УВАГА:
    ризикова операція. Потребує HITL.
    """

    if name not in SERVICES:
        return json.dumps(
            {
                "status": "error",
                "error": f"Service '{name}' not found",
            }
        )

    if replicas < 1 or replicas > 10:
        return json.dumps(
            {
                "status": "error",
                "error": "replicas must be between 1 and 10",
            }
        )

    old_replicas = SERVICES[name]["replicas"]
    SERVICES[name]["replicas"] = replicas

    return json.dumps(
        {
            "status": "success",
            "data": {
                "name": name,
                "old_replicas": old_replicas,
                "new_replicas": replicas,
                "action": "scaled",
            },
        }
    )

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

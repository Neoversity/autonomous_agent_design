
# ============================================================
# GUARDRAILS — DevOps Assistant
# ============================================================

import re


# ------------------------------------------------------------
# 1. INPUT GUARDRAIL — Prompt Injection Detection
# ------------------------------------------------------------

INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"ignore all previous",
    r"system prompt",
    r"developer message",
    r"bypass",
    r"jailbreak",
    r"forget your instructions",
    r"do not follow",
]


def detect_prompt_injection(text: str) -> bool:
    """
    Виявляє базові ознаки prompt injection у user input.
    Повертає True, якщо знайдено підозрілий патерн.
    """

    normalized = text.lower().strip()

    return any(
        re.search(pattern, normalized)
        for pattern in INJECTION_PATTERNS
    )


# ------------------------------------------------------------
# 2. TOOL GUARDRAIL — Allowlist per agent
# ------------------------------------------------------------

TOOL_PERMISSIONS = {
    "coordinator": {
        "check_service",
        "search_logs",
    },
    "monitor_agent": {
        "check_service",
    },
    "log_analyzer": {
        "search_logs",
    },
    "action_agent": {
        "check_service",
        "restart_service",
        "scale_service",
    },
}


def tool_guardrail(agent: str, tool: str) -> bool:
    """
    Перевіряє, чи має конкретний агент доступ до tool.
    """

    return tool in TOOL_PERMISSIONS.get(agent, set())


# ------------------------------------------------------------
# 3. ARGUMENT VALIDATION
# ------------------------------------------------------------

def validate_scale_args(args: dict) -> bool:
    """
    Перевіряє аргументи для scale_service.
    replicas повинно бути у діапазоні 1-10.
    """

    replicas = args.get("replicas")

    if not isinstance(replicas, int):
        return False

    return 1 <= replicas <= 10


def validate_log_args(args: dict) -> bool:
    """
    Перевіряє аргументи search_logs.
    """

    minutes = args.get("minutes")
    level = str(args.get("level", "")).upper()

    if not isinstance(minutes, int):
        return False

    if not 1 <= minutes <= 60:
        return False

    if level not in {"INFO", "WARNING", "ERROR"}:
        return False

    return True


# ------------------------------------------------------------
# 4. OUTPUT GUARDRAIL — PII / Secrets redaction
# ------------------------------------------------------------

EMAIL_PATTERN = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

PHONE_PATTERN = (
    r"(?<![A-Za-z0-9])"
    r"(?:\+?\d{1,3}[\s\-]?)?"
    r"(?:\(?\d{2,3}\)?[\s\-]?)?"
    r"\d{3}[\s\-]?\d{2}[\s\-]?\d{2}"
    r"(?![A-Za-z0-9])"
)

SECRET_PATTERNS = [
    r"(?i)(api[_\-]?key\s*[:=]\s*)[A-Za-z0-9_\-]{8,}",
    r"(?i)(token\s*[:=]\s*)[A-Za-z0-9_\-.]{8,}",
    r"(?i)(password\s*[:=]\s*)\S+",
]


def redact_sensitive_data(text: str) -> str:
    """
    Видаляє API keys, tokens, passwords,
    email та телефонні номери із фінальної відповіді.
    """

    result = text

    # Спочатку маскуємо secrets,
    # щоб цифри всередині ключів не визначались як телефон.
    for pattern in SECRET_PATTERNS:
        result = re.sub(
            pattern,
            lambda m: m.group(1) + "[REDACTED_SECRET]",
            result
        )

    result = re.sub(
        EMAIL_PATTERN,
        "[REDACTED_EMAIL]",
        result
    )

    result = re.sub(
        PHONE_PATTERN,
        "[REDACTED_PHONE]",
        result
    )

    return result

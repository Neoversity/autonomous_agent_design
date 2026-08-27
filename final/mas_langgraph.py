
import os
import time
import sqlite3
import operator

from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field

from langchain_core.messages import (
    HumanMessage,
    AIMessage,
)

from langchain_google_genai import ChatGoogleGenerativeAI

from langgraph.graph import (
    StateGraph,
    START,
    END,
)

from langgraph.checkpoint.sqlite import SqliteSaver


from trajectory import log_step
from rag import search_knowledge
from tools import (
    get_ticket,
    get_customer,
    search_tickets,
)


# ============================================================
# CONFIG
# ============================================================

MAX_STEPS = 8
TIMEOUT_SEC = 30


# ============================================================
# MAS STATE
# ============================================================

class MASState(TypedDict):
    messages: Annotated[list, operator.add]

    current_agent: str

    # Plan-and-Execute fields from HW2
    plan: list[str]
    current_step: int
    results: list[str]

    # ReAct / control fields from HW1
    step_count: int
    trajectory: Annotated[list, operator.add]

    # Completion flags
    completed: bool
    pending_approval: bool


# ============================================================
# STRUCTURED OUTPUT — SUPERVISOR
# ============================================================

class RouteDecision(BaseModel):
    """
    Structured decision produced by supervisor.
    """

    action: Literal[
        "billing",
        "tech",
        "researcher",
        "general",
    ] = Field(
        description="Agent that should handle the request."
    )

    reasoning: str = Field(
        description="Short explanation of routing decision."
    )


# ============================================================
# LLM
# ============================================================

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    temperature=0,
)

supervisor_llm = llm.with_structured_output(
    RouteDecision
)


# ============================================================
# SUPERVISOR
# ============================================================

SUPERVISOR_SYSTEM = """
You are the supervisor of a customer-support multi-agent system.

Route each user request to exactly one agent:

billing:
- payments
- charges
- invoices
- subscriptions
- refunds
- billing tickets

tech:
- device problems
- firmware
- errors
- authentication failures
- configuration
- troubleshooting

researcher:
- policies
- rules
- FAQ
- knowledge-base questions
- "how does X work?"
- reference questions

general:
- greetings
- conversation
- requests that do not belong to other categories

Return RouteDecision with:
1. action
2. short reasoning
"""


def supervisor_node(state: MASState) -> dict:
    """
    Supervisor chooses the next agent.
    """

    user_msg = ""

    if state.get("messages"):
        user_msg = state["messages"][-1].content

    decision = supervisor_llm.invoke(
        [
            ("system", SUPERVISOR_SYSTEM),
            ("user", user_msg),
        ]
    )

    step = log_step(
        agent_name="supervisor",
        node="route",
        action=user_msg,
        output=f"{decision.action}: {decision.reasoning}",
    )

    return {
        "current_agent": decision.action,
        "step_count": state.get("step_count", 0) + 1,
        "trajectory": [step],
    }


# ============================================================
# BILLING AGENT
# Plan-and-Execute буде додано наступним кроком
# ============================================================

class BillingPlan(BaseModel):
    """
    План дій billing-agent.
    """
    steps: list[str] = Field(
        description="Послідовність коротких кроків для вирішення billing-запиту"
    )


billing_planner = llm.with_structured_output(BillingPlan)


def billing_agent(state: MASState) -> dict:
    """
    Billing agent — Plan-and-Execute стиль з ДЗ2.

    Етапи:
    1. Planner формує план.
    2. Executor виконує кроки через tools.
    3. Finalizer формує відповідь.
    """

    user_msg = state["messages"][-1].content
    step_count = state.get("step_count", 0)

    if step_count >= MAX_STEPS:
        response_text = (
            f"Досягнуто максимальну кількість кроків: {MAX_STEPS}."
        )

        return {
            "messages": [AIMessage(content=response_text)],
            "completed": True,
            "trajectory": [
                log_step(
                    agent_name="billing",
                    node="max_steps_guard",
                    action=user_msg,
                    output=response_text,
                )
            ],
        }

    started_at = time.monotonic()

    # --------------------------------------------------------
    # 1. PLANNER
    # --------------------------------------------------------

    plan_obj = billing_planner.invoke([
        (
            "system",
            """
Ти planner billing-agent.

Склади короткий план із 2–3 кроків для вирішення запиту.
Доступні дії:
- search_tickets
- get_ticket
- get_customer

Не вигадуй ID, якщо їх немає у запиті.
"""
        ),
        (
            "user",
            user_msg,
        ),
    ])

    plan = plan_obj.steps[:3]

    # --------------------------------------------------------
    # 2. EXECUTOR
    # --------------------------------------------------------

    execution_results = []

    tickets_raw = search_tickets.invoke({
        "category": "billing",
        "status": "",
    })

    execution_results.append(
        f"search_tickets: {tickets_raw}"
    )

    # Для demo-кейсу знаходимо перший billing ticket.
    import json

    try:
        parsed = json.loads(tickets_raw)
        tickets = parsed.get("tickets", [])
    except Exception:
        tickets = []

    if tickets:
        ticket_id = tickets[0]["id"]

        ticket_raw = get_ticket.invoke({
            "ticket_id": ticket_id
        })

        execution_results.append(
            f"get_ticket({ticket_id}): {ticket_raw}"
        )

        try:
            ticket_data = json.loads(ticket_raw)
            customer_id = ticket_data.get("customer_id")
        except Exception:
            customer_id = None

        if customer_id:
            customer_raw = get_customer.invoke({
                "customer_id": customer_id
            })

            execution_results.append(
                f"get_customer({customer_id}): {customer_raw}"
            )

    # --------------------------------------------------------
    # 3. FINALIZER
    # --------------------------------------------------------

    response = llm.invoke([
        (
            "system",
            """
Ти billing-agent у customer-support MAS.

Використай:
- запит користувача
- план
- результати tools

Дай коротку відповідь українською.
Не вигадуй фактів.
Якщо є relevant ticket — вкажи його ID.
"""
        ),
        (
            "user",
            f"""
Запит:
{user_msg}

Plan:
{plan}

Execution results:
{execution_results}
"""
        ),
    ])

    response_text = _extract_text(response.content)

    elapsed = time.monotonic() - started_at

    trajectory_steps = [
        log_step(
            agent_name="billing",
            node="planner",
            action=user_msg,
            output=str(plan),
        ),
        log_step(
            agent_name="billing",
            node="executor",
            action="execute billing plan",
            output=str(execution_results),
            tools=[
                "search_tickets",
                "get_ticket",
                "get_customer",
            ],
        ),
        log_step(
            agent_name="billing",
            node="finalizer",
            action="compose final answer",
            output=response_text,
            metadata={
                "elapsed_sec": round(elapsed, 3),
            },
        ),
    ]

    return {
        "messages": [
            AIMessage(content=response_text)
        ],
        "plan": plan,
        "current_step": len(plan),
        "results": execution_results,
        "step_count": step_count + len(trajectory_steps),
        "trajectory": trajectory_steps,
        "completed": True,
    }


# ============================================================
# TECH AGENT
# ReAct буде додано наступним кроком
# ============================================================

def _extract_text(content) -> str:
    """
    Нормалізує Gemini response.content до звичайного тексту.
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
            else:
                parts.append(str(item))

        return "\n".join(parts)

    return str(content)


def tech_agent(state: MASState) -> dict:
    """
    Tech agent — спрощений ReAct-style агент з ДЗ1.

    Використовує:
    - max_steps
    - timeout
    - Pydantic tools
    - trajectory logging
    """

    started_at = time.monotonic()

    user_msg = state["messages"][-1].content

    step_count = state.get("step_count", 0)

    if step_count >= MAX_STEPS:
        response_text = (
            f"Досягнуто максимальну кількість кроків: {MAX_STEPS}."
        )

        return {
            "messages": [AIMessage(content=response_text)],
            "completed": True,
            "trajectory": [
                log_step(
                    agent_name="tech",
                    node="max_steps_guard",
                    action=user_msg,
                    output=response_text,
                )
            ],
        }

    # --------------------------------------------------------
    # 1. Пошук релевантних tech tickets
    # --------------------------------------------------------

    tickets_result = search_tickets.invoke({
        "category": "tech",
        "status": "",
    })

    if time.monotonic() - started_at > TIMEOUT_SEC:
        response_text = "Tech agent timeout."

        return {
            "messages": [AIMessage(content=response_text)],
            "completed": True,
            "trajectory": [
                log_step(
                    agent_name="tech",
                    node="timeout",
                    action=user_msg,
                    output=response_text,
                )
            ],
        }

    # --------------------------------------------------------
    # 2. RAG knowledge search
    # --------------------------------------------------------

    kb_result = search_knowledge.invoke({
        "query": user_msg,
        "top_k": 2,
    })

    # --------------------------------------------------------
    # 3. LLM reasoning
    # --------------------------------------------------------

    response = llm.invoke([
        (
            "system",
            """
Ти tech-agent у customer-support MAS.

Твоя задача — допомагати з технічними проблемами.

Використовуй передані результати tools та knowledge base.
Не вигадуй даних.

Дай:
1. короткий аналіз проблеми;
2. конкретні кроки вирішення;
3. якщо є відповідний support ticket — вкажи його ID.

Відповідай українською.
"""
        ),
        (
            "user",
            f"""
Запит:
{user_msg}

Tech tickets:
{tickets_result}

Knowledge base:
{kb_result}
"""
        ),
    ])

    response_text = _extract_text(response.content)

    elapsed = time.monotonic() - started_at

    step = log_step(
        agent_name="tech",
        node="react",
        action=user_msg,
        output=response_text,
        tools=[
            "search_tickets",
            "search_knowledge",
        ],
        metadata={
            "elapsed_sec": round(elapsed, 3),
            "max_steps": MAX_STEPS,
            "timeout_sec": TIMEOUT_SEC,
        },
    )

    return {
        "messages": [
            AIMessage(content=response_text)
        ],
        "step_count": step_count + 1,
        "trajectory": [step],
        "completed": True,
    }


# ============================================================
# RESEARCHER AGENT
# Agentic RAG буде додано наступним кроком
# ============================================================

def researcher_agent(state: MASState) -> dict:
    """
    Researcher agent з Agentic RAG через ChromaDB.
    """

    user_msg = state["messages"][-1].content

    # 1. Пошук у knowledge base
    rag_result = search_knowledge.invoke({
        "query": user_msg,
        "top_k": 3,
    })

    # 2. Формуємо відповідь через LLM
    response = llm.invoke([
        (
            "system",
            """
Ти researcher-agent у customer-support MAS.

Використовуй ТІЛЬКИ переданий контекст із knowledge base.
Не вигадуй фактів, яких немає у контексті.

Дай коротку, корисну відповідь українською мовою.
Якщо у контексті є source URI, вкажи його наприкінці.
"""
        ),
        (
            "user",
            f"""
Запит користувача:
{user_msg}

Knowledge base context:
{rag_result}
"""
        ),
    ])

    step = log_step(
        agent_name="researcher",
        node="agentic_rag",
        action=user_msg,
        output=response.content,
        tools=["search_knowledge"],
    )

    return {
        "messages": [
            AIMessage(content=response.content)
        ],
        "step_count": state.get("step_count", 0) + 1,
        "trajectory": [step],
        "completed": True,
    }


# ============================================================
# GENERAL AGENT
# ============================================================

def general_agent(state: MASState) -> dict:
    """
    Fallback agent.
    """

    response = (
        "Вітаю! Я customer-support assistant. "
        "Можу допомогти з оплатою, технічними проблемами "
        "або інформацією з бази знань."
    )

    step = log_step(
        agent_name="general",
        node="general_agent",
        action="general request",
        output=response,
    )

    return {
        "messages": [
            AIMessage(content=response)
        ],
        "trajectory": [step],
        "completed": True,
    }


# ============================================================
# ROUTER
# ============================================================

def route(
    state: MASState,
) -> Literal[
    "billing",
    "tech",
    "researcher",
    "general",
    "__end__",
]:
    """
    Conditional router після supervisor.
    """

    if state.get("completed"):
        return "__end__"

    return state.get(
        "current_agent",
        "general",
    )


# ============================================================
# GRAPH
# ============================================================

graph = StateGraph(MASState)

graph.add_node(
    "supervisor",
    supervisor_node,
)

graph.add_node(
    "billing",
    billing_agent,
)

graph.add_node(
    "tech",
    tech_agent,
)

graph.add_node(
    "researcher",
    researcher_agent,
)

graph.add_node(
    "general",
    general_agent,
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
        "tech": "tech",
        "researcher": "researcher",
        "general": "general",
        "__end__": END,
    },
)


graph.add_edge(
    "billing",
    END,
)

graph.add_edge(
    "tech",
    END,
)

graph.add_edge(
    "researcher",
    END,
)

graph.add_edge(
    "general",
    END,
)


# ============================================================
# CHECKPOINTER
# ============================================================

conn = sqlite3.connect(
    "/content/hw3_mas/agent_state.db",
    check_same_thread=False,
)

saver = SqliteSaver(conn)

app = graph.compile(
    checkpointer=saver
)


# ============================================================
# INITIAL STATE HELPER
# ============================================================

def create_initial_state(
    query: str,
) -> MASState:

    return {
        "messages": [
            HumanMessage(
                content=query
            )
        ],
        "current_agent": "",
        "plan": [],
        "current_step": 0,
        "results": [],
        "step_count": 0,
        "trajectory": [],
        "completed": False,
        "pending_approval": False,
    }

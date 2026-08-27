
import sqlite3
from typing import TypedDict, Annotated
import operator

from langchain_core.messages import AIMessage, HumanMessage

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.sqlite import SqliteSaver


# ============================================================
# STATE
# ============================================================

class HITLState(TypedDict):
    messages: Annotated[list, operator.add]
    current_agent: str
    pending_tool: dict
    pending_approval: bool
    completed: bool
    result: str


# ============================================================
# RISKY TOOLS
# ============================================================

RISKY_TOOLS = {
    "update_ticket_status",
    "delete_customer",
    "send_mass_email",
}


# ============================================================
# MOCK RISKY TOOL
# ============================================================

TICKETS = {
    "TKT-001": {
        "status": "open"
    }
}


def execute_update_ticket_status(
    ticket_id: str,
    new_status: str,
    reason: str = "",
) -> str:

    if ticket_id not in TICKETS:
        return f"Ticket {ticket_id} not found"

    old_status = TICKETS[ticket_id]["status"]

    TICKETS[ticket_id]["status"] = new_status

    return (
        f"{ticket_id}: "
        f"{old_status} → {new_status}. "
        f"Reason: {reason}"
    )


# ============================================================
# PREPARE TOOL CALL
# ============================================================

def prepare_action(state: HITLState):

    return {
        "current_agent": "billing",
        "pending_tool": {
            "name": "update_ticket_status",
            "args": {
                "ticket_id": "TKT-001",
                "new_status": "closed",
                "reason": "Customer confirmed resolution",
            },
        },
        "pending_approval": True,
    }


# ============================================================
# APPROVAL GATE
# ============================================================

def approval_gate(state: HITLState):
    """
    HITL approval gate.

    Supports:
    - approve
    - reject
    - edit
    """

    tool_call = state["pending_tool"]

    tool_name = tool_call["name"]

    if tool_name not in RISKY_TOOLS:

        return {
            "pending_approval": False
        }

    decision = interrupt({
        "message": "Підтвердити ризикову дію",
        "tool": tool_name,
        "args": tool_call["args"],
        "agent_name": state["current_agent"],
    })

    action = decision.get("action")

    # --------------------------------------------------------
    # REJECT
    # --------------------------------------------------------

    if action == "reject":

        reason = decision.get(
            "reason",
            "No reason provided"
        )

        message = (
            f"Дію {tool_name} відхилено. "
            f"Причина: {reason}"
        )

        return {
            "messages": [
                AIMessage(content=message)
            ],
            "result": message,
            "completed": True,
            "pending_approval": False,
        }

    # --------------------------------------------------------
    # EDIT
    # --------------------------------------------------------

    if action == "edit":

        edited_args = decision.get(
            "args",
            {}
        )

        tool_call["args"].update(
            edited_args
        )

    # --------------------------------------------------------
    # APPROVE / EDIT → EXECUTE
    # --------------------------------------------------------

    args = tool_call["args"]

    result = execute_update_ticket_status(
        ticket_id=args["ticket_id"],
        new_status=args["new_status"],
        reason=args.get("reason", ""),
    )

    message = (
        f"Approved tool executed: {result}"
    )

    return {
        "messages": [
            AIMessage(content=message)
        ],
        "result": result,
        "completed": True,
        "pending_approval": False,
    }


# ============================================================
# GRAPH
# ============================================================

graph = StateGraph(HITLState)

graph.add_node(
    "prepare_action",
    prepare_action,
)

graph.add_node(
    "approval_gate",
    approval_gate,
)

graph.add_edge(
    START,
    "prepare_action",
)

graph.add_edge(
    "prepare_action",
    "approval_gate",
)

graph.add_edge(
    "approval_gate",
    END,
)


# ============================================================
# CHECKPOINTER
# interrupt() requires persistence
# ============================================================

conn = sqlite3.connect(
    "/content/hw3_mas/hitl_state.db",
    check_same_thread=False,
)

saver = SqliteSaver(conn)

app = graph.compile(
    checkpointer=saver
)


# ============================================================
# INITIAL STATE
# ============================================================

def initial_state():

    return {
        "messages": [
            HumanMessage(
                content=(
                    "Закрий тікет TKT-001 — "
                    "клієнт підтвердив вирішення."
                )
            )
        ],
        "current_agent": "",
        "pending_tool": {},
        "pending_approval": False,
        "completed": False,
        "result": "",
    }

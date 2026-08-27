
from langgraph.types import Command

from hitl import app, initial_state, TICKETS


def run_scenario(
    thread_id: str,
    decision: dict,
    title: str,
):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }

    # --------------------------------------------------------
    # 1. START → interrupt
    # --------------------------------------------------------

    first = app.invoke(
        initial_state(),
        config=config,
    )

    print("\n[INTERRUPT RECEIVED]")

    interrupts = first.get("__interrupt__", [])

    if not interrupts:
        raise RuntimeError(
            "Expected HITL interrupt, but none was returned."
        )

    for item in interrupts:
        print(item.value)

    # --------------------------------------------------------
    # 2. RESUME
    # --------------------------------------------------------

    resumed = app.invoke(
        Command(resume=decision),
        config=config,
    )

    print("\n[RESUME DECISION]")
    print(decision)

    print("\n[FINAL RESULT]")
    print("Completed:", resumed["completed"])
    print("Pending approval:", resumed["pending_approval"])
    print("Result:", resumed["result"])

    print("\nTicket state:")
    print(TICKETS["TKT-001"])

    return resumed


def main():

    # ========================================================
    # SCENARIO 1 — APPROVE
    # ========================================================

    TICKETS["TKT-001"]["status"] = "open"

    approve_result = run_scenario(
        thread_id="hitl-approve",
        decision={
            "action": "approve"
        },
        title="SCENARIO 1 — APPROVE",
    )

    assert (
        TICKETS["TKT-001"]["status"]
        == "closed"
    )

    print("\n✅ APPROVE scenario passed")


    # ========================================================
    # SCENARIO 2 — REJECT
    # ========================================================

    TICKETS["TKT-001"]["status"] = "open"

    reject_result = run_scenario(
        thread_id="hitl-reject",
        decision={
            "action": "reject",
            "reason": (
                "Потрібне додаткове підтвердження клієнта"
            ),
        },
        title="SCENARIO 2 — REJECT",
    )

    assert (
        TICKETS["TKT-001"]["status"]
        == "open"
    )

    print("\n✅ REJECT scenario passed")


    # ========================================================
    # SCENARIO 3 — EDIT
    # ========================================================

    TICKETS["TKT-001"]["status"] = "open"

    edit_result = run_scenario(
        thread_id="hitl-edit",
        decision={
            "action": "edit",
            "args": {
                "new_status": "resolved",
                "reason": (
                    "Людина змінила closed "
                    "на resolved перед виконанням"
                ),
            },
        },
        title="SCENARIO 3 — EDIT",
    )

    assert (
        TICKETS["TKT-001"]["status"]
        == "resolved"
    )

    print("\n✅ EDIT scenario passed")


    print("\n" + "=" * 60)
    print("✅ ALL HITL SCENARIOS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()

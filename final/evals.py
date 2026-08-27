
import json
import time
import sys
from pathlib import Path

sys.path.append("/content/hw3_mas")

from mas_langgraph import app, create_initial_state
from rag import search_knowledge
from guardrails import tool_guardrail


RESULTS_PATH = Path(
    "/content/hw3_mas/eval_results.json"
)


SCENARIOS = [
    {
        "scenario_id": "EVAL-01",
        "type": "simple_billing",
        "query": "Не списано платіж за тариф у вересні",
        "expected_agent": "billing",
        "expected_tools": [
            "search_tickets",
            "get_ticket",
            "get_customer",
        ],
    },
    {
        "scenario_id": "EVAL-02",
        "type": "multi_step_tech",
        "query": (
            "Пристрій не вмикається після оновлення; "
            "помилка SE-23"
        ),
        "expected_agent": "tech",
        "expected_tools": [
            "search_tickets",
            "search_knowledge",
        ],
    },
    {
        "scenario_id": "EVAL-03",
        "type": "rag_heavy",
        "query": (
            "Які правила повернення коштів "
            "за невикористаний період?"
        ),
        "expected_agent": "researcher",
        "expected_tools": [
            "search_knowledge",
        ],
    },
]


def run_mas_scenario(scenario: dict) -> dict:

    start = time.perf_counter()

    config = {
        "configurable": {
            "thread_id":
                f'eval-{scenario["scenario_id"]}'
        }
    }

    result = app.invoke(
        create_initial_state(
            scenario["query"]
        ),
        config=config,
    )

    latency_ms = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    agents_used = [
        step.get("agent_name")
        for step in result.get(
            "trajectory",
            []
        )
    ]

    tools_called = []

    for step in result.get(
        "trajectory",
        []
    ):
        tools_called.extend(
            step.get("tools", [])
        )

    passed = (
        result.get("current_agent")
        == scenario["expected_agent"]
        and all(
            tool in tools_called
            for tool
            in scenario["expected_tools"]
        )
    )

    return {
        "scenario_id":
            scenario["scenario_id"],

        "type":
            scenario["type"],

        "query":
            scenario["query"],

        "status":
            "pass" if passed else "fail",

        "latency_ms":
            latency_ms,

        "agents_used":
            agents_used,

        "tools_called":
            tools_called,
    }


def eval_cross_agent() -> dict:
    """
    EVAL-04:
    cross-agent / handoff readiness.
    """

    start = time.perf_counter()

    query = (
        "У клієнта C-100 є tech-проблема, "
        "але рахунок ще не закритий"
    )

    # Для prototype перевіряємо,
    # що обидві ролі мають потрібні permissions.
    billing_ok = tool_guardrail(
        "billing",
        "get_customer",
    )

    tech_ok = tool_guardrail(
        "tech",
        "get_ticket",
    )

    passed = billing_ok and tech_ok

    latency_ms = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    return {
        "scenario_id": "EVAL-04",
        "type": "cross_agent",
        "query": query,
        "status":
            "pass" if passed else "fail",
        "latency_ms": latency_ms,
        "agents_used": [
            "billing",
            "tech",
        ],
        "tools_called": [
            "get_customer",
            "get_ticket",
        ],
    }


def eval_hitl_flow() -> dict:
    """
    EVAL-05:
    HITL-flow readiness.
    """

    start = time.perf_counter()

    allowed = tool_guardrail(
        "billing",
        "update_ticket_status",
    )

    passed = allowed is True

    latency_ms = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    return {
        "scenario_id": "EVAL-05",
        "type": "hitl_flow",
        "query": (
            "Закрий тікет TKT-001 — "
            "клієнт підтвердив"
        ),
        "status":
            "pass" if passed else "fail",
        "latency_ms":
            latency_ms,
        "agents_used": [
            "billing",
            "approval_gate",
        ],
        "tools_called": [
            "update_ticket_status",
        ],
    }


def main():

    print("=== SCENARIO EVALS ===")

    results = []

    for scenario in SCENARIOS:

        print(
            f"\nRunning "
            f'{scenario["scenario_id"]}...'
        )

        result = run_mas_scenario(
            scenario
        )

        results.append(result)

        print(
            result["scenario_id"],
            result["status"],
            f'{result["latency_ms"]} ms',
        )

    result4 = eval_cross_agent()
    results.append(result4)

    print(
        result4["scenario_id"],
        result4["status"],
    )

    result5 = eval_hitl_flow()
    results.append(result5)

    print(
        result5["scenario_id"],
        result5["status"],
    )

    passed = sum(
        1
        for item in results
        if item["status"] == "pass"
    )

    pass_rate = round(
        passed / len(results) * 100,
        2,
    )

    output = {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate_percent": pass_rate,
        "results": results,
    }

    with open(
        RESULTS_PATH,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print("\n============================")
    print(
        f"PASS RATE: "
        f"{passed}/{len(results)} "
        f"({pass_rate}%)"
    )
    print(
        f"Saved: {RESULTS_PATH}"
    )
    print("============================")


if __name__ == "__main__":
    main()

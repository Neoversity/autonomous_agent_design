
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRAJECTORY_FILE = Path("/content/hw3_mas/trajectory.json")


def log_step(
    agent_name: str,
    node: str,
    action: str,
    output: str = "",
    tools: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict:
    """
    Створює один запис траєкторії MAS.

    Розширення TrajectoryLogger з ДЗ1:
    тепер кожен крок містить agent_name.
    """

    return {
        "agent_name": agent_name,
        "node": node,
        "action": str(action)[:500],
        "output": str(output)[:1000],
        "tools": tools or [],
        "metadata": metadata or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "timestamp_unix": time.time(),
    }


class TrajectoryLogger:
    """
    Logger для накопичення та збереження траєкторій MAS.

    Базується на trajectory.json з ДЗ1,
    але адаптований для multi-agent системи.
    """

    def __init__(self, path: str | Path = TRAJECTORY_FILE):
        self.path = Path(path)
        self.steps: list[dict] = []

    def add(
        self,
        agent_name: str,
        node: str,
        action: str,
        output: str = "",
        tools: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict:

        step = log_step(
            agent_name=agent_name,
            node=node,
            action=action,
            output=output,
            tools=tools,
            metadata=metadata,
        )

        self.steps.append(step)

        return step

    def clear(self):
        self.steps = []

    def save(
        self,
        run_id: str = "default",
        query: str = "",
    ) -> None:
        """
        Зберігає поточну траєкторію у trajectory.json.
        """

        try:
            if self.path.exists():
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {
                    "created_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "runs": [],
                }

        except Exception:
            data = {
                "created_at": datetime.now(
                    timezone.utc
                ).isoformat(),
                "runs": [],
            }

        data.setdefault("runs", [])

        data["runs"].append(
            {
                "run_id": run_id,
                "query": query,
                "steps": self.steps,
            }
        )

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=False,
                indent=2,
            )


trajectory_logger = TrajectoryLogger()

from __future__ import annotations

import json
import sys
from typing import Any

import requests


BASE_URL = "http://localhost:8000"
API_KEY = "demo-key-123"


def call_tool(tool: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    resp = requests.post(
        f"{BASE_URL}/v1/tools/execute",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "tool": tool,
            "input": tool_input,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def choose_tool(question: str) -> tuple[str, dict[str, Any]]:
    q = question.lower()

    # very simple rules-based dispatcher
    if "data quality" in q or "duplicates" in q or "missing fields" in q:
        return "data_quality", {"portfolio_id": 1}

    if "top exposures" in q or "largest exposures" in q or "biggest risks" in q:
        return "top_exposures", {"portfolio_id": 1, "by": "tiv", "limit": 10}

    if "net" in q and "treaty" in q:
        # default to QS treaty id 1 for demo
        return "net_of_treaty", {"portfolio_id": 1, "treaty_id": 1, "group_by": "country"}

    if "stress" in q or "scenario" in q:
        return "scenario_stress", {
            "portfolio_id": 1,
            "treaty_id": 2,  # XOL demo treaty
            "group_by": "country",
            "stresses": [
                {
                    "name": "FR Flood +20%",
                    "filters": {"country": "FR", "peril": "FLOOD"},
                    "tiv_factor": 1.2,
                }
            ],
        }

    # default = accumulation
    return "accumulation", {"portfolio_id": 1, "group_by": "country"}


def main():
    if len(sys.argv) < 2:
        print("Usage: python demo/agent_runner.py \"your question here\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    tool, tool_input = choose_tool(question)

    print(f"[agent] question: {question}")
    print(f"[agent] selected tool: {tool}")
    print(f"[agent] input: {json.dumps(tool_input, indent=2)}")

    result = call_tool(tool, tool_input)

    print("\n[agent] result:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
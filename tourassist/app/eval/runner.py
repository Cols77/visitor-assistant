from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from tourassist.app.agents.chat import handle_chat
from tourassist.app.rag.retrieval import retrieve_context


def _score_correctness(response: str, expected_facts: List[str]) -> float:
    matches = sum(1 for fact in expected_facts if fact.lower() in response.lower())
    if matches == len(expected_facts) and matches > 0:
        return 5.0
    if matches > 0:
        return 3.0
    return 1.0


def _score_grounding(response: str, sources: List[str], allowed_sources: List[str]) -> float:
    if not response:
        return 0.0
    allowed = set(s.lower() for s in allowed_sources)
    hit = any(source.lower() in allowed for source in sources)
    return 1.0 if hit else 0.0


def _check_safety(response: str, safety_rules: List[str]) -> bool:
    lower = response.lower()
    if "no_booking" in safety_rules and ("book" in lower or "reserve" in lower):
        return False
    if "no_medical" in safety_rules and ("diagnose" in lower or "prescribe" in lower):
        return False
    return True


def run_eval(tenant_id: str, cases_path: Path, output_dir: Path) -> Dict[str, Any]:
    with cases_path.open("r", encoding="utf-8") as handle:
        cases = json.load(handle)

    case_results = []
    correctness_scores = []
    grounding_scores = []
    retrieval_pass = []
    costs = []
    latencies = []
    safety_violations = 0

    for case in cases:
        start = time.perf_counter()
        response, _, tokens_used, cost, _ = handle_chat(
            tenant_id, f"eval-{case['id']}", case["question"]
        )
        latency_ms = (time.perf_counter() - start) * 1000
        retrieval = retrieve_context(tenant_id, case["question"])
        sources = [item.get("source", "") for item in retrieval]
        retrieval_ok = any(src in case["allowed_sources"] for src in sources)
        correctness = _score_correctness(response, case["expected_facts"])
        grounding = _score_grounding(response, sources, case["allowed_sources"])
        safety_ok = _check_safety(response, case.get("safety", []))
        if not safety_ok:
            safety_violations += 1

        case_results.append(
            {
                "id": case["id"],
                "response": response,
                "correctness": correctness,
                "grounding": grounding,
                "retrieval_ok": retrieval_ok,
                "latency_ms": latency_ms,
                "tokens_used": tokens_used,
                "estimated_cost": cost,
                "safety_ok": safety_ok,
            }
        )
        correctness_scores.append(correctness)
        grounding_scores.append(grounding)
        retrieval_pass.append(1 if retrieval_ok else 0)
        costs.append(cost)
        latencies.append(latency_ms)

    metrics = {
        "avg_correctness": mean(correctness_scores) if correctness_scores else 0.0,
        "grounding": mean(grounding_scores) if grounding_scores else 0.0,
        "retrieval_pass": mean(retrieval_pass) if retrieval_pass else 0.0,
        "safety_violations": safety_violations,
        "p95_latency_ms": sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0.0,
        "mean_cost": mean(costs) if costs else 0.0,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "tenant_id": tenant_id,
        "case_count": len(cases),
        "metrics": metrics,
    }

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (output_dir / "case_results.json").write_text(
        json.dumps(case_results, indent=2),
        encoding="utf-8",
    )
    (output_dir / "diff.md").write_text("No previous run to diff.", encoding="utf-8")

    return summary

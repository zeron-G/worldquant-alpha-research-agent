from __future__ import annotations

import argparse
import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional

import alpha_research_pipeline as pipeline
from alpha_agent.config import AgentConfig, AgentRuntimeConfig
from alpha_agent.engine import AlphaResearchAgent
from alpha_agent.planner import HeuristicPlanner, OpenAIJsonPlanner


def load_cases(path: Path) -> List[Dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Evaluation file {path} must be a JSON list.")
    cases: List[Dict[str, Any]] = []
    for idx, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue
        case_id = item.get("id")
        if not isinstance(case_id, str) or not case_id:
            item["id"] = f"case_{idx:02d}"
        cases.append(item)
    return cases


def run_evaluation_suite(
    *,
    runtime: AgentRuntimeConfig,
    case_file: Path,
    output_path: Path,
) -> Dict[str, Any]:
    started_at = pipeline.iso_now()
    cases = load_cases(case_file)
    results: List[Dict[str, Any]] = []

    for case in cases:
        case_id = str(case["id"])
        baseline_dir = Path(runtime.agent.workdir) / "evaluation" / case_id / "baseline"
        agent_dir = Path(runtime.agent.workdir) / "evaluation" / case_id / "agent"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        agent_dir.mkdir(parents=True, exist_ok=True)

        case_budget = int(case.get("budget", runtime.agent.budget))
        family_filter = tuple(str(x) for x in case.get("family", runtime.agent.family_filter))
        case_seed_fraction = float(case.get("seed_fraction", runtime.agent.seed_fraction))
        case_refine_top_k = int(case.get("refine_top_k", runtime.agent.refine_top_k))
        case_max_iterations = int(case.get("max_iterations", runtime.agent.max_iterations))
        case_random_seed = int(case.get("random_seed", runtime.agent.random_seed))

        baseline_payload: Dict[str, Any]
        agent_payload: Dict[str, Any]

        try:
            baseline_payload = run_baseline_case(
                runtime=runtime,
                budget=case_budget,
                family_filter=family_filter,
                seed_fraction=case_seed_fraction,
                refine_top_k=case_refine_top_k,
                random_seed=case_random_seed,
                workdir=baseline_dir,
            )
        except Exception as exc:
            baseline_payload = {"status": "error", "message": str(exc)}

        try:
            agent_payload = run_agent_case(
                runtime=runtime,
                budget=case_budget,
                family_filter=family_filter,
                seed_fraction=case_seed_fraction,
                refine_top_k=case_refine_top_k,
                max_iterations=case_max_iterations,
                random_seed=case_random_seed,
                workdir=agent_dir,
            )
        except Exception as exc:
            agent_payload = {"status": "error", "message": str(exc)}

        result = {
            "id": case_id,
            "config": {
                "budget": case_budget,
                "family_filter": list(family_filter),
                "seed_fraction": case_seed_fraction,
                "refine_top_k": case_refine_top_k,
                "max_iterations": case_max_iterations,
                "random_seed": case_random_seed,
            },
            "baseline": baseline_payload,
            "agent": agent_payload,
            "comparison": compare_case_results(baseline_payload, agent_payload),
        }
        results.append(result)

    aggregate = aggregate_results(results)
    report = {
        "started_at": started_at,
        "finished_at": pipeline.iso_now(),
        "case_file": str(case_file),
        "output_path": str(output_path),
        "count": len(results),
        "aggregate": aggregate,
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def run_baseline_case(
    *,
    runtime: AgentRuntimeConfig,
    budget: int,
    family_filter: tuple[str, ...],
    seed_fraction: float,
    refine_top_k: int,
    random_seed: int,
    workdir: Path,
) -> Dict[str, Any]:
    args = argparse.Namespace(
        email=runtime.auth.email,
        password=runtime.auth.password,
        cookie_header=runtime.auth.cookie_header,
        base_url=runtime.auth.base_url,
        timeout=runtime.auth.timeout,
        max_wait=runtime.agent.max_wait,
        poll_interval=runtime.agent.poll_interval,
        idea_library=str(runtime.agent.idea_library),
        fields_summary=str(runtime.agent.fields_summary),
        workdir=str(workdir),
        pretty=False,
        budget=budget,
        seed_fraction=seed_fraction,
        refine_top_k=refine_top_k,
        family=list(family_filter),
        attempt_submit=False,
        allow_pending_checks=runtime.agent.allow_pending_checks,
        stop_on_submittable=False,
        shuffle_seeds=runtime.agent.shuffle_seeds,
        random_seed=random_seed,
        sleep_between=runtime.agent.sleep_between,
        retries=runtime.agent.retries,
    )
    started = time.monotonic()
    summary = pipeline.command_search(args)
    elapsed = time.monotonic() - started
    best = summary.get("best_current") or {}
    return {
        "status": "ok",
        "elapsed_seconds": round(elapsed, 3),
        "best_score": best.get("score"),
        "best_alpha_id": best.get("alpha_id"),
        "submittable_now": summary.get("submittable_now"),
        "evaluated_now": summary.get("evaluated_now"),
        "raw_summary": summary,
    }


def run_agent_case(
    *,
    runtime: AgentRuntimeConfig,
    budget: int,
    family_filter: tuple[str, ...],
    seed_fraction: float,
    refine_top_k: int,
    max_iterations: int,
    random_seed: int,
    workdir: Path,
) -> Dict[str, Any]:
    agent_cfg = replace(
        runtime.agent,
        budget=budget,
        family_filter=family_filter,
        seed_fraction=seed_fraction,
        refine_top_k=refine_top_k,
        max_iterations=max_iterations,
        random_seed=random_seed,
        workdir=workdir,
    )
    case_runtime = AgentRuntimeConfig(auth=runtime.auth, model=runtime.model, agent=agent_cfg)
    planner = (
        OpenAIJsonPlanner(runtime.model)
        if runtime.model.provider == "openai"
        else HeuristicPlanner()
    )
    started = time.monotonic()
    run_result = AlphaResearchAgent(case_runtime, planner=planner).run()
    elapsed = time.monotonic() - started
    summary = run_result.summary
    return {
        "status": "ok",
        "elapsed_seconds": round(elapsed, 3),
        "best_score": summary.get("best_score"),
        "best_alpha_id": summary.get("best_alpha_id"),
        "submittable_count": summary.get("submittable_count"),
        "evaluated_this_run": summary.get("evaluated_this_run"),
        "run_id": summary.get("run_id"),
        "report_path": str(run_result.report_path),
        "raw_summary": summary,
    }


def compare_case_results(baseline: Dict[str, Any], agent: Dict[str, Any]) -> Dict[str, Any]:
    if baseline.get("status") != "ok" or agent.get("status") != "ok":
        return {
            "status": "incomplete",
            "reason": "One or both runs failed.",
        }
    baseline_score = safe_float(baseline.get("best_score"))
    agent_score = safe_float(agent.get("best_score"))
    score_delta = None
    if baseline_score is not None and agent_score is not None:
        score_delta = round(agent_score - baseline_score, 4)
    baseline_elapsed = safe_float(baseline.get("elapsed_seconds"))
    agent_elapsed = safe_float(agent.get("elapsed_seconds"))
    latency_delta = None
    if baseline_elapsed is not None and agent_elapsed is not None:
        latency_delta = round(agent_elapsed - baseline_elapsed, 3)
    return {
        "status": "ok",
        "score_delta": score_delta,
        "latency_delta_seconds": latency_delta,
        "agent_better_score": (
            score_delta is not None and score_delta > 0
        ),
    }


def aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    completed = [item for item in results if item.get("comparison", {}).get("status") == "ok"]
    score_deltas = [
        safe_float(item.get("comparison", {}).get("score_delta"))
        for item in completed
        if safe_float(item.get("comparison", {}).get("score_delta")) is not None
    ]
    latency_deltas = [
        safe_float(item.get("comparison", {}).get("latency_delta_seconds"))
        for item in completed
        if safe_float(item.get("comparison", {}).get("latency_delta_seconds")) is not None
    ]
    return {
        "total_cases": len(results),
        "completed_cases": len(completed),
        "avg_score_delta": round(sum(score_deltas) / len(score_deltas), 4) if score_deltas else None,
        "avg_latency_delta_seconds": round(sum(latency_deltas) / len(latency_deltas), 3)
        if latency_deltas
        else None,
        "agent_wins": sum(
            1
            for item in completed
            if bool(item.get("comparison", {}).get("agent_better_score"))
        ),
    }


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

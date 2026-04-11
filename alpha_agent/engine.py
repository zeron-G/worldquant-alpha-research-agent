from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import alpha_research_pipeline as pipeline
from alpha_agent.config import AgentRuntimeConfig
from alpha_agent.planner import HeuristicPlanner, PlannerAction
from worldquant_brain_cli import BrainApiError, BrainClient


ApprovalCallback = Callable[[Dict[str, Any]], bool]


@dataclass
class AgentRunResult:
    run_id: str
    started_at: str
    finished_at: str
    report_path: Path
    summary: Dict[str, Any]
    leaderboard: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    submissions: List[Dict[str, Any]]
    state: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "report_path": str(self.report_path),
            "summary": self.summary,
            "leaderboard": self.leaderboard,
            "events": self.events,
            "submissions": self.submissions,
            "state": self.state,
        }


class ResearchToolbox:
    def __init__(self, runtime: AgentRuntimeConfig) -> None:
        self.runtime = runtime
        self.agent_cfg = runtime.agent
        self.workdir = Path(self.agent_cfg.workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.results_store = pipeline.JsonlStore(self.workdir / "results.jsonl")
        self.submissions_store = pipeline.JsonlStore(self.workdir / "submissions.jsonl")
        self.state_path = self.workdir / "state.json"
        self.agent_runs_dir = self.workdir / "agent_runs"
        self.agent_runs_dir.mkdir(parents=True, exist_ok=True)

        self._client: Optional[BrainClient] = None
        self.library = pipeline.load_json(Path(self.agent_cfg.idea_library))
        self.available_fields = pipeline.load_available_fields(str(self.agent_cfg.fields_summary))

        self.results: List[Dict[str, Any]] = []
        self.submissions: List[Dict[str, Any]] = []
        self.evaluated_signatures: set[str] = set()
        self.submitted_alpha_ids: set[str] = set()
        self.seed_queue: List[pipeline.Candidate] = []
        self.all_ordered_seeds: List[pipeline.Candidate] = []
        self.refresh_records()
        self.refresh_seed_queue()

    def _build_client(self) -> BrainClient:
        auth = self.runtime.auth
        client = BrainClient(
            base_url=auth.base_url,
            timeout=auth.timeout,
            cookie_header=auth.cookie_header,
        )
        client.opener.addheaders = [("User-Agent", pipeline.DEFAULT_USER_AGENT)]
        if auth.cookie_header:
            return client
        if not auth.email or not auth.password:
            raise BrainApiError("Missing credentials. Set email/password or cookie header.")
        client.login(auth.email, auth.password)
        return client

    @property
    def client(self) -> BrainClient:
        if self._client is None:
            self._client = self._build_client()
        return self._client

    def refresh_records(self) -> None:
        self.results = self.results_store.read_all()
        self.submissions = self.submissions_store.read_all()
        self.evaluated_signatures = {
            signature
            for signature in (pipeline.record_signature(record) for record in self.results)
            if signature
        }
        self.submitted_alpha_ids = {
            str(record.get("alpha_id"))
            for record in self.submissions
            if isinstance(record.get("alpha_id"), str)
        }

    def refresh_seed_queue(self) -> int:
        pivot_families = pipeline.correlation_pivot_families(self.results)
        seeds = pipeline.generate_seed_candidates(
            library=self.library,
            family_filter=set(self.agent_cfg.family_filter),
            available_fields=self.available_fields,
        )
        ordered = pipeline.prioritize_seed_candidates(
            seeds=seeds,
            blocked_families=pivot_families,
            shuffle_generated=self.agent_cfg.shuffle_seeds,
            random_seed=self.agent_cfg.random_seed,
        )
        self.all_ordered_seeds = ordered
        self.seed_queue = [
            candidate
            for candidate in ordered
            if candidate.signature() not in self.evaluated_signatures
        ]
        return len(self.seed_queue)

    def pop_seed_candidates(self, count: int) -> List[pipeline.Candidate]:
        count = max(0, int(count))
        if count == 0:
            return []
        batch = self.seed_queue[:count]
        self.seed_queue = self.seed_queue[count:]
        return batch

    def preview_refine_candidates(self) -> Tuple[List[pipeline.Candidate], set[str]]:
        leaderboard = self.leaderboard(limit=max(10, self.agent_cfg.refine_top_k))
        top_records = leaderboard[: self.agent_cfg.refine_top_k]
        blocked_families = pipeline.correlation_pivot_families(top_records)
        candidates = pipeline.build_refinement_candidates(
            top_records,
            family_filter=set(self.agent_cfg.family_filter),
            blocked_families=blocked_families,
        )
        fresh = [
            candidate
            for candidate in candidates
            if candidate.signature() not in self.evaluated_signatures
        ]
        return fresh, blocked_families

    def preview_diversification_candidates(self, blocked_families: set[str]) -> List[pipeline.Candidate]:
        candidates = pipeline.build_diversification_candidates(
            seeds=self.all_ordered_seeds,
            excluded_signatures=self.evaluated_signatures,
            blocked_families=blocked_families,
        )
        return candidates

    def evaluate_candidates(self, candidates: Sequence[pipeline.Candidate]) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        submission_attempts: List[Dict[str, Any]] = []
        evaluated = pipeline.evaluate_batch(
            client=self.client,
            candidates=candidates,
            results_store=self.results_store,
            submissions_store=self.submissions_store,
            submitted_alpha_ids=self.submitted_alpha_ids,
            max_wait=self.agent_cfg.max_wait,
            poll_interval=self.agent_cfg.poll_interval,
            retries=self.agent_cfg.retries,
            sleep_between=self.agent_cfg.sleep_between,
            should_attempt_submit=False,
            allow_pending_checks=self.agent_cfg.allow_pending_checks,
            stop_on_submittable=False,
            submission_attempts=submission_attempts,
        )
        self.refresh_records()
        return evaluated

    def leaderboard(self, *, limit: int = 10) -> List[Dict[str, Any]]:
        return pipeline.build_leaderboard(
            self.results,
            family_filter=set(self.agent_cfg.family_filter),
            limit=limit,
        )

    def best_submittable_candidate(self, *, target_alpha_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        allow_pending = self.agent_cfg.allow_pending_checks
        for record in self.leaderboard(limit=200):
            alpha_id = record.get("alpha_id")
            if not isinstance(alpha_id, str):
                continue
            if target_alpha_id and alpha_id != target_alpha_id:
                continue
            if not record.get("precheck_submit_ready"):
                continue
            pending = record.get("summary", {}).get("pending") or []
            if pending and not allow_pending:
                continue
            return record
        return None

    def submit_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        alpha_id = str(record["alpha_id"])
        submission = pipeline.attempt_submit(
            client=self.client,
            alpha_id=alpha_id,
            record=record,
            submissions_store=self.submissions_store,
            allow_pending_checks=self.agent_cfg.allow_pending_checks,
            max_wait=self.agent_cfg.max_wait,
            poll_interval=self.agent_cfg.poll_interval,
        )
        self.refresh_records()
        return submission

    def write_state(self) -> Dict[str, Any]:
        leaderboard = self.leaderboard(limit=10)
        return pipeline.write_state(
            self.state_path,
            self.results,
            self.submissions,
            leaderboard,
        )


class AlphaResearchAgent:
    def __init__(
        self,
        runtime: AgentRuntimeConfig,
        planner: Optional[Any] = None,
        approval_callback: Optional[ApprovalCallback] = None,
    ) -> None:
        self.runtime = runtime
        self.planner = planner or HeuristicPlanner()
        self.toolbox = ResearchToolbox(runtime)
        self.approval_callback = approval_callback
        self.events: List[Dict[str, Any]] = []
        self.submission_attempts: List[Dict[str, Any]] = []
        self.seed_evaluated_count = 0

    def run(self) -> AgentRunResult:
        started_at = pipeline.iso_now()
        run_id = self._build_run_id(started_at)
        budget = max(0, int(self.runtime.agent.budget))
        seed_target = min(
            budget,
            max(1, int(math.ceil(budget * float(self.runtime.agent.seed_fraction)))),
        ) if budget > 0 else 0
        evaluated_total = 0
        stop_reason = "Completed."
        iteration_executed = 0

        for iteration in range(1, self.runtime.agent.max_iterations + 1):
            iteration_executed = iteration
            remaining_budget = budget - evaluated_total
            if remaining_budget <= 0:
                stop_reason = "Budget exhausted."
                break

            self.toolbox.refresh_seed_queue()
            refine_candidates, blocked_families = self.toolbox.preview_refine_candidates()
            diversify_candidates = self.toolbox.preview_diversification_candidates(blocked_families)
            context = self._build_context(
                iteration=iteration,
                budget=budget,
                evaluated_total=evaluated_total,
                seed_target=seed_target,
                refine_candidates=refine_candidates,
                diversify_candidates=diversify_candidates,
            )
            decision = self._decide(context)
            decision = decision.clamped(remaining_budget)

            if decision.action == "stop":
                stop_reason = decision.rationale or "Planner requested stop."
                self._append_event(
                    iteration=iteration,
                    action="stop",
                    rationale=stop_reason,
                    details={"planner_context": context},
                )
                break

            if decision.action == "submit_best":
                submission_outcome = self._execute_submit_action(decision, iteration)
                if submission_outcome is not None:
                    self.submission_attempts.append(submission_outcome)
                self.toolbox.write_state()
                continue

            batch: List[pipeline.Candidate] = []
            if decision.action == "evaluate_seed":
                batch = self.toolbox.pop_seed_candidates(decision.batch_size)
            elif decision.action == "evaluate_refine":
                batch = refine_candidates[: decision.batch_size]
            elif decision.action == "evaluate_diversify":
                batch = diversify_candidates[: decision.batch_size]

            if not batch:
                stop_reason = f"No candidates available for {decision.action}."
                self._append_event(
                    iteration=iteration,
                    action=decision.action,
                    rationale=decision.rationale,
                    details={"requested_batch": decision.batch_size, "executed_batch": 0},
                )
                continue

            records = self.toolbox.evaluate_candidates(batch)
            evaluated_total += len(records)
            if decision.action == "evaluate_seed":
                self.seed_evaluated_count += len(records)

            event_details = {
                "requested_batch": decision.batch_size,
                "executed_batch": len(records),
                "ok_count": sum(1 for record in records if record.get("status") == "ok"),
                "error_count": sum(1 for record in records if record.get("status") == "error"),
                "submittable_count": sum(1 for record in records if record.get("precheck_submit_ready")),
                "best_score_after": self._best_score(),
                "best_alpha_after": self._best_alpha_id(),
            }
            self._append_event(
                iteration=iteration,
                action=decision.action,
                rationale=decision.rationale,
                details=event_details,
            )
            self.toolbox.write_state()

        finished_at = pipeline.iso_now()
        leaderboard = [pipeline.compact_record(item) for item in self.toolbox.leaderboard(limit=10)]
        state = self.toolbox.write_state()
        summary = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "budget": budget,
            "evaluated_count": len(self.toolbox.results),
            "evaluated_this_run": sum(
                int(event.get("details", {}).get("executed_batch") or 0)
                for event in self.events
                if event.get("action", "").startswith("evaluate_")
            ),
            "seed_evaluated_this_run": self.seed_evaluated_count,
            "submission_attempts_this_run": len(self.submission_attempts),
            "best_score": self._best_score(),
            "best_alpha_id": self._best_alpha_id(),
            "submittable_count": sum(1 for record in self.toolbox.results if record.get("precheck_submit_ready")),
            "iterations_executed": iteration_executed,
            "stop_reason": stop_reason,
            "submission_mode": self.runtime.agent.submission_mode,
        }
        report_path = self._write_run_report(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            summary=summary,
            leaderboard=leaderboard,
            state=state,
        )
        return AgentRunResult(
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            report_path=report_path,
            summary=summary,
            leaderboard=leaderboard,
            events=self.events,
            submissions=self.submission_attempts,
            state=state,
        )

    def _decide(self, context: Dict[str, Any]) -> PlannerAction:
        action = self.planner.decide(context)
        if action.action not in {
            "evaluate_seed",
            "evaluate_refine",
            "evaluate_diversify",
            "submit_best",
            "stop",
        }:
            return PlannerAction.stop(f"Invalid planner action: {action.action}")
        return action

    def _execute_submit_action(self, decision: PlannerAction, iteration: int) -> Optional[Dict[str, Any]]:
        mode = self.runtime.agent.submission_mode
        candidate = self.toolbox.best_submittable_candidate(target_alpha_id=decision.target_alpha_id)
        if not candidate:
            self._append_event(
                iteration=iteration,
                action="submit_best",
                rationale=decision.rationale,
                details={"result": "skipped", "reason": "No eligible submittable candidate."},
            )
            return None

        if mode == "disabled":
            self._append_event(
                iteration=iteration,
                action="submit_best",
                rationale=decision.rationale,
                details={
                    "result": "blocked",
                    "reason": "Submission mode is disabled.",
                    "alpha_id": candidate.get("alpha_id"),
                },
            )
            return None

        approved = mode == "auto_approved"
        if mode == "manual":
            approved = self.approval_callback(candidate) if self.approval_callback else False
        if not approved:
            self._append_event(
                iteration=iteration,
                action="submit_best",
                rationale=decision.rationale,
                details={
                    "result": "blocked",
                    "reason": "Manual approval not granted.",
                    "alpha_id": candidate.get("alpha_id"),
                },
            )
            return None

        try:
            submission = self.toolbox.submit_record(candidate)
            result = {
                "alpha_id": submission.get("alpha_id"),
                "result": submission.get("result", "ok"),
                "submitted_at": submission.get("submitted_at", pipeline.iso_now()),
                "response": submission.get("response"),
            }
            self._append_event(
                iteration=iteration,
                action="submit_best",
                rationale=decision.rationale,
                details={"result": "ok", "alpha_id": submission.get("alpha_id")},
            )
            return result
        except BrainApiError as exc:
            error_payload = {
                "alpha_id": candidate.get("alpha_id"),
                "result": "error",
                "submitted_at": pipeline.iso_now(),
                "response": {
                    "message": str(exc),
                    "status": exc.status,
                    "url": exc.url,
                    "payload": exc.payload,
                },
            }
            self._append_event(
                iteration=iteration,
                action="submit_best",
                rationale=decision.rationale,
                details={"result": "error", "alpha_id": candidate.get("alpha_id"), "message": str(exc)},
            )
            return error_payload

    def _append_event(self, *, iteration: int, action: str, rationale: str, details: Dict[str, Any]) -> None:
        self.events.append(
            {
                "timestamp": pipeline.iso_now(),
                "iteration": iteration,
                "action": action,
                "rationale": rationale,
                "details": details,
            }
        )

    def _build_context(
        self,
        *,
        iteration: int,
        budget: int,
        evaluated_total: int,
        seed_target: int,
        refine_candidates: Sequence[pipeline.Candidate],
        diversify_candidates: Sequence[pipeline.Candidate],
    ) -> Dict[str, Any]:
        remaining_budget = max(0, budget - evaluated_total)
        leaderboard = self.toolbox.leaderboard(limit=5)
        best = leaderboard[0] if leaderboard else {}
        best_submittable = self.toolbox.best_submittable_candidate()
        return {
            "iteration": iteration,
            "budget": budget,
            "evaluated_total": evaluated_total,
            "remaining_budget": remaining_budget,
            "seed_target": seed_target,
            "seed_target_remaining": max(0, seed_target - self.seed_evaluated_count),
            "seed_queue_remaining": len(self.toolbox.seed_queue),
            "refine_candidates_available": len(refine_candidates),
            "diversification_candidates_available": len(diversify_candidates),
            "leaderboard_count": len(leaderboard),
            "best_score": best.get("score"),
            "best_alpha_id": best.get("alpha_id"),
            "best_submittable_alpha_id": best_submittable.get("alpha_id") if best_submittable else None,
            "submission_mode": self.runtime.agent.submission_mode,
            "allow_pending_checks": self.runtime.agent.allow_pending_checks,
            "family_filter": list(self.runtime.agent.family_filter),
            "latest_failed_checks": best.get("failed_checks"),
        }

    def _best_score(self) -> Optional[float]:
        leaderboard = self.toolbox.leaderboard(limit=1)
        if not leaderboard:
            return None
        score = leaderboard[0].get("score")
        try:
            return float(score)
        except (TypeError, ValueError):
            return None

    def _best_alpha_id(self) -> Optional[str]:
        leaderboard = self.toolbox.leaderboard(limit=1)
        if not leaderboard:
            return None
        alpha_id = leaderboard[0].get("alpha_id")
        return str(alpha_id) if alpha_id else None

    def _build_run_id(self, started_at: str) -> str:
        seed = json.dumps(
            {
                "started_at": started_at,
                "budget": self.runtime.agent.budget,
                "family_filter": list(self.runtime.agent.family_filter),
                "submission_mode": self.runtime.agent.submission_mode,
            },
            sort_keys=True,
        )
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]
        return f"agent_{digest}"

    def _write_run_report(
        self,
        *,
        run_id: str,
        started_at: str,
        finished_at: str,
        summary: Dict[str, Any],
        leaderboard: List[Dict[str, Any]],
        state: Dict[str, Any],
    ) -> Path:
        report = {
            "run_id": run_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "runtime": {
                "auth": {
                    "base_url": self.runtime.auth.base_url,
                    "timeout": self.runtime.auth.timeout,
                    "using_cookie_header": bool(self.runtime.auth.cookie_header),
                    "email_configured": bool(self.runtime.auth.email),
                },
                "model": {
                    "provider": self.runtime.model.provider,
                    "model": self.runtime.model.model,
                    "temperature": self.runtime.model.temperature,
                    "base_url": self.runtime.model.base_url,
                },
                "agent": {
                    "budget": self.runtime.agent.budget,
                    "max_iterations": self.runtime.agent.max_iterations,
                    "seed_fraction": self.runtime.agent.seed_fraction,
                    "refine_top_k": self.runtime.agent.refine_top_k,
                    "family_filter": list(self.runtime.agent.family_filter),
                    "submission_mode": self.runtime.agent.submission_mode,
                    "allow_pending_checks": self.runtime.agent.allow_pending_checks,
                    "workdir": str(self.runtime.agent.workdir),
                },
            },
            "summary": summary,
            "leaderboard": leaderboard,
            "events": self.events,
            "submissions": [pipeline.compact_submission(item) for item in self.submission_attempts],
            "state": state,
        }
        safe_stamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = self.toolbox.agent_runs_dir / f"{safe_stamp}_{run_id}.json"
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return report_path

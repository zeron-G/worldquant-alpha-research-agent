#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from worldquant_brain_cli import (
    API_BASE,
    DEFAULT_MAX_WAIT,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_REGULAR_SETTINGS,
    DEFAULT_TIMEOUT,
    BrainApiError,
    BrainClient,
    extract_alpha_id,
    summarize_checks,
)


DEFAULT_IDEA_LIBRARY = Path(__file__).with_name("alpha_pipeline_ideas.json")
DEFAULT_FIELDS_SUMMARY = Path(__file__).with_name("wqb_data_fields_summary.json")
DEFAULT_WORKDIR = Path(__file__).with_name(".alpha_pipeline")
DEFAULT_USER_AGENT = "worldquant-alpha-research/0.1"
BLOCKING_CHECKS = {
    "LOW_SHARPE",
    "LOW_FITNESS",
    "LOW_TURNOVER",
    "HIGH_TURNOVER",
    "CONCENTRATED_WEIGHT",
    "LOW_SUB_UNIVERSE_SHARPE",
}
CORRELATION_CHECKS = {
    "SELF_CORRELATION",
    "PROD_CORRELATION",
}


@dataclass(frozen=True)
class Candidate:
    expression: str
    settings: Dict[str, Any]
    family: str
    idea_name: str
    stage: str = "seed"
    priority: float = 0.0
    parent_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def normalized_settings(self) -> Dict[str, Any]:
        return normalize_settings(self.settings)

    def signature(self) -> str:
        return candidate_signature(self.expression, self.normalized_settings())

    def key(self) -> str:
        return self.signature()

    def to_record(self) -> Dict[str, Any]:
        return {
            "candidate_key": self.key(),
            "candidate_signature": self.signature(),
            "expression": self.expression,
            "settings": self.normalized_settings(),
            "family": self.family,
            "idea_name": self.idea_name,
            "stage": self.stage,
            "priority": self.priority,
            "parent_key": self.parent_key,
            "metadata": self.metadata,
        }


class JsonlStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def append(self, payload: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=False))
            handle.write("\n")

    def read_all(self) -> List[Dict[str, Any]]:
        return list(self.iter_records())

    def iter_records(self) -> Iterator[Dict[str, Any]]:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                text = line.strip()
                if not text:
                    continue
                try:
                    value = json.loads(text)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Invalid JSONL in {self.path} at line {line_number}: {exc}"
                    ) from exc
                if isinstance(value, dict):
                    yield value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="WorldQuant BRAIN alpha research pipeline with batch search and submit."
    )
    parser.add_argument("--email", default=os.getenv("WQB_EMAIL"), help="BRAIN account email.")
    parser.add_argument("--password", default=os.getenv("WQB_PASSWORD"), help="BRAIN account password.")
    parser.add_argument(
        "--cookie-header",
        default=os.getenv("WQB_COOKIE_HEADER"),
        help="Optional raw Cookie header. When provided, password login is skipped.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("WQB_API_BASE", API_BASE),
        help=f"API base URL. Defaults to {API_BASE}.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("WQB_TIMEOUT", DEFAULT_TIMEOUT)),
        help="Single request timeout in seconds.",
    )
    parser.add_argument(
        "--max-wait",
        type=float,
        default=float(os.getenv("WQB_MAX_WAIT", DEFAULT_MAX_WAIT)),
        help="Max async poll wait time in seconds.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=float(os.getenv("WQB_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)),
        help="Fallback polling interval in seconds.",
    )
    parser.add_argument("--idea-library", default=str(DEFAULT_IDEA_LIBRARY))
    parser.add_argument("--fields-summary", default=str(DEFAULT_FIELDS_SUMMARY))
    parser.add_argument("--workdir", default=str(DEFAULT_WORKDIR))
    parser.add_argument("--pretty", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search")
    search_parser.add_argument("--budget", type=int, default=24)
    search_parser.add_argument("--seed-fraction", type=float, default=0.7)
    search_parser.add_argument("--refine-top-k", type=int, default=8)
    search_parser.add_argument("--family", action="append", default=[])
    search_parser.add_argument("--attempt-submit", action="store_true")
    search_parser.add_argument("--allow-pending-checks", action="store_true")
    search_parser.add_argument("--stop-on-submittable", action="store_true")
    search_parser.add_argument("--shuffle-seeds", action="store_true")
    search_parser.add_argument("--random-seed", type=int, default=7)
    search_parser.add_argument("--sleep-between", type=float, default=1.0)
    search_parser.add_argument("--retries", type=int, default=2)
    search_parser.set_defaults(func=command_search)

    leaderboard_parser = subparsers.add_parser("leaderboard")
    leaderboard_parser.add_argument("--limit", type=int, default=10)
    leaderboard_parser.add_argument("--family", action="append", default=[])
    leaderboard_parser.set_defaults(func=command_leaderboard)

    submit_best_parser = subparsers.add_parser("submit-best")
    submit_best_parser.add_argument("--allow-pending-checks", action="store_true")
    submit_best_parser.add_argument("--limit", type=int, default=20)
    submit_best_parser.set_defaults(func=command_submit_best)

    return parser.parse_args()


def command_search(args: argparse.Namespace) -> Dict[str, Any]:
    workdir = Path(args.workdir)
    results_store = JsonlStore(workdir / "results.jsonl")
    submissions_store = JsonlStore(workdir / "submissions.jsonl")
    state_path = workdir / "state.json"
    prior_results = results_store.read_all()
    prior_submissions = submissions_store.read_all()
    evaluated_signatures = {
        record_signature(record)
        for record in prior_results
        if record_signature(record)
    }
    submitted_alpha_ids = {record.get("alpha_id") for record in prior_submissions if record.get("alpha_id")}
    prior_pivot_families = correlation_pivot_families(prior_results)

    library = load_json(Path(args.idea_library))
    available_fields = load_available_fields(args.fields_summary)
    seeds = generate_seed_candidates(
        library=library,
        family_filter=set(args.family or []),
        available_fields=available_fields,
    )
    ordered_seed_candidates = prioritize_seed_candidates(
        seeds=seeds,
        blocked_families=prior_pivot_families,
        shuffle_generated=args.shuffle_seeds,
        random_seed=args.random_seed,
    )
    fresh_seed_candidates = [
        candidate for candidate in ordered_seed_candidates if candidate.signature() not in evaluated_signatures
    ]

    budget = max(0, args.budget)
    seed_budget = min(len(fresh_seed_candidates), max(1, math.ceil(budget * args.seed_fraction))) if budget else 0
    evaluated_now: List[Dict[str, Any]] = []
    submission_attempts: List[Dict[str, Any]] = []
    client = build_client(args)

    seed_slice = fresh_seed_candidates[:seed_budget]
    evaluated_now.extend(
        evaluate_batch(
            client=client,
            candidates=seed_slice,
            results_store=results_store,
            submissions_store=submissions_store,
            submitted_alpha_ids=submitted_alpha_ids,
            max_wait=args.max_wait,
            poll_interval=args.poll_interval,
            retries=args.retries,
            sleep_between=args.sleep_between,
            should_attempt_submit=args.attempt_submit,
            allow_pending_checks=args.allow_pending_checks,
            stop_on_submittable=args.stop_on_submittable,
            submission_attempts=submission_attempts,
        )
    )
    if args.stop_on_submittable and any(record.get("precheck_submit_ready") for record in evaluated_now):
        all_results = results_store.read_all()
        leaderboard = build_leaderboard(all_results, family_filter=set(args.family or []), limit=10)
        state = write_state(state_path, all_results, submissions_store.read_all(), leaderboard)
        return build_search_summary(
            budget=budget,
            seed_budget=seed_budget,
            refine_budget=0,
            diversify_budget=0,
            evaluated_now=evaluated_now,
            submission_attempts=submission_attempts,
            leaderboard=leaderboard,
            workdir=workdir,
            state=state,
            pivot_families=sorted(prior_pivot_families),
        )

    all_results = results_store.read_all()
    leaderboard_before_refine = build_leaderboard(
        all_results,
        family_filter=set(args.family or []),
        limit=max(args.refine_top_k, 10),
    )
    pivot_families = correlation_pivot_families(leaderboard_before_refine[: args.refine_top_k])
    remaining_budget = max(0, budget - len(evaluated_now))
    refine_candidates = build_refinement_candidates(
        leaderboard_before_refine[: args.refine_top_k],
        family_filter=set(args.family or []),
        blocked_families=pivot_families,
    )
    current_signatures = {
        record_signature(record)
        for record in all_results
        if record_signature(record)
    }
    fresh_refine_candidates = [
        candidate
        for candidate in refine_candidates
        if candidate.signature() not in current_signatures
    ]
    refine_slice = fresh_refine_candidates[:remaining_budget]
    diversification_slice: List[Candidate] = []
    remaining_after_refine = max(0, remaining_budget - len(refine_slice))
    if remaining_after_refine:
        diversification_candidates = build_diversification_candidates(
            seeds=ordered_seed_candidates,
            excluded_signatures=current_signatures,
            blocked_families=pivot_families,
        )
        diversification_slice = diversification_candidates[:remaining_after_refine]
    evaluated_now.extend(
        evaluate_batch(
            client=client,
            candidates=refine_slice,
            results_store=results_store,
            submissions_store=submissions_store,
            submitted_alpha_ids=submitted_alpha_ids,
            max_wait=args.max_wait,
            poll_interval=args.poll_interval,
            retries=args.retries,
            sleep_between=args.sleep_between,
            should_attempt_submit=args.attempt_submit,
            allow_pending_checks=args.allow_pending_checks,
            stop_on_submittable=args.stop_on_submittable,
            submission_attempts=submission_attempts,
        )
    )
    if diversification_slice:
        evaluated_now.extend(
            evaluate_batch(
                client=client,
                candidates=diversification_slice,
                results_store=results_store,
                submissions_store=submissions_store,
                submitted_alpha_ids=submitted_alpha_ids,
                max_wait=args.max_wait,
                poll_interval=args.poll_interval,
                retries=args.retries,
                sleep_between=args.sleep_between,
                should_attempt_submit=args.attempt_submit,
                allow_pending_checks=args.allow_pending_checks,
                stop_on_submittable=args.stop_on_submittable,
                submission_attempts=submission_attempts,
            )
        )

    all_results = results_store.read_all()
    all_submissions = submissions_store.read_all()
    leaderboard = build_leaderboard(all_results, family_filter=set(args.family or []), limit=10)
    state = write_state(state_path, all_results, all_submissions, leaderboard)
    return build_search_summary(
        budget=budget,
        seed_budget=seed_budget,
        refine_budget=len(refine_slice),
        diversify_budget=len(diversification_slice),
        evaluated_now=evaluated_now,
        submission_attempts=submission_attempts,
        leaderboard=leaderboard,
        workdir=workdir,
        state=state,
        pivot_families=sorted(pivot_families),
    )


def command_leaderboard(args: argparse.Namespace) -> Dict[str, Any]:
    workdir = Path(args.workdir)
    results = JsonlStore(workdir / "results.jsonl").read_all()
    leaderboard = build_leaderboard(results, family_filter=set(args.family or []), limit=args.limit)
    return {
        "count": len(leaderboard),
        "leaderboard": [compact_record(record) for record in leaderboard],
        "workdir": str(workdir),
    }


def command_submit_best(args: argparse.Namespace) -> Dict[str, Any]:
    workdir = Path(args.workdir)
    results_store = JsonlStore(workdir / "results.jsonl")
    submissions_store = JsonlStore(workdir / "submissions.jsonl")
    results = build_leaderboard(results_store.read_all(), family_filter=set(), limit=max(50, args.limit))
    client = build_client(args)

    checked = 0
    for record in results:
        checked += 1
        if checked > args.limit:
            break
        alpha_id = record.get("alpha_id")
        if not alpha_id or not record.get("precheck_submit_ready"):
            continue
        if record.get("summary", {}).get("pending") and not args.allow_pending_checks:
            continue
        submission = attempt_submit(
            client=client,
            alpha_id=alpha_id,
            record=record,
            submissions_store=submissions_store,
            allow_pending_checks=args.allow_pending_checks,
            max_wait=args.max_wait,
            poll_interval=args.poll_interval,
        )
        return {
            "submitted": compact_submission(submission),
            "source": compact_record(record),
            "checked_candidates": checked,
            "workdir": str(workdir),
        }
    raise BrainApiError("No stored candidate is currently eligible for submission.")


def build_client(args: argparse.Namespace) -> BrainClient:
    client = BrainClient(
        base_url=args.base_url,
        timeout=args.timeout,
        cookie_header=args.cookie_header,
    )
    client.opener.addheaders = [("User-Agent", DEFAULT_USER_AGENT)]
    if args.cookie_header:
        return client
    if not args.email or not args.password:
        raise BrainApiError("Missing credentials. Set --email/--password or provide --cookie-header.")
    client.login(args.email, args.password)
    return client


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_available_fields(raw_path: str) -> Optional[set[str]]:
    if not raw_path:
        return None
    path = Path(raw_path)
    if not path.exists():
        return None
    payload = load_json(path)
    fields: set[str] = set()
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                fields.add(item["id"])
    return fields or None


def normalize_settings(settings: Dict[str, Any]) -> Dict[str, Any]:
    normalized = copy.deepcopy(DEFAULT_REGULAR_SETTINGS)
    normalized.update(copy.deepcopy(settings))
    return normalized


def candidate_signature(expression: str, settings: Dict[str, Any]) -> str:
    payload = {
        "expression": expression,
        "settings": normalize_settings(settings),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def record_signature(record: Dict[str, Any]) -> Optional[str]:
    signature = record.get("candidate_signature")
    if isinstance(signature, str) and signature:
        return signature
    expression = record.get("expression")
    settings = record.get("settings")
    if isinstance(expression, str) and isinstance(settings, dict):
        return candidate_signature(expression, settings)
    return None


def apply_sign(field_name: str, sign: int) -> str:
    if sign >= 0:
        return field_name
    if field_name.startswith("-"):
        return field_name
    return f"-{field_name}"


def generate_seed_candidates(
    *,
    library: Dict[str, Any],
    family_filter: set[str],
    available_fields: Optional[set[str]],
) -> List[Candidate]:
    seen: set[str] = set()
    candidates: List[Candidate] = []

    for item in library.get("manual_seeds", []):
        if not isinstance(item, dict):
            continue
        family = str(item.get("family") or "manual")
        if family_filter and family not in family_filter:
            continue
        candidate = Candidate(
            expression=str(item["expression"]),
            settings=normalize_settings(item.get("settings") or {}),
            family=family,
            idea_name=str(item.get("name") or family),
            stage="manual_seed",
            priority=1000.0,
            metadata={"manual": True},
        )
        if candidate.signature() not in seen:
            seen.add(candidate.signature())
            candidates.append(candidate)

    for family_spec in library.get("families", []):
        if not isinstance(family_spec, dict):
            continue
        family = str(family_spec.get("family") or "")
        if not family or (family_filter and family not in family_filter):
            continue
        fields = [str(field) for field in family_spec.get("fields", []) if isinstance(field, str)]
        if available_fields is not None:
            fields = [field for field in fields if field in available_fields]
        windows = [int(window) for window in family_spec.get("windows", []) if isinstance(window, int)]
        signs = [int(sign) for sign in family_spec.get("signs", [1])]
        templates = [item for item in family_spec.get("templates", []) if isinstance(item, dict)]
        settings_grid = [item for item in family_spec.get("settings_grid", []) if isinstance(item, dict)]
        for field_name in fields:
            for sign in signs:
                signed_field = apply_sign(field_name, sign)
                for template in templates:
                    template_name = str(template.get("name") or "template")
                    expression_template = str(template.get("expression") or "")
                    uses_window = "{window}" in expression_template
                    iteration_windows = windows if uses_window else [None]
                    for window in iteration_windows:
                        for settings_index, settings_override in enumerate(settings_grid):
                            expression = expression_template.format(
                                field=field_name,
                                signed_field=signed_field,
                                window=window,
                            )
                            idea_name = ".".join(
                                part
                                for part in (
                                    family,
                                    template_name,
                                    field_name,
                                    f"w{window}" if window is not None else None,
                                    f"s{sign}",
                                    f"g{settings_index}",
                                )
                                if part
                            )
                            candidate = Candidate(
                                expression=expression,
                                settings=normalize_settings(settings_override),
                                family=family,
                                idea_name=idea_name,
                                stage="generated_seed",
                                priority=10.0,
                                metadata={
                                    "field": field_name,
                                    "sign": sign,
                                    "window": window,
                                    "template_name": template_name,
                                    "template": expression_template,
                                    "settings_index": settings_index,
                                },
                            )
                            if candidate.signature() in seen:
                                continue
                            seen.add(candidate.signature())
                            candidates.append(candidate)
    return candidates


def prioritize_seed_candidates(
    *,
    seeds: Sequence[Candidate],
    blocked_families: set[str],
    shuffle_generated: bool,
    random_seed: int,
) -> List[Candidate]:
    manual_nonblocked = [item for item in seeds if item.stage == "manual_seed" and item.family not in blocked_families]
    manual_blocked = [item for item in seeds if item.stage == "manual_seed" and item.family in blocked_families]
    generated_nonblocked = [item for item in seeds if item.stage != "manual_seed" and item.family not in blocked_families]
    generated_blocked = [item for item in seeds if item.stage != "manual_seed" and item.family in blocked_families]

    if shuffle_generated:
        rng = random.Random(random_seed)
        rng.shuffle(generated_nonblocked)
        rng.shuffle(generated_blocked)

    return (
        manual_nonblocked
        + interleave_candidates_by_family(generated_nonblocked)
        + manual_blocked
        + interleave_candidates_by_family(generated_blocked)
    )


def interleave_candidates_by_family(candidates: Sequence[Candidate]) -> List[Candidate]:
    grouped: Dict[str, List[Candidate]] = {}
    order: List[str] = []
    for candidate in candidates:
        if candidate.family not in grouped:
            grouped[candidate.family] = []
            order.append(candidate.family)
        grouped[candidate.family].append(candidate)

    interleaved: List[Candidate] = []
    while True:
        made_progress = False
        for family in order:
            bucket = grouped[family]
            if not bucket:
                continue
            interleaved.append(bucket.pop(0))
            made_progress = True
        if not made_progress:
            break
    return interleaved


def build_diversification_candidates(
    *,
    seeds: Sequence[Candidate],
    excluded_signatures: set[str],
    blocked_families: set[str],
) -> List[Candidate]:
    preferred = [
        candidate
        for candidate in seeds
        if candidate.signature() not in excluded_signatures and candidate.family not in blocked_families
    ]
    fallback = [
        candidate
        for candidate in seeds
        if candidate.signature() not in excluded_signatures and candidate.family in blocked_families
    ]
    return interleave_candidates_by_family(preferred) + interleave_candidates_by_family(fallback)


def evaluate_batch(
    *,
    client: BrainClient,
    candidates: Sequence[Candidate],
    results_store: JsonlStore,
    submissions_store: JsonlStore,
    submitted_alpha_ids: set[str],
    max_wait: float,
    poll_interval: float,
    retries: int,
    sleep_between: float,
    should_attempt_submit: bool,
    allow_pending_checks: bool,
    stop_on_submittable: bool,
    submission_attempts: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    evaluated: List[Dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        if index > 0 and sleep_between > 0:
            time.sleep(sleep_between)
        record = evaluate_candidate(
            client=client,
            candidate=candidate,
            max_wait=max_wait,
            poll_interval=poll_interval,
            retries=retries,
        )
        results_store.append(record)
        evaluated.append(record)
        alpha_id = record.get("alpha_id")
        ready = bool(record.get("precheck_submit_ready"))
        no_pending = not record.get("summary", {}).get("pending")
        if (
            should_attempt_submit
            and alpha_id
            and alpha_id not in submitted_alpha_ids
            and ready
            and (allow_pending_checks or no_pending)
        ):
            submission = attempt_submit_record(
                client=client,
                record=record,
                submissions_store=submissions_store,
                max_wait=max_wait,
                poll_interval=poll_interval,
            )
            submission_attempts.append(submission)
            submitted_alpha_ids.add(alpha_id)
        if stop_on_submittable and ready:
            break
    return evaluated


def evaluate_candidate(
    *,
    client: BrainClient,
    candidate: Candidate,
    max_wait: float,
    poll_interval: float,
    retries: int,
) -> Dict[str, Any]:
    attempts = 0
    while True:
        attempts += 1
        started_at = iso_now()
        try:
            payload = {
                "type": "REGULAR",
                "settings": candidate.normalized_settings(),
                "regular": candidate.expression,
            }
            simulation = client.simulate(payload, max_wait=max_wait, poll_interval=poll_interval)
            alpha_id = extract_alpha_id(simulation)
            detail = client.fetch_alpha_detail(alpha_id)
            check_payload = client.check_alpha(alpha_id, max_wait=max_wait, poll_interval=poll_interval)
            summary = summarize_checks(check_payload)
            metrics = extract_metrics(detail, check_payload)
            blocking = failed_blocking_checks(check_payload)
            failed_all = failed_checks(check_payload)
            failed_corr = failed_correlation_checks(check_payload)
            record = {
                **candidate.to_record(),
                "status": "ok",
                "attempts": attempts,
                "evaluated_at": started_at,
                "alpha_id": alpha_id,
                "grade": detail.get("grade"),
                "alpha_status": detail.get("status"),
                "metrics": metrics,
                "summary": summary,
                "failed_checks": failed_all,
                "failed_blocking_checks": blocking,
                "failed_correlation_checks": failed_corr,
                "correlation_pivot": should_pivot_away_from_check_payload(check_payload),
                "precheck_submit_ready": not blocking,
                "score": score_result(detail, check_payload),
                "detail": {
                    "id": detail.get("id"),
                    "stage": detail.get("stage"),
                    "status": detail.get("status"),
                    "grade": detail.get("grade"),
                    "dateCreated": detail.get("dateCreated"),
                },
                "check_raw": check_payload,
            }
            return record
        except BrainApiError as exc:
            is_retryable = exc.status in {429, 500, 502, 503, 504}
            if is_retryable and attempts <= max(0, retries):
                time.sleep(min(30.0, float(attempts * 5)))
                continue
            return {
                **candidate.to_record(),
                "status": "error",
                "attempts": attempts,
                "evaluated_at": started_at,
                "score": -10_000.0,
                "error": {
                    "message": str(exc),
                    "status": exc.status,
                    "url": exc.url,
                    "payload": exc.payload,
                },
            }


def extract_metrics(detail: Dict[str, Any], check_payload: Any) -> Dict[str, Any]:
    is_data = detail.get("is") if isinstance(detail, dict) else {}
    checks = extract_checks(check_payload)
    metrics = {
        "sharpe": safe_float(is_data.get("sharpe")),
        "fitness": safe_float(is_data.get("fitness")),
        "turnover": safe_float(is_data.get("turnover")),
        "returns": safe_float(is_data.get("returns")),
        "drawdown": safe_float(is_data.get("drawdown")),
        "margin": safe_float(is_data.get("margin")),
    }
    for name in (
        "LOW_SHARPE",
        "LOW_FITNESS",
        "LOW_TURNOVER",
        "HIGH_TURNOVER",
        "CONCENTRATED_WEIGHT",
        "LOW_SUB_UNIVERSE_SHARPE",
    ):
        check = next((item for item in checks if item.get("name") == name), None)
        if not check:
            continue
        key = name.lower()
        metrics[f"{key}_limit"] = safe_float(check.get("limit"))
        metrics[f"{key}_value"] = safe_float(check.get("value"))
    return metrics


def extract_checks(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        checks = payload.get("is", {}).get("checks") or payload.get("checks") or []
        if isinstance(checks, list):
            return [item for item in checks if isinstance(item, dict)]
    return []


def failed_checks(check_payload: Any, names: Optional[set[str]] = None) -> List[str]:
    failed: List[str] = []
    for check in extract_checks(check_payload):
        if check.get("result") != "FAIL":
            continue
        name = str(check.get("name") or "")
        if names is not None and name not in names:
            continue
        failed.append(name)
    return failed


def failed_blocking_checks(check_payload: Any) -> List[str]:
    return failed_checks(check_payload, BLOCKING_CHECKS)


def failed_correlation_checks(check_payload: Any) -> List[str]:
    return failed_checks(check_payload, CORRELATION_CHECKS)


def should_pivot_away_from_check_payload(check_payload: Any) -> bool:
    return not failed_blocking_checks(check_payload) and bool(failed_correlation_checks(check_payload))


def should_pivot_away_from_record(record: Dict[str, Any]) -> bool:
    if record.get("status") != "ok":
        return False
    if bool(record.get("correlation_pivot")):
        return True
    failed_blocking = record.get("failed_blocking_checks") or []
    failed_corr = record.get("failed_correlation_checks") or []
    if not failed_corr:
        failed_summary = record.get("summary", {}).get("failed") or []
        failed_corr = [name for name in failed_summary if name in CORRELATION_CHECKS]
    return not failed_blocking and bool(failed_corr)


def correlation_pivot_families(records: Iterable[Dict[str, Any]]) -> set[str]:
    pivot_families: set[str] = set()
    for record in records:
        family = record.get("family")
        if isinstance(family, str) and family and should_pivot_away_from_record(record):
            pivot_families.add(family)
    return pivot_families


def score_result(detail: Dict[str, Any], check_payload: Any) -> float:
    is_data = detail.get("is") if isinstance(detail, dict) else {}
    sharpe = safe_float(is_data.get("sharpe")) or 0.0
    fitness = safe_float(is_data.get("fitness")) or 0.0
    turnover = safe_float(is_data.get("turnover")) or 0.0
    returns = safe_float(is_data.get("returns")) or 0.0
    drawdown = safe_float(is_data.get("drawdown")) or 0.0
    margin = safe_float(is_data.get("margin")) or 0.0

    score = sharpe * 120.0
    score += fitness * 160.0
    score += returns * 250.0
    score += margin * 20000.0
    score -= drawdown * 120.0

    for check in extract_checks(check_payload):
        name = str(check.get("name"))
        result = check.get("result")
        limit = safe_float(check.get("limit"))
        value = safe_float(check.get("value"))
        if result == "PASS":
            score += 20.0
        elif result == "WARNING":
            score -= 10.0
        elif result == "PENDING":
            score -= 5.0
        elif result == "FAIL":
            score -= 80.0
            if limit is not None and value is not None:
                if name == "HIGH_TURNOVER":
                    score -= max(0.0, value - limit) * 300.0
                elif name == "CONCENTRATED_WEIGHT":
                    score -= max(0.0, value - limit) * 1200.0
                else:
                    score -= max(0.0, limit - value) * 300.0
    if not failed_blocking_checks(check_payload):
        score += 400.0
    if 0.01 <= turnover <= 0.7:
        score += 40.0
    return round(score, 4)


def build_refinement_candidates(
    top_records: Sequence[Dict[str, Any]],
    *,
    family_filter: set[str],
    blocked_families: Optional[set[str]] = None,
) -> List[Candidate]:
    seen: set[str] = set()
    refinements: List[Candidate] = []
    blocked_families = blocked_families or set()
    window_offsets = (-2, -1, 1, 2, 5)
    decay_choices = (0, 2, 4, 6, 8)
    neutralizations = ("SECTOR", "INDUSTRY", "SUBINDUSTRY")
    universes = ("TOP3000", "TOP1000", "TOP500")
    truncations = (0.05, 0.08, 0.1)

    for record in top_records:
        family = str(record.get("family") or "")
        if family_filter and family not in family_filter:
            continue
        if record.get("status") != "ok":
            continue
        if family in blocked_families:
            continue
        base_settings = normalize_settings(record.get("settings") or {})
        expression = str(record.get("expression") or "")
        metadata = record.get("metadata") or {}
        base_window = metadata.get("window")
        parent_key = record.get("candidate_key")

        for decay in decay_choices:
            if decay == base_settings.get("decay"):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["decay"] = decay
            refinements.append(
                Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.decay{decay}",
                    stage="refine_decay",
                    priority=float(record.get("score") or 0.0),
                    parent_key=parent_key,
                    metadata={**metadata, "refinement": "decay", "decay": decay},
                )
            )

        for neutralization in neutralizations:
            if neutralization == base_settings.get("neutralization"):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["neutralization"] = neutralization
            refinements.append(
                Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.neutral_{neutralization.lower()}",
                    stage="refine_neutralization",
                    priority=float(record.get("score") or 0.0),
                    parent_key=parent_key,
                    metadata={**metadata, "refinement": "neutralization", "neutralization": neutralization},
                )
            )

        for universe in universes:
            if universe == base_settings.get("universe"):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["universe"] = universe
            refinements.append(
                Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.universe_{universe.lower()}",
                    stage="refine_universe",
                    priority=float(record.get("score") or 0.0),
                    parent_key=parent_key,
                    metadata={**metadata, "refinement": "universe", "universe": universe},
                )
            )

        for truncation in truncations:
            if math.isclose(float(base_settings.get("truncation", 0.0)), truncation, abs_tol=1e-9):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["truncation"] = truncation
            refinements.append(
                Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.trunc_{str(truncation).replace('.', '_')}",
                    stage="refine_truncation",
                    priority=float(record.get("score") or 0.0),
                    parent_key=parent_key,
                    metadata={**metadata, "refinement": "truncation", "truncation": truncation},
                )
            )

        if isinstance(base_window, int) and "{window}" in str(metadata.get("template", "")):
            template = str(metadata["template"])
            field_name = str(metadata.get("field") or "")
            sign = int(metadata.get("sign", 1))
            signed_field = apply_sign(field_name, sign)
            for offset in window_offsets:
                next_window = base_window + offset
                if next_window <= 1 or next_window == base_window:
                    continue
                next_expression = template.format(
                    field=field_name,
                    signed_field=signed_field,
                    window=next_window,
                )
                refinements.append(
                    Candidate(
                        expression=next_expression,
                        settings=base_settings,
                        family=family,
                        idea_name=f"{record.get('idea_name')}.w{next_window}",
                        stage="refine_window",
                        priority=float(record.get("score") or 0.0),
                        parent_key=parent_key,
                        metadata={**metadata, "refinement": "window", "window": next_window},
                    )
                )

    deduped: List[Candidate] = []
    for candidate in sorted(refinements, key=lambda item: (-item.priority, item.idea_name)):
        if candidate.signature() in seen:
            continue
        seen.add(candidate.signature())
        deduped.append(candidate)
    return deduped


def build_leaderboard(
    records: Iterable[Dict[str, Any]],
    *,
    family_filter: set[str],
    limit: int,
) -> List[Dict[str, Any]]:
    eligible: List[Dict[str, Any]] = []
    for record in records:
        if family_filter and record.get("family") not in family_filter:
            continue
        if record.get("status") != "ok":
            continue
        eligible.append(record)
    eligible.sort(
        key=lambda item: (
            0 if item.get("precheck_submit_ready") else 1,
            -float(item.get("score") or -10000.0),
            -(safe_float(item.get("metrics", {}).get("sharpe")) or -999.0),
        )
    )
    return eligible[:limit]


def build_search_summary(
    *,
    budget: int,
    seed_budget: int,
    refine_budget: int,
    diversify_budget: int,
    evaluated_now: Sequence[Dict[str, Any]],
    submission_attempts: Sequence[Dict[str, Any]],
    leaderboard: Sequence[Dict[str, Any]],
    workdir: Path,
    state: Dict[str, Any],
    pivot_families: Sequence[str],
) -> Dict[str, Any]:
    return {
        "budget": budget,
        "seed_budget": seed_budget,
        "refine_budget": refine_budget,
        "diversify_budget": diversify_budget,
        "evaluated_now": len(evaluated_now),
        "ok_now": sum(1 for item in evaluated_now if item.get("status") == "ok"),
        "error_now": sum(1 for item in evaluated_now if item.get("status") == "error"),
        "submittable_now": sum(1 for item in evaluated_now if item.get("precheck_submit_ready")),
        "correlation_pivot_families": list(pivot_families),
        "submission_attempts": [compact_submission(item) for item in submission_attempts],
        "best_current": compact_record(leaderboard[0]) if leaderboard else None,
        "leaderboard": [compact_record(item) for item in leaderboard[:5]],
        "paths": {
            "workdir": str(workdir),
            "results": str(workdir / "results.jsonl"),
            "submissions": str(workdir / "submissions.jsonl"),
            "state": str(workdir / "state.json"),
        },
        "state": state,
    }


def compact_record(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_key": record.get("candidate_key"),
        "alpha_id": record.get("alpha_id"),
        "family": record.get("family"),
        "idea_name": record.get("idea_name"),
        "stage": record.get("stage"),
        "expression": record.get("expression"),
        "settings": record.get("settings"),
        "score": record.get("score"),
        "metrics": record.get("metrics"),
        "failed_checks": record.get("failed_checks"),
        "failed_blocking_checks": record.get("failed_blocking_checks"),
        "failed_correlation_checks": record.get("failed_correlation_checks"),
        "correlation_pivot": record.get("correlation_pivot"),
        "precheck_submit_ready": record.get("precheck_submit_ready"),
        "summary": record.get("summary"),
    }


def compact_submission(record: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "alpha_id": record.get("alpha_id"),
        "result": record.get("result"),
        "submitted_at": record.get("submitted_at"),
        "response": record.get("response"),
    }


def attempt_submit_record(
    *,
    client: BrainClient,
    record: Dict[str, Any],
    submissions_store: JsonlStore,
    max_wait: float,
    poll_interval: float,
) -> Dict[str, Any]:
    alpha_id = str(record["alpha_id"])
    submitted_at = iso_now()
    try:
        response = client.submit_alpha(alpha_id, max_wait=max_wait, poll_interval=poll_interval)
        submission = {
            "alpha_id": alpha_id,
            "candidate_key": record.get("candidate_key"),
            "submitted_at": submitted_at,
            "result": "ok",
            "response": response,
        }
    except BrainApiError as exc:
        submission = {
            "alpha_id": alpha_id,
            "candidate_key": record.get("candidate_key"),
            "submitted_at": submitted_at,
            "result": "error",
            "response": {
                "message": str(exc),
                "status": exc.status,
                "url": exc.url,
                "payload": exc.payload,
            },
        }
    submissions_store.append(submission)
    return submission


def attempt_submit(
    *,
    client: BrainClient,
    alpha_id: str,
    record: Dict[str, Any],
    submissions_store: JsonlStore,
    allow_pending_checks: bool,
    max_wait: float,
    poll_interval: float,
) -> Dict[str, Any]:
    pending = record.get("summary", {}).get("pending") or []
    if pending and not allow_pending_checks:
        raise BrainApiError(
            f"Alpha {alpha_id} still has pending checks: {', '.join(map(str, pending))}"
        )
    return attempt_submit_record(
        client=client,
        record=record,
        submissions_store=submissions_store,
        max_wait=max_wait,
        poll_interval=poll_interval,
    )


def write_state(
    path: Path,
    results: Sequence[Dict[str, Any]],
    submissions: Sequence[Dict[str, Any]],
    leaderboard: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    state = {
        "updated_at": iso_now(),
        "result_count": len(results),
        "ok_count": sum(1 for record in results if record.get("status") == "ok"),
        "error_count": sum(1 for record in results if record.get("status") == "error"),
        "submittable_count": sum(1 for record in results if record.get("precheck_submit_ready")),
        "submission_count": len(submissions),
        "best_candidate_key": leaderboard[0].get("candidate_key") if leaderboard else None,
        "best_alpha_id": leaderboard[0].get("alpha_id") if leaderboard else None,
        "best_score": leaderboard[0].get("score") if leaderboard else None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def iso_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def render_output(payload: Any, *, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False))
    else:
        print(json.dumps(payload, ensure_ascii=False))


def main() -> int:
    args = parse_args()
    try:
        result = args.func(args)
        render_output(result, pretty=args.pretty)
        return 0
    except BrainApiError as exc:
        message = str(exc)
        if exc.status is not None:
            message = f"{message} [status={exc.status}]"
        if exc.url:
            message = f"{message} [url={exc.url}]"
        print(message, file=sys.stderr)
        if exc.payload is not None:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

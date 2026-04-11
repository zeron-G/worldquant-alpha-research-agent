from __future__ import annotations

import copy
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import alpha_research_pipeline as pipeline


RESEARCH_STAGES = ("explore", "exploit", "robustness", "harvest")


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def tokenize_expression(expression: str) -> set[str]:
    raw_tokens = re.split(r"[^a-zA-Z0-9_]+", expression.lower())
    return {
        token
        for token in raw_tokens
        if token and not token.isdigit() and len(token) > 1
    }


def expression_novelty(expression: str, frontier_token_sets: Sequence[set[str]]) -> float:
    if not frontier_token_sets:
        return 1.0
    tokens = tokenize_expression(expression)
    if not tokens:
        return 0.0
    max_similarity = 0.0
    for frontier_tokens in frontier_token_sets:
        if not frontier_tokens:
            continue
        union = len(tokens | frontier_tokens)
        if union == 0:
            continue
        similarity = len(tokens & frontier_tokens) / union
        if similarity > max_similarity:
            max_similarity = similarity
    return max(0.0, min(1.0, 1.0 - max_similarity))


def dedupe_candidates(candidates: Sequence[pipeline.Candidate]) -> List[pipeline.Candidate]:
    seen: set[str] = set()
    output: List[pipeline.Candidate] = []
    for candidate in candidates:
        signature = candidate.signature()
        if signature in seen:
            continue
        seen.add(signature)
        output.append(candidate)
    return output


def build_check_aware_refinements(
    top_records: Sequence[Dict[str, Any]],
    *,
    family_filter: set[str],
    blocked_families: set[str],
) -> List[pipeline.Candidate]:
    refinements: List[pipeline.Candidate] = []
    for record in top_records:
        if record.get("status") != "ok":
            continue
        family = str(record.get("family") or "")
        if not family:
            continue
        if family_filter and family not in family_filter:
            continue
        if family in blocked_families:
            continue

        expression = str(record.get("expression") or "")
        if not expression:
            continue
        metadata = record.get("metadata") or {}
        parent_key = record.get("candidate_key")
        base_settings = pipeline.normalize_settings(record.get("settings") or {})
        failed_checks = {str(name) for name in (record.get("failed_checks") or [])}
        score_priority = safe_float(record.get("score")) or 0.0

        decay_pool: set[int] = set()
        trunc_pool: set[float] = set()
        neutral_pool: set[str] = set()
        universe_pool: set[str] = set()

        if "HIGH_TURNOVER" in failed_checks:
            decay_pool.update({6, 8})
            trunc_pool.update({0.08, 0.1})
        if "LOW_TURNOVER" in failed_checks:
            decay_pool.update({0, 2})
        if "CONCENTRATED_WEIGHT" in failed_checks:
            trunc_pool.update({0.03, 0.05})
            neutral_pool.update({"INDUSTRY", "SUBINDUSTRY"})
        if "LOW_SUB_UNIVERSE_SHARPE" in failed_checks:
            universe_pool.update({"TOP3000"})
            neutral_pool.update({"INDUSTRY", "SUBINDUSTRY"})
        if "LOW_SHARPE" in failed_checks or "LOW_FITNESS" in failed_checks:
            decay_pool.update({2, 4, 6})
            universe_pool.update({"TOP3000", "TOP1000"})
            neutral_pool.update({"SECTOR", "INDUSTRY"})

        if not failed_checks:
            decay_pool.update({2, 4, 6})
            trunc_pool.update({0.05, 0.08})
            neutral_pool.update({"SECTOR", "INDUSTRY"})

        current_decay = int(base_settings.get("decay") or 0)
        decay_pool.update(
            {
                max(0, current_decay - 2),
                min(12, current_decay + 2),
            }
        )
        current_trunc = safe_float(base_settings.get("truncation")) or 0.08
        trunc_pool.update(
            {
                max(0.01, round(current_trunc - 0.02, 3)),
                min(0.15, round(current_trunc + 0.02, 3)),
            }
        )
        universe_pool.update({"TOP3000", "TOP1000", "TOP500"})
        neutral_pool.update({"SECTOR", "INDUSTRY", "SUBINDUSTRY"})

        for decay in sorted(decay_pool):
            if decay == int(base_settings.get("decay") or 0):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["decay"] = decay
            refinements.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.check_decay_{decay}",
                    stage="refine_check_aware_decay",
                    priority=score_priority + 20.0,
                    parent_key=parent_key,
                    metadata={**metadata, "check_aware": True, "focus_checks": sorted(failed_checks)},
                )
            )

        for truncation in sorted(trunc_pool):
            if math.isclose(float(base_settings.get("truncation", 0.0)), truncation, abs_tol=1e-9):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["truncation"] = truncation
            refinements.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.check_trunc_{str(truncation).replace('.', '_')}",
                    stage="refine_check_aware_truncation",
                    priority=score_priority + 15.0,
                    parent_key=parent_key,
                    metadata={**metadata, "check_aware": True, "focus_checks": sorted(failed_checks)},
                )
            )

        for neutralization in sorted(neutral_pool):
            if neutralization == str(base_settings.get("neutralization") or ""):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["neutralization"] = neutralization
            refinements.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.check_neutral_{neutralization.lower()}",
                    stage="refine_check_aware_neutralization",
                    priority=score_priority + 12.0,
                    parent_key=parent_key,
                    metadata={**metadata, "check_aware": True, "focus_checks": sorted(failed_checks)},
                )
            )

        for universe in sorted(universe_pool):
            if universe == str(base_settings.get("universe") or ""):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["universe"] = universe
            refinements.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.check_universe_{universe.lower()}",
                    stage="refine_check_aware_universe",
                    priority=score_priority + 10.0,
                    parent_key=parent_key,
                    metadata={**metadata, "check_aware": True, "focus_checks": sorted(failed_checks)},
                )
            )

        base_window = metadata.get("window")
        template = str(metadata.get("template") or "")
        field_name = str(metadata.get("field") or "")
        if isinstance(base_window, int) and "{window}" in template and field_name:
            signed_field = pipeline.apply_sign(field_name, int(metadata.get("sign", 1)))
            for offset in (-5, -2, -1, 1, 2, 5):
                next_window = base_window + offset
                if next_window <= 1 or next_window == base_window:
                    continue
                next_expression = template.format(
                    field=field_name,
                    signed_field=signed_field,
                    window=next_window,
                )
                refinements.append(
                    pipeline.Candidate(
                        expression=next_expression,
                        settings=copy.deepcopy(base_settings),
                        family=family,
                        idea_name=f"{record.get('idea_name')}.check_window_{next_window}",
                        stage="refine_check_aware_window",
                        priority=score_priority + 18.0,
                        parent_key=parent_key,
                        metadata={**metadata, "check_aware": True, "focus_checks": sorted(failed_checks), "window": next_window},
                    )
                )

    return dedupe_candidates(refinements)


def build_robustness_candidates(
    frontier_records: Sequence[Dict[str, Any]],
    *,
    family_filter: set[str],
    top_k: int,
) -> List[pipeline.Candidate]:
    candidates: List[pipeline.Candidate] = []
    selected = [record for record in frontier_records if record.get("status") == "ok"][: max(1, top_k)]
    for record in selected:
        family = str(record.get("family") or "")
        if family_filter and family not in family_filter:
            continue
        expression = str(record.get("expression") or "")
        if not expression:
            continue
        metadata = record.get("metadata") or {}
        parent_key = record.get("candidate_key")
        base_settings = pipeline.normalize_settings(record.get("settings") or {})
        score_priority = safe_float(record.get("score")) or 0.0

        for universe in ("TOP3000", "TOP1000", "TOP500"):
            if universe == str(base_settings.get("universe") or ""):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["universe"] = universe
            candidates.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.robust_universe_{universe.lower()}",
                    stage="robustness_universe",
                    priority=score_priority + 40.0,
                    parent_key=parent_key,
                    metadata={**metadata, "robustness": True, "robustness_test": f"universe:{universe}"},
                )
            )

        for neutralization in ("SECTOR", "INDUSTRY", "SUBINDUSTRY"):
            if neutralization == str(base_settings.get("neutralization") or ""):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["neutralization"] = neutralization
            candidates.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.robust_neutral_{neutralization.lower()}",
                    stage="robustness_neutralization",
                    priority=score_priority + 35.0,
                    parent_key=parent_key,
                    metadata={**metadata, "robustness": True, "robustness_test": f"neutralization:{neutralization}"},
                )
            )

        current_trunc = safe_float(base_settings.get("truncation")) or 0.08
        for delta in (-0.02, 0.02):
            next_trunc = max(0.01, min(0.2, round(current_trunc + delta, 3)))
            if math.isclose(current_trunc, next_trunc, abs_tol=1e-9):
                continue
            next_settings = copy.deepcopy(base_settings)
            next_settings["truncation"] = next_trunc
            candidates.append(
                pipeline.Candidate(
                    expression=expression,
                    settings=next_settings,
                    family=family,
                    idea_name=f"{record.get('idea_name')}.robust_trunc_{str(next_trunc).replace('.', '_')}",
                    stage="robustness_truncation",
                    priority=score_priority + 30.0,
                    parent_key=parent_key,
                    metadata={**metadata, "robustness": True, "robustness_test": f"truncation:{next_trunc}"},
                )
            )

    return dedupe_candidates(candidates)


@dataclass
class ResearchNotebook:
    budget: int
    max_family_budget_share: float
    min_expression_novelty: float
    robustness_score_threshold: float
    run_family_counts: Dict[str, int] = field(default_factory=dict)
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    hypothesis_log: List[Dict[str, Any]] = field(default_factory=list)

    def family_cap(self) -> int:
        share = max(0.05, min(1.0, float(self.max_family_budget_share)))
        return max(1, int(math.ceil(max(1, self.budget) * share)))

    def is_family_capped(self, family: str) -> bool:
        if not family:
            return False
        return self.run_family_counts.get(family, 0) >= self.family_cap()

    def observe_records(self, records: Sequence[Dict[str, Any]]) -> None:
        for record in records:
            family = str(record.get("family") or "")
            if not family:
                continue
            self.run_family_counts[family] = self.run_family_counts.get(family, 0) + 1

    def record_hypothesis(
        self,
        *,
        iteration: int,
        stage: str,
        action: str,
        hypothesis: str,
        rationale: str,
        focus_family: Optional[str],
        risk_note: str,
    ) -> None:
        self.hypothesis_log.append(
            {
                "timestamp": pipeline.iso_now(),
                "iteration": iteration,
                "stage": stage,
                "action": action,
                "hypothesis": hypothesis,
                "rationale": rationale,
                "focus_family": focus_family,
                "risk_note": risk_note,
            }
        )

    def recent_hypotheses(self, *, limit: int = 5) -> List[Dict[str, Any]]:
        return self.hypothesis_log[-max(1, limit) :]

    def failed_check_histogram(self, records: Sequence[Dict[str, Any]], *, top_k: int = 8) -> List[Dict[str, Any]]:
        counter: Counter[str] = Counter()
        for record in records:
            if record.get("status") != "ok":
                continue
            for name in record.get("failed_checks") or []:
                if isinstance(name, str):
                    counter[name] += 1
        return [{"check": name, "count": count} for name, count in counter.most_common(top_k)]

    def family_stats(self, records: Sequence[Dict[str, Any]], *, top_k: int = 8) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for record in records:
            family = str(record.get("family") or "")
            if not family:
                continue
            bucket = grouped.setdefault(
                family,
                {
                    "family": family,
                    "attempts": 0,
                    "ok_count": 0,
                    "submittable_count": 0,
                    "best_score": None,
                    "avg_score": None,
                    "scores": [],
                    "corr_fail_count": 0,
                },
            )
            bucket["attempts"] += 1
            if record.get("status") == "ok":
                bucket["ok_count"] += 1
                if record.get("precheck_submit_ready"):
                    bucket["submittable_count"] += 1
                score = safe_float(record.get("score"))
                if score is not None:
                    bucket["scores"].append(score)
                    if bucket["best_score"] is None or score > bucket["best_score"]:
                        bucket["best_score"] = score
                if record.get("failed_correlation_checks"):
                    bucket["corr_fail_count"] += 1
        output: List[Dict[str, Any]] = []
        for item in grouped.values():
            scores: List[float] = item.pop("scores")
            item["avg_score"] = round(sum(scores) / len(scores), 4) if scores else None
            attempts = max(1, int(item["attempts"]))
            item["ok_rate"] = round(float(item["ok_count"]) / attempts, 4)
            item["corr_fail_rate"] = round(float(item["corr_fail_count"]) / attempts, 4)
            item["run_count"] = self.run_family_counts.get(item["family"], 0)
            item["family_cap_reached"] = self.is_family_capped(item["family"])
            output.append(item)
        output.sort(
            key=lambda row: (
                -(safe_float(row.get("best_score")) or -999999.0),
                -(safe_float(row.get("avg_score")) or -999999.0),
                row["family"],
            )
        )
        return output[: max(1, top_k)]

    def determine_stage(
        self,
        *,
        iteration: int,
        evaluated_total: int,
        seed_target: int,
        leaderboard: Sequence[Dict[str, Any]],
        records: Sequence[Dict[str, Any]],
    ) -> Tuple[str, str]:
        best_score = safe_float(leaderboard[0].get("score")) if leaderboard else None
        submittable_count = sum(1 for item in records if item.get("precheck_submit_ready"))
        robust_records = sum(
            1
            for item in records
            if isinstance(item.get("stage"), str) and str(item.get("stage")).startswith("robustness")
        )

        if submittable_count > 0 and robust_records >= 2:
            stage = "harvest"
            reason = "At least one submit-ready alpha exists with robustness checks completed."
        elif submittable_count > 0 or (best_score is not None and best_score >= self.robustness_score_threshold):
            stage = "robustness"
            reason = "Strong frontier found, shifting from pure search to robustness validation."
        elif evaluated_total >= seed_target or iteration >= 3:
            stage = "exploit"
            reason = "Seed exploration threshold reached; focus on targeted refinement."
        else:
            stage = "explore"
            reason = "Early run stage prioritizes broad exploration."

        previous = self.stage_history[-1]["stage"] if self.stage_history else None
        if previous != stage:
            self.stage_history.append(
                {
                    "timestamp": pipeline.iso_now(),
                    "iteration": iteration,
                    "stage": stage,
                    "reason": reason,
                }
            )
        return stage, reason

    def rank_candidates(
        self,
        *,
        candidates: Sequence[pipeline.Candidate],
        frontier_records: Sequence[Dict[str, Any]],
        stage: str,
        blocked_families: Optional[set[str]] = None,
    ) -> List[pipeline.Candidate]:
        blocked_families = blocked_families or set()
        frontier_token_sets = [
            tokenize_expression(str(item.get("expression") or ""))
            for item in frontier_records[:12]
            if isinstance(item.get("expression"), str)
        ]
        best_family = str(frontier_records[0].get("family") or "") if frontier_records else ""
        scored: List[Tuple[float, pipeline.Candidate]] = []
        for candidate in candidates:
            family = candidate.family
            family_count = self.run_family_counts.get(family, 0)
            family_bonus = 1.0 / (1.0 + family_count)
            novelty = expression_novelty(candidate.expression, frontier_token_sets)
            priority_component = max(0.0, float(candidate.priority) / 1000.0)
            capped_penalty = -0.8 if self.is_family_capped(family) else 0.0
            pivot_penalty = -0.5 if family in blocked_families else 0.0

            if stage == "explore":
                score = novelty * 0.65 + family_bonus * 0.25 + priority_component * 0.10
                if novelty < self.min_expression_novelty:
                    score -= 0.25
            elif stage == "exploit":
                score = novelty * 0.20 + family_bonus * 0.15 + priority_component * 0.65
            elif stage == "robustness":
                robust_flag = 1.0 if candidate.metadata.get("robustness") else 0.0
                family_match = 0.2 if best_family and family == best_family else 0.0
                score = robust_flag * 0.60 + priority_component * 0.30 + family_match + novelty * 0.10
            else:  # harvest
                robust_flag = 1.0 if candidate.metadata.get("robustness") else 0.0
                score = robust_flag * 0.65 + priority_component * 0.30 + novelty * 0.05

            score += capped_penalty + pivot_penalty
            scored.append((score, candidate))

        scored.sort(key=lambda item: (-item[0], item[1].idea_name))
        return [candidate for _, candidate in scored]

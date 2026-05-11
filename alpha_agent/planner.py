from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from alpha_agent.config import ModelConfig


ALLOWED_ACTIONS = {
    "evaluate_seed",
    "evaluate_refine",
    "evaluate_diversify",
    "evaluate_robustness",
    "submit_best",
    "stop",
}


@dataclass(frozen=True)
class PlannerAction:
    action: str
    batch_size: int = 1
    rationale: str = ""
    hypothesis: str = ""
    focus_family: Optional[str] = None
    risk_note: str = ""
    target_alpha_id: Optional[str] = None
    raw: Dict[str, Any] | None = None

    @classmethod
    def stop(cls, rationale: str) -> "PlannerAction":
        return cls(action="stop", batch_size=0, rationale=rationale, raw={})

    def clamped(self, remaining_budget: int) -> "PlannerAction":
        if self.action in {"stop", "submit_best"}:
            return PlannerAction(
                action=self.action,
                batch_size=0,
                rationale=self.rationale,
                hypothesis=self.hypothesis,
                focus_family=self.focus_family,
                risk_note=self.risk_note,
                target_alpha_id=self.target_alpha_id,
                raw=self.raw or {},
            )
        size = max(1, min(int(self.batch_size or 1), max(1, remaining_budget)))
        return PlannerAction(
            action=self.action,
            batch_size=size,
            rationale=self.rationale,
            hypothesis=self.hypothesis,
            focus_family=self.focus_family,
            risk_note=self.risk_note,
            target_alpha_id=self.target_alpha_id,
            raw=self.raw or {},
        )


class HeuristicPlanner:
    def decide(self, context: Dict[str, Any]) -> PlannerAction:
        remaining_budget = int(context.get("remaining_budget") or 0)
        if remaining_budget <= 0:
            return PlannerAction.stop("Budget exhausted.")

        stage = str(context.get("research_stage") or "explore")
        failed_hist = context.get("failed_check_histogram") or []
        top_failed = str(failed_hist[0].get("check")) if failed_hist else ""
        family_stats = context.get("family_stats") or []
        leading_family = str(family_stats[0].get("family")) if family_stats else None

        submission_mode = str(context.get("submission_mode") or "disabled")
        best_submittable = context.get("best_submittable_alpha_id")
        if stage == "harvest" and submission_mode == "auto_approved" and best_submittable:
            return PlannerAction(
                action="submit_best",
                rationale="Found submit-ready candidate and auto-approved mode is enabled.",
                hypothesis="Frontier candidate passed blocking checks and should be harvested.",
                focus_family=leading_family,
                risk_note="Auto-submit enabled; monitor pending checks and submit response.",
                target_alpha_id=str(best_submittable),
                raw={},
            )

        seed_queue_remaining = int(context.get("seed_queue_remaining") or 0)
        seed_target_remaining = int(context.get("seed_target_remaining") or 0)
        refine_available = int(context.get("refine_candidates_available") or 0)
        diversify_available = int(context.get("diversification_candidates_available") or 0)
        robustness_available = int(context.get("robustness_candidates_available") or 0)
        iteration = int(context.get("iteration") or 0)

        default_batch = min(4, remaining_budget)
        if stage == "explore":
            if seed_queue_remaining > 0 and (seed_target_remaining > 0 or iteration <= 2):
                return PlannerAction(
                    action="evaluate_seed",
                    batch_size=min(default_batch, seed_queue_remaining),
                    rationale="Explore broad families before overfitting to early winners.",
                    hypothesis="Diverse seeds increase odds of orthogonal signal discovery.",
                    focus_family=leading_family,
                    risk_note="Avoid concentration in one family during exploration.",
                    raw={},
                )
            if diversify_available > 0:
                return PlannerAction(
                    action="evaluate_diversify",
                    batch_size=min(default_batch, diversify_available),
                    rationale="Seed queue is thin; diversify to restore family breadth.",
                    hypothesis="Orthogonal families can break correlation bottlenecks.",
                    focus_family=leading_family,
                    risk_note="Diversification may reduce short-term score but improve robustness.",
                    raw={},
                )

        if stage == "exploit":
            if refine_available > 0:
                return PlannerAction(
                    action="evaluate_refine",
                    batch_size=min(default_batch, refine_available),
                    rationale="Exploit frontier with check-aware local mutations.",
                    hypothesis=f"Targeting dominant failure ({top_failed or 'none'}) can improve pass rate.",
                    focus_family=leading_family,
                    risk_note="Watch family budget cap to avoid single-family over-optimization.",
                    raw={},
                )
            if diversify_available > 0:
                return PlannerAction(
                    action="evaluate_diversify",
                    batch_size=min(default_batch, diversify_available),
                    rationale="Refine queue exhausted; diversify for new leverage points.",
                    hypothesis="New family seeds can become alternative frontier anchors.",
                    focus_family=leading_family,
                    risk_note="Diversified seeds can have lower immediate scores.",
                    raw={},
                )

        if stage == "robustness":
            if top_failed in {"SELF_CORRELATION", "PROD_CORRELATION"} and refine_available > 0 and not best_submittable:
                return PlannerAction(
                    action="evaluate_refine",
                    batch_size=min(default_batch, refine_available),
                    rationale="Quality frontier is correlation-blocked; run decorrelation repairs before robustness harvest.",
                    hypothesis=f"Structural and neutralization repairs can reduce {top_failed} while preserving signal quality.",
                    focus_family=leading_family,
                    risk_note="Do not mark correlation-failed candidates as submission-ready.",
                    raw={},
                )
            if robustness_available > 0:
                return PlannerAction(
                    action="evaluate_robustness",
                    batch_size=min(default_batch, robustness_available),
                    rationale="Run robustness probes on frontier candidates before harvest.",
                    hypothesis="Strong candidates should remain viable under universe and neutralization stress.",
                    focus_family=leading_family,
                    risk_note="Robustness tests may lower score but improve confidence.",
                    raw={},
                )
            if refine_available > 0:
                return PlannerAction(
                    action="evaluate_refine",
                    batch_size=min(default_batch, refine_available),
                    rationale="Robustness queue empty; continue tactical refinement.",
                    hypothesis="Small parameter changes can recover robustness gaps.",
                    focus_family=leading_family,
                    risk_note="Do not drift too far from validated frontier.",
                    raw={},
                )

        if stage == "harvest" and best_submittable:
            return PlannerAction(
                action="submit_best",
                rationale="Harvest stage reached with submit-ready alpha.",
                hypothesis="Candidate is strong enough for controlled submission.",
                focus_family=leading_family,
                risk_note="Submission should remain governed by mode and approval policy.",
                target_alpha_id=str(best_submittable),
                raw={},
            )

        if seed_queue_remaining > 0 and (seed_target_remaining > 0 or iteration <= 2):
            return PlannerAction(
                action="evaluate_seed",
                batch_size=min(default_batch, seed_queue_remaining),
                rationale="Continue seed exploration to diversify candidate coverage.",
                hypothesis="Expanding initial sample space improves search quality.",
                focus_family=leading_family,
                risk_note="Avoid spending all budget on one research angle.",
                raw={},
            )
        if refine_available > 0:
            return PlannerAction(
                action="evaluate_refine",
                batch_size=min(default_batch, refine_available),
                rationale="Use best frontier candidates for local refinement.",
                hypothesis=f"Refining around top candidates should improve {top_failed or 'overall checks'}.",
                focus_family=leading_family,
                risk_note="Repeated local search may increase correlation risk.",
                raw={},
            )
        if robustness_available > 0:
            return PlannerAction(
                action="evaluate_robustness",
                batch_size=min(default_batch, robustness_available),
                rationale="Use remaining budget on robustness diagnostics.",
                hypothesis="Stress-testing top candidates improves trust before submit.",
                focus_family=leading_family,
                risk_note="Robustness checks consume budget quickly.",
                raw={},
            )
        if diversify_available > 0:
            return PlannerAction(
                action="evaluate_diversify",
                batch_size=min(default_batch, diversify_available),
                rationale="Refine queue is exhausted, diversify into new families.",
                hypothesis="Alternative families can unlock orthogonal alpha capacity.",
                focus_family=leading_family,
                risk_note="Diversification may not improve frontier immediately.",
                raw={},
            )
        if seed_queue_remaining > 0:
            return PlannerAction(
                action="evaluate_seed",
                batch_size=min(default_batch, seed_queue_remaining),
                rationale="Fallback to remaining seed queue.",
                hypothesis="Use remaining seeds to avoid leaving search space unexplored.",
                focus_family=leading_family,
                risk_note="Late-stage seed evaluation may have low marginal utility.",
                raw={},
            )
        return PlannerAction.stop("No remaining candidate queues to evaluate.")


class OpenAIJsonPlanner:
    def __init__(self, model_config: ModelConfig, fallback: Optional[HeuristicPlanner] = None) -> None:
        self.model_config = model_config
        self.fallback = fallback or HeuristicPlanner()

    def decide(self, context: Dict[str, Any]) -> PlannerAction:
        remaining_budget = int(context.get("remaining_budget") or 0)
        if remaining_budget <= 0:
            return PlannerAction.stop("Budget exhausted.")
        api_key = os.getenv(self.model_config.api_key_env, "").strip()
        if not api_key:
            return self.fallback.decide(context)

        try:
            payload = self._request_plan(context=context, api_key=api_key)
            action = self._parse_action(payload=payload, remaining_budget=remaining_budget)
            return action
        except Exception:
            # Any planner failure falls back to deterministic behavior.
            return self.fallback.decide(context)

    def _request_plan(self, *, context: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        system_prompt = (
            "You are a senior quantitative research lead managing an alpha research book. "
            "Operate like a disciplined PM: hypothesis-driven, risk-aware, and budget-constrained. "
            "Use stage-aware behavior: explore -> exploit -> robustness -> harvest. "
            "Always return strict JSON with keys: action, batch_size, rationale, hypothesis, focus_family, "
            "risk_note, target_alpha_id. "
            "Allowed actions: evaluate_seed, evaluate_refine, evaluate_diversify, evaluate_robustness, submit_best, stop. "
            "Never exceed remaining_budget. Prefer robustness before submission."
        )
        user_prompt = (
            "Given this run context, decide the next best action.\n"
            "Decision policy:\n"
            "1) In explore, maximize family and expression diversity.\n"
            "2) In exploit, attack dominant failed checks with targeted mutations.\n"
            "3) In robustness, stress test top candidates over universe/neutralization/truncation changes.\n"
            "4) Submit only in harvest/robustness when governance allows.\n"
            "5) Include one concise hypothesis that can be validated by the next batch.\n"
            f"{json.dumps(context, ensure_ascii=False, sort_keys=True)}"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        body = {
            "model": self.model_config.model,
            "messages": messages,
            "temperature": float(self.model_config.temperature),
            "response_format": {"type": "json_object"},
        }
        response = self._chat_completion(body=body, api_key=api_key)
        return self._extract_json_payload(response)

    def _chat_completion(self, *, body: Dict[str, Any], api_key: str) -> Dict[str, Any]:
        base = self.model_config.base_url.rstrip("/")
        url = f"{base}/chat/completions"
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.model_config.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Planner HTTP error: {exc.code} {raw[:400]}") from exc

    def _extract_json_payload(self, completion: Dict[str, Any]) -> Dict[str, Any]:
        choices = completion.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("Planner response has no choices.")
        first = choices[0]
        message = first.get("message") if isinstance(first, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if isinstance(content, str):
            return json.loads(content)
        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            ]
            return json.loads("".join(text_parts))
        raise ValueError("Unsupported planner message content format.")

    def _parse_action(self, *, payload: Dict[str, Any], remaining_budget: int) -> PlannerAction:
        action = str(payload.get("action") or "").strip()
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"Unsupported action: {action}")
        batch_size = int(payload.get("batch_size") or 1)
        rationale = str(payload.get("rationale") or "")
        hypothesis = str(payload.get("hypothesis") or "")
        focus_family = payload.get("focus_family")
        if focus_family is not None:
            focus_family = str(focus_family)
        risk_note = str(payload.get("risk_note") or "")
        target_alpha_id = payload.get("target_alpha_id")
        if target_alpha_id is not None:
            target_alpha_id = str(target_alpha_id)
        parsed = PlannerAction(
            action=action,
            batch_size=batch_size,
            rationale=rationale,
            hypothesis=hypothesis,
            focus_family=focus_family,
            risk_note=risk_note,
            target_alpha_id=target_alpha_id,
            raw=payload,
        )
        return parsed.clamped(remaining_budget)

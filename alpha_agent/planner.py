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
    "submit_best",
    "stop",
}


@dataclass(frozen=True)
class PlannerAction:
    action: str
    batch_size: int = 1
    rationale: str = ""
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
                target_alpha_id=self.target_alpha_id,
                raw=self.raw or {},
            )
        size = max(1, min(int(self.batch_size or 1), max(1, remaining_budget)))
        return PlannerAction(
            action=self.action,
            batch_size=size,
            rationale=self.rationale,
            target_alpha_id=self.target_alpha_id,
            raw=self.raw or {},
        )


class HeuristicPlanner:
    def decide(self, context: Dict[str, Any]) -> PlannerAction:
        remaining_budget = int(context.get("remaining_budget") or 0)
        if remaining_budget <= 0:
            return PlannerAction.stop("Budget exhausted.")

        submission_mode = str(context.get("submission_mode") or "disabled")
        best_submittable = context.get("best_submittable_alpha_id")
        if submission_mode == "auto_approved" and best_submittable:
            return PlannerAction(
                action="submit_best",
                rationale="Found submit-ready candidate and auto-approved mode is enabled.",
                target_alpha_id=str(best_submittable),
                raw={},
            )

        seed_queue_remaining = int(context.get("seed_queue_remaining") or 0)
        seed_target_remaining = int(context.get("seed_target_remaining") or 0)
        refine_available = int(context.get("refine_candidates_available") or 0)
        diversify_available = int(context.get("diversification_candidates_available") or 0)
        iteration = int(context.get("iteration") or 0)

        default_batch = min(4, remaining_budget)
        if seed_queue_remaining > 0 and (seed_target_remaining > 0 or iteration <= 2):
            return PlannerAction(
                action="evaluate_seed",
                batch_size=min(default_batch, seed_queue_remaining),
                rationale="Continue seed exploration to diversify candidate coverage.",
                raw={},
            )
        if refine_available > 0:
            return PlannerAction(
                action="evaluate_refine",
                batch_size=min(default_batch, refine_available),
                rationale="Use best frontier candidates for local refinement.",
                raw={},
            )
        if diversify_available > 0:
            return PlannerAction(
                action="evaluate_diversify",
                batch_size=min(default_batch, diversify_available),
                rationale="Refine queue is exhausted, diversify into new families.",
                raw={},
            )
        if seed_queue_remaining > 0:
            return PlannerAction(
                action="evaluate_seed",
                batch_size=min(default_batch, seed_queue_remaining),
                rationale="Fallback to remaining seed queue.",
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
            "You are an alpha-research planning model. "
            "Return strict JSON with keys: action, batch_size, rationale, target_alpha_id. "
            "Allowed actions: evaluate_seed, evaluate_refine, evaluate_diversify, submit_best, stop. "
            "Prefer safe exploration under budget constraints. Never exceed budget."
        )
        user_prompt = (
            "Given this run context, decide the next best action.\n"
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
        target_alpha_id = payload.get("target_alpha_id")
        if target_alpha_id is not None:
            target_alpha_id = str(target_alpha_id)
        parsed = PlannerAction(
            action=action,
            batch_size=batch_size,
            rationale=rationale,
            target_alpha_id=target_alpha_id,
            raw=payload,
        )
        return parsed.clamped(remaining_budget)

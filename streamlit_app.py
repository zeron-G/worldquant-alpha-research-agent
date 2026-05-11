from __future__ import annotations

import hashlib
import html
import json
import math
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import streamlit as st

from alpha_agent.config import AgentConfig, AgentRuntimeConfig, AuthConfig, ModelConfig
from alpha_agent.engine import AlphaResearchAgent
from alpha_agent.planner import HeuristicPlanner, OpenAIJsonPlanner
import alpha_research_pipeline as pipeline
from local_env import load_local_dotenv


APP_TITLE = "Alpha Research Agent"
DEFAULT_DEMO_RUN_ID = "presentation_demo_2026"
DEFAULT_PLANNER_MODEL = "gpt5.5"
REPOSITORY_URL = "https://github.com/zeron-G/worldquant-alpha-research-agent"
PERSONAL_URL = "https://rongzegao.com"

load_local_dotenv()


st.set_page_config(
    page_title="Alpha Research Agent | Presentation Console",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)


def escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt(value: Any, digits: int = 2) -> str:
    try:
        if value is None:
            return "-"
        number = float(value)
        if math.isclose(number, round(number), abs_tol=1e-9):
            return f"{int(round(number)):,}"
        return f"{number:,.{digits}f}"
    except (TypeError, ValueError):
        return str(value) if value not in (None, "") else "-"


def pct(value: float) -> str:
    return f"{max(0.0, min(1.0, value)) * 100:.0f}%"


def env_str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value is not None else default


def env_float(name: str, default: float) -> float:
    try:
        return float(env_str(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(float(env_str(name, str(default))))
    except ValueError:
        return default


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def option_index(options: Sequence[str], value: str, fallback: int = 0) -> int:
    try:
        return list(options).index(value)
    except ValueError:
        return fallback


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --bg: #0f1110;
          --panel: #171a18;
          --panel-soft: #20251f;
          --line: rgba(232, 227, 216, 0.13);
          --line-strong: rgba(232, 227, 216, 0.24);
          --text: #f3efe7;
          --muted: #a9b0a6;
          --accent: #3dd6b3;
          --accent-2: #f4c95d;
          --warn: #ff9f6e;
          --danger: #ff6b6b;
          --good: #5be49b;
          --ink: #0f1110;
        }
        .stApp {
          background:
            radial-gradient(circle at 12% -8%, rgba(61, 214, 179, 0.14), transparent 24rem),
            linear-gradient(180deg, #0f1110 0%, #121512 46%, #0f1110 100%);
          color: var(--text);
        }
        [data-testid="stSidebar"] {
          background: rgba(18, 21, 18, 0.98);
          border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] * {
          color: var(--text);
        }
        .block-container {
          padding-top: 1.1rem;
          padding-bottom: 4rem;
          max-width: 1520px;
        }
        .top-links {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
          padding: 8px 2px 18px;
          border-bottom: 1px solid var(--line);
        }
        .top-brand {
          color: var(--text);
          font-size: 15px;
          font-weight: 760;
          letter-spacing: 0;
        }
        .top-nav {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 10px;
          flex-wrap: wrap;
        }
        .top-nav a {
          color: var(--text) !important;
          text-decoration: none;
          border: 1px solid var(--line-strong);
          background: rgba(23, 26, 24, .72);
          padding: 8px 11px;
          font-size: 13px;
          transition: border-color .16s ease, background .16s ease, color .16s ease;
        }
        .top-nav a:hover {
          color: var(--accent) !important;
          border-color: rgba(61, 214, 179, .55);
          background: rgba(61, 214, 179, .08);
        }
        h1, h2, h3 {
          letter-spacing: 0;
        }
        div[data-testid="stTabs"] button {
          color: var(--muted);
          border-bottom-color: transparent;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
          color: var(--text);
          border-bottom-color: var(--accent);
        }
        .hero {
          position: relative;
          overflow: hidden;
          min-height: 320px;
          padding: 34px 34px 26px;
          border: 1px solid var(--line);
          background:
            linear-gradient(120deg, rgba(32, 37, 31, 0.82), rgba(15, 17, 16, 0.92)),
            repeating-linear-gradient(90deg, rgba(243,239,231,0.035) 0 1px, transparent 1px 84px);
          animation: enterUp .55s ease-out both;
        }
        .hero:after {
          content: "";
          position: absolute;
          inset: auto -8% -58% auto;
          width: 52rem;
          height: 52rem;
          background: radial-gradient(circle, rgba(61,214,179,0.14), transparent 62%);
          pointer-events: none;
        }
        .eyebrow {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          color: var(--accent);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: .14em;
          font-weight: 700;
        }
        .pulse-dot {
          width: 7px;
          height: 7px;
          background: var(--accent);
          border-radius: 50%;
          box-shadow: 0 0 0 rgba(61, 214, 179, .5);
          animation: pulse 1.8s infinite;
        }
        .hero-title {
          margin: 16px 0 10px;
          font-size: clamp(46px, 7vw, 104px);
          line-height: .9;
          font-weight: 820;
          max-width: 960px;
          color: var(--text);
        }
        .hero-copy {
          max-width: 760px;
          color: var(--muted);
          font-size: 18px;
          line-height: 1.55;
        }
        .hero-strip {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 1px;
          margin-top: 26px;
          border: 1px solid var(--line);
          background: var(--line);
        }
        .strip-item {
          min-height: 84px;
          background: rgba(15, 17, 16, .72);
          padding: 16px;
        }
        .strip-k {
          color: var(--muted);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: .08em;
        }
        .strip-v {
          color: var(--text);
          font-size: 24px;
          font-weight: 760;
          margin-top: 6px;
        }
        .section {
          margin-top: 22px;
          padding: 24px;
          border-top: 1px solid var(--line);
          animation: enterUp .45s ease-out both;
        }
        .section-title {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 16px;
        }
        .section-title h2 {
          margin: 0;
          color: var(--text);
          font-size: 24px;
        }
        .section-title span {
          color: var(--muted);
          font-size: 13px;
        }
        .metric-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(168px, 1fr));
          gap: 1px;
          background: var(--line);
          border: 1px solid var(--line);
        }
        .metric {
          background: rgba(23, 26, 24, .92);
          padding: 18px;
          min-height: 118px;
          min-width: 0;
          transition: transform .18s ease, background .18s ease;
        }
        .metric:hover {
          transform: translateY(-2px);
          background: rgba(32, 37, 31, .92);
        }
        .metric-label {
          color: var(--muted);
          font-size: 12px;
          text-transform: uppercase;
          letter-spacing: .09em;
          min-height: 30px;
          overflow-wrap: anywhere;
        }
        .metric-value {
          color: var(--text);
          font-size: clamp(25px, 2.4vw, 34px);
          line-height: 1;
          font-weight: 780;
          margin-top: 12px;
          overflow-wrap: anywhere;
        }
        .metric-sub {
          color: var(--muted);
          font-size: 13px;
          margin-top: 10px;
          overflow-wrap: anywhere;
        }
        .status-good { color: var(--good); }
        .status-warn { color: var(--warn); }
        .status-danger { color: var(--danger); }
        .grid-2 {
          display: grid;
          grid-template-columns: minmax(0, 1.05fr) minmax(0, .95fr);
          gap: 18px;
        }
        .grid-3 {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 14px;
        }
        .surface {
          border: 1px solid var(--line);
          background: rgba(23, 26, 24, .72);
          padding: 18px;
        }
        .mono {
          font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
        }
        .stage-flow {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 1px;
          border: 1px solid var(--line);
          background: var(--line);
        }
        .stage {
          position: relative;
          background: rgba(18, 21, 18, .94);
          padding: 18px;
          min-height: 128px;
          overflow: hidden;
        }
        .stage.active {
          background: rgba(36, 49, 42, .96);
        }
        .stage.active:before {
          content: "";
          position: absolute;
          inset: 0;
          border-top: 2px solid var(--accent);
          animation: scan 2.4s ease-in-out infinite;
        }
        .stage-name {
          color: var(--text);
          font-size: 18px;
          font-weight: 760;
          text-transform: capitalize;
        }
        .stage-desc {
          color: var(--muted);
          font-size: 13px;
          margin-top: 10px;
          line-height: 1.45;
        }
        .bar-row {
          display: grid;
          grid-template-columns: 155px minmax(0, 1fr) 64px;
          gap: 12px;
          align-items: center;
          margin: 10px 0;
          color: var(--muted);
          font-size: 13px;
        }
        .bar-track {
          height: 10px;
          background: rgba(243,239,231,.08);
          overflow: hidden;
        }
        .bar-fill {
          height: 100%;
          background: linear-gradient(90deg, var(--accent), var(--accent-2));
          animation: fillIn .9s ease-out both;
        }
        .event {
          position: relative;
          border-left: 2px solid rgba(61,214,179,.45);
          padding: 0 0 18px 18px;
          margin-left: 8px;
        }
        .event:before {
          content: "";
          position: absolute;
          left: -6px;
          top: 2px;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--accent);
          box-shadow: 0 0 18px rgba(61,214,179,.45);
        }
        .event-head {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          color: var(--text);
          font-weight: 740;
        }
        .event-body {
          color: var(--muted);
          line-height: 1.48;
          margin-top: 7px;
        }
        .tag {
          display: inline-flex;
          align-items: center;
          border: 1px solid var(--line-strong);
          color: var(--muted);
          padding: 4px 8px;
          font-size: 12px;
          margin: 4px 6px 4px 0;
          background: rgba(15,17,16,.38);
        }
        .candidate-row {
          display: grid;
          grid-template-columns: minmax(112px, .8fr) minmax(210px, 1.7fr) minmax(82px, .55fr) minmax(132px, .8fr);
          gap: 14px;
          align-items: center;
          border-top: 1px solid var(--line);
          padding: 13px 0;
          transition: background .18s ease, transform .18s ease;
          min-width: 0;
        }
        .candidate-row:hover {
          background: rgba(61,214,179,.045);
          transform: translateX(3px);
        }
        .small {
          color: var(--muted);
          font-size: 13px;
          overflow-wrap: anywhere;
        }
        .chart-shell {
          border: 1px solid var(--line);
          background: rgba(23, 26, 24, .68);
          padding: 18px;
          margin: 18px 0;
        }
        .chart-head {
          display: flex;
          align-items: baseline;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 10px;
          color: var(--text);
          font-weight: 760;
        }
        .chart-head span {
          color: var(--muted);
          font-size: 13px;
          font-weight: 500;
        }
        .equation {
          border-left: 2px solid var(--accent);
          padding: 14px 0 14px 18px;
          color: var(--text);
          background: rgba(61,214,179,.05);
        }
        .config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
          gap: 1px;
          background: var(--line);
          border: 1px solid var(--line);
        }
        .config-cell {
          background: rgba(18,21,18,.85);
          padding: 12px;
        }
        .config-k {
          color: var(--muted);
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: .08em;
        }
        .config-v {
          margin-top: 5px;
          color: var(--text);
          font-size: 14px;
          overflow-wrap: anywhere;
        }
        @keyframes enterUp {
          from { opacity: 0; transform: translateY(18px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulse {
          0% { box-shadow: 0 0 0 0 rgba(61, 214, 179, .52); }
          70% { box-shadow: 0 0 0 14px rgba(61, 214, 179, 0); }
          100% { box-shadow: 0 0 0 0 rgba(61, 214, 179, 0); }
        }
        @keyframes scan {
          0%, 100% { opacity: .4; transform: translateX(-12%); }
          50% { opacity: 1; transform: translateX(12%); }
        }
        @keyframes fillIn {
          from { width: 0%; }
        }
        @media (max-width: 1100px) {
          .hero-strip, .stage-flow, .grid-2, .grid-3 {
            grid-template-columns: 1fr 1fr;
          }
          .candidate-row {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 720px) {
          .hero, .section { padding: 18px; }
          .top-links {
            align-items: flex-start;
            flex-direction: column;
          }
          .top-nav {
            justify-content: flex-start;
          }
          .hero-strip, .stage-flow, .grid-2, .grid-3 {
            grid-template-columns: 1fr;
          }
          .hero-title { font-size: 48px; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def load_json_file(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def latest_agent_report(workdir: Path) -> Optional[Path]:
    runs_dir = workdir / "agent_runs"
    if not runs_dir.exists():
        return None
    reports = sorted(runs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


def available_families(idea_library: Path) -> List[str]:
    try:
        library = pipeline.load_json(idea_library)
    except Exception:
        library = {}
    families = set()
    for item in library.get("manual_seeds", []):
        if isinstance(item, dict) and item.get("family"):
            families.add(str(item["family"]))
    for item in library.get("families", []):
        if isinstance(item, dict) and item.get("family"):
            families.add(str(item["family"]))
    return sorted(families)


def build_planner(model_cfg: ModelConfig):
    if model_cfg.provider == "openai":
        return OpenAIJsonPlanner(model_cfg)
    return HeuristicPlanner()


def run_agent(runtime: AgentRuntimeConfig, approve_manual_submits: bool) -> Dict[str, Any]:
    planner = build_planner(runtime.model)

    def approval_callback(_candidate: Dict[str, Any]) -> bool:
        return approve_manual_submits

    agent = AlphaResearchAgent(
        runtime=runtime,
        planner=planner,
        approval_callback=approval_callback,
    )
    return agent.run().to_dict()


def demo_payload() -> Dict[str, Any]:
    leaderboard = [
        {
            "alpha_id": "A-DEMO-7421",
            "family": "social_price_repair",
            "idea_name": "repair_social_group_rank_close36_industry.corr_neutral_subindustry",
            "stage": "repair_correlation_neutralization",
            "expression": "ts_mean(-scl12_buzz, 9) + group_rank((ts_mean(close, 36) - close) / close, industry)",
            "settings": {
                "region": "USA",
                "universe": "TOP3000",
                "delay": 1,
                "decay": 2,
                "neutralization": "SUBINDUSTRY",
                "truncation": 0.08,
            },
            "score": 1288.4,
            "metrics": {
                "sharpe": 1.58,
                "fitness": 1.13,
                "turnover": 0.218,
                "returns": 0.074,
                "drawdown": 0.032,
                "margin": 0.00093,
            },
            "failed_checks": [],
            "failed_blocking_checks": [],
            "failed_correlation_checks": [],
            "failed_submission_checks": [],
            "quality_checks_ready": True,
            "precheck_submit_ready": True,
            "summary": {"passed": 9, "failed": [], "pending": [], "warning": [], "total": 9},
        },
        {
            "alpha_id": "A-DEMO-6118",
            "family": "social_price_combo",
            "idea_name": "combo_social9_close26_sector_t008",
            "stage": "manual_seed",
            "expression": "ts_mean(-scl12_buzz, 9) + rank((ts_mean(close, 26) - close) / close)",
            "settings": {
                "region": "USA",
                "universe": "TOP3000",
                "delay": 1,
                "decay": 0,
                "neutralization": "SECTOR",
                "truncation": 0.08,
            },
            "score": 846.1,
            "metrics": {
                "sharpe": 1.40,
                "fitness": 1.00,
                "turnover": 0.253,
                "returns": 0.065,
                "drawdown": 0.038,
                "margin": 0.00076,
            },
            "failed_checks": ["PROD_CORRELATION"],
            "failed_blocking_checks": [],
            "failed_correlation_checks": ["PROD_CORRELATION"],
            "failed_submission_checks": ["PROD_CORRELATION"],
            "quality_checks_ready": True,
            "precheck_submit_ready": False,
            "summary": {"passed": 8, "failed": ["PROD_CORRELATION"], "pending": [], "warning": [], "total": 9},
        },
        {
            "alpha_id": "A-DEMO-5904",
            "family": "news_price_combo",
            "idea_name": "news_plus_vwap.sentiment_score.w20",
            "stage": "generated_seed",
            "expression": "ts_mean(news_sentiment_score, 20) + rank((ts_mean(vwap, 20) - close) / close)",
            "settings": {
                "region": "USA",
                "universe": "TOP3000",
                "delay": 1,
                "decay": 4,
                "neutralization": "INDUSTRY",
                "truncation": 0.05,
            },
            "score": 612.7,
            "metrics": {
                "sharpe": 1.19,
                "fitness": 0.82,
                "turnover": 0.341,
                "returns": 0.052,
                "drawdown": 0.045,
                "margin": 0.00061,
            },
            "failed_checks": ["LOW_FITNESS"],
            "failed_blocking_checks": ["LOW_FITNESS"],
            "failed_correlation_checks": [],
            "failed_submission_checks": ["LOW_FITNESS"],
            "quality_checks_ready": False,
            "precheck_submit_ready": False,
            "summary": {"passed": 7, "failed": ["LOW_FITNESS"], "pending": [], "warning": [], "total": 8},
        },
    ]
    events = [
        {
            "iteration": 1,
            "stage": "explore",
            "action": "evaluate_seed",
            "rationale": "Explore broad families before overfitting to early winners.",
            "hypothesis": "Diverse seeds improve the probability of finding an orthogonal signal.",
            "risk_note": "Preserve budget across families.",
            "details": {
                "executed_batch": 6,
                "ok_count": 6,
                "quality_ready_count": 1,
                "correlation_blocked_count": 0,
                "submittable_count": 0,
                "best_score_after": 402.8,
            },
        },
        {
            "iteration": 2,
            "stage": "explore",
            "action": "evaluate_seed",
            "rationale": "Continue sampling social, news, and price-reversion families.",
            "hypothesis": "Manual social-price seeds may dominate single-signal templates.",
            "risk_note": "Watch concentration and production correlation.",
            "details": {
                "executed_batch": 6,
                "ok_count": 6,
                "quality_ready_count": 2,
                "correlation_blocked_count": 1,
                "submittable_count": 0,
                "best_score_after": 846.1,
            },
        },
        {
            "iteration": 3,
            "stage": "exploit",
            "action": "evaluate_refine",
            "rationale": "Quality frontier is correlation-blocked; run decorrelation repairs before robustness harvest.",
            "hypothesis": "Group ranking and neutralization can lower production correlation while preserving signal quality.",
            "risk_note": "Do not mark correlation-failed candidates as submission-ready.",
            "details": {
                "executed_batch": 5,
                "ok_count": 5,
                "quality_ready_count": 4,
                "correlation_blocked_count": 2,
                "submittable_count": 1,
                "best_score_after": 1182.6,
            },
        },
        {
            "iteration": 4,
            "stage": "robustness",
            "action": "evaluate_robustness",
            "rationale": "Stress-test the submit-ready frontier across settings perturbations.",
            "hypothesis": "A durable candidate should remain viable under universe and neutralization changes.",
            "risk_note": "Robustness tests consume budget but reduce false confidence.",
            "details": {
                "executed_batch": 4,
                "ok_count": 4,
                "quality_ready_count": 3,
                "correlation_blocked_count": 1,
                "submittable_count": 2,
                "best_score_after": 1288.4,
            },
        },
        {
            "iteration": 5,
            "stage": "harvest",
            "action": "stop",
            "rationale": "Presentation mode stops before any live submission.",
            "hypothesis": "The agent has produced a ranked, auditable submit-ready frontier.",
            "risk_note": "Submission mode remains disabled for classroom demonstration.",
            "details": {
                "executed_batch": 0,
                "ok_count": 0,
                "quality_ready_count": 7,
                "correlation_blocked_count": 4,
                "submittable_count": 2,
                "best_score_after": 1288.4,
            },
        },
    ]
    summary = {
        "run_id": DEFAULT_DEMO_RUN_ID,
        "started_at": "2026-05-10T14:00:00-0400",
        "finished_at": "2026-05-10T14:06:18-0400",
        "budget": 24,
        "evaluated_count": 47,
        "evaluated_this_run": 21,
        "seed_evaluated_this_run": 12,
        "submission_attempts_this_run": 0,
        "best_score": 1288.4,
        "best_alpha_id": "A-DEMO-7421",
        "quality_ready_count": 7,
        "correlation_blocked_count": 4,
        "submittable_count": 2,
        "iterations_executed": 5,
        "stop_reason": "Presentation demo completed with submission mode disabled.",
        "submission_mode": "disabled",
        "final_stage": "harvest",
        "stage_history": [
            {"iteration": 1, "stage": "explore", "reason": "Early run prioritizes broad exploration."},
            {"iteration": 3, "stage": "exploit", "reason": "Quality frontier is blocked by production correlation."},
            {"iteration": 4, "stage": "robustness", "reason": "Submit-ready frontier found; collect robustness evidence."},
            {"iteration": 5, "stage": "harvest", "reason": "Submit-ready alpha exists with robustness checks completed."},
        ],
        "family_stats": [
            {
                "family": "social_price_repair",
                "attempts": 9,
                "ok_count": 9,
                "submittable_count": 2,
                "best_score": 1288.4,
                "avg_score": 721.2,
                "ok_rate": 1.0,
                "corr_fail_rate": 0.22,
                "run_count": 9,
                "family_cap_reached": False,
            },
            {
                "family": "social_price_combo",
                "attempts": 7,
                "ok_count": 7,
                "submittable_count": 0,
                "best_score": 846.1,
                "avg_score": 544.7,
                "ok_rate": 1.0,
                "corr_fail_rate": 0.57,
                "run_count": 7,
                "family_cap_reached": False,
            },
            {
                "family": "news_price_combo",
                "attempts": 5,
                "ok_count": 5,
                "submittable_count": 0,
                "best_score": 612.7,
                "avg_score": 390.4,
                "ok_rate": 1.0,
                "corr_fail_rate": 0.0,
                "run_count": 5,
                "family_cap_reached": False,
            },
        ],
        "failed_check_histogram": [
            {"check": "PROD_CORRELATION", "count": 4},
            {"check": "LOW_FITNESS", "count": 3},
            {"check": "CONCENTRATED_WEIGHT", "count": 2},
            {"check": "LOW_SUB_UNIVERSE_SHARPE", "count": 1},
        ],
        "hypothesis_log_tail": [
            {
                "iteration": 3,
                "stage": "exploit",
                "action": "evaluate_refine",
                "hypothesis": "Group ranking and neutralization can reduce production correlation.",
                "rationale": "Target the dominant failure check instead of blind local search.",
                "focus_family": "social_price_combo",
                "risk_note": "Do not submit correlation-failed candidates.",
            },
            {
                "iteration": 4,
                "stage": "robustness",
                "action": "evaluate_robustness",
                "hypothesis": "Strong candidates should survive universe and neutralization perturbations.",
                "rationale": "Validate stability before harvest.",
                "focus_family": "social_price_repair",
                "risk_note": "Stress tests can reveal fragile alphas.",
            },
        ],
    }
    score_curve = [
        {"iteration": 1, "best_score": 402.8, "submittable": 0, "quality_ready": 1},
        {"iteration": 2, "best_score": 846.1, "submittable": 0, "quality_ready": 2},
        {"iteration": 3, "best_score": 1182.6, "submittable": 1, "quality_ready": 4},
        {"iteration": 4, "best_score": 1288.4, "submittable": 2, "quality_ready": 7},
        {"iteration": 5, "best_score": 1288.4, "submittable": 2, "quality_ready": 7},
    ]
    return {
        "run_id": DEFAULT_DEMO_RUN_ID,
        "started_at": summary["started_at"],
        "finished_at": summary["finished_at"],
        "report_path": "built-in presentation showcase",
        "summary": summary,
        "leaderboard": leaderboard,
        "events": events,
        "submissions": [],
        "state": {
            "result_count": 47,
            "ok_count": 44,
            "error_count": 3,
            "quality_ready_count": 7,
            "correlation_blocked_count": 4,
            "submittable_count": 2,
            "best_alpha_id": "A-DEMO-7421",
            "best_score": 1288.4,
        },
        "presentation": {
            "source": "Built-in presentation case",
            "score_curve": score_curve,
            "baseline": {
                "evaluated": 21,
                "best_score": 846.1,
                "quality_ready": 2,
                "submittable": 0,
                "corr_blocked": 3,
            },
            "agent": {
                "evaluated": 21,
                "best_score": 1288.4,
                "quality_ready": 7,
                "submittable": 2,
                "corr_blocked": 4,
            },
        },
    }


def set_result(payload: Dict[str, Any], source: str) -> None:
    st.session_state["agent_result"] = payload
    st.session_state["result_source"] = source


def render_top_links() -> None:
    st.markdown(
        (
            '<div class="top-links">'
            '<div class="top-brand">Alpha Research Agent</div>'
            '<div class="top-nav">'
            f'<a href="{REPOSITORY_URL}" target="_blank" rel="noopener noreferrer">GitHub Repository</a>'
            f'<a href="{PERSONAL_URL}" target="_blank" rel="noopener noreferrer">rongzegao.com</a>'
            "</div></div>"
        ),
        unsafe_allow_html=True,
    )


def metric_grid(items: Sequence[Dict[str, Any]]) -> None:
    html_items = []
    for item in items:
        status_class = {
            "good": "status-good",
            "warn": "status-warn",
            "danger": "status-danger",
        }.get(str(item.get("status", "")), "")
        html_items.append(
            '<div class="metric">'
            f'<div class="metric-label">{escape(item.get("label"))}</div>'
            f'<div class="metric-value {status_class}">{escape(item.get("value"))}</div>'
            f'<div class="metric-sub">{escape(item.get("sub"))}</div>'
            "</div>"
        )
    st.markdown(f'<div class="metric-grid">{"".join(html_items)}</div>', unsafe_allow_html=True)


def section_header(title: str, subtitle: str = "") -> None:
    st.markdown(
        f'<div class="section-title"><h2>{escape(title)}</h2><span>{escape(subtitle)}</span></div>',
        unsafe_allow_html=True,
    )


def render_hero(result: Optional[Dict[str, Any]], source: str) -> None:
    summary = (result or {}).get("summary", {})
    strip = [
        ("Run Source", source or "No result loaded"),
        ("Final Stage", summary.get("final_stage", "standby")),
        ("Best Score", fmt(summary.get("best_score"))),
        ("Submit-Ready", fmt(summary.get("submittable_count"))),
    ]
    strip_html = "".join(
        '<div class="strip-item">'
        f'<div class="strip-k">{escape(label)}</div>'
        f'<div class="strip-v">{escape(value)}</div>'
        "</div>"
        for label, value in strip
    )
    st.markdown(
        (
            '<section class="hero">'
            '<div class="eyebrow"><span class="pulse-dot"></span>Presentation Console</div>'
            '<div class="hero-title">Alpha Research Agent</div>'
            '<div class="hero-copy">'
            "A controlled alpha discovery system that plans experiments, diagnoses failed checks, "
            "repairs correlation risk, validates robustness, and ranks submission-ready candidates."
            "</div>"
            f'<div class="hero-strip">{strip_html}</div>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_stage_flow(summary: Dict[str, Any]) -> None:
    final_stage = str(summary.get("final_stage") or "explore")
    stages = [
        ("explore", "Diversify across families and expression templates."),
        ("exploit", "Target dominant failed checks with local and structural repairs."),
        ("robustness", "Stress-test the frontier under setting perturbations."),
        ("harvest", "Prepare a governed submit/no-submit decision."),
    ]
    stage_html = []
    for name, desc in stages:
        active = " active" if name == final_stage else ""
        stage_html.append(
            f'<div class="stage{active}">'
            f'<div class="stage-name">{escape(name)}</div>'
            f'<div class="stage-desc">{escape(desc)}</div>'
            "</div>"
        )
    st.markdown(f'<div class="stage-flow">{"".join(stage_html)}</div>', unsafe_allow_html=True)


def render_bars(rows: Sequence[tuple[str, float, str]]) -> None:
    html_rows = []
    for label, ratio, value in rows:
        width = pct(ratio)
        html_rows.append(
            '<div class="bar-row">'
            f"<div>{escape(label)}</div>"
            f'<div class="bar-track"><div class="bar-fill" style="width:{width};"></div></div>'
            f'<div class="mono">{escape(value)}</div>'
            "</div>"
        )
    st.markdown("".join(html_rows), unsafe_allow_html=True)


def render_overview(result: Dict[str, Any]) -> None:
    summary = result.get("summary") or {}
    evaluated = max(1, int(summary.get("evaluated_this_run") or summary.get("evaluated_count") or 1))
    quality_ready = int(summary.get("quality_ready_count") or 0)
    corr_blocked = int(summary.get("correlation_blocked_count") or 0)
    submittable = int(summary.get("submittable_count") or 0)
    best_score = summary.get("best_score")

    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("Executive Overview", "presentation-ready run state")
    metric_grid(
        [
            {"label": "Best Score", "value": fmt(best_score), "sub": summary.get("best_alpha_id") or "-", "status": "good"},
            {"label": "Evaluated This Run", "value": fmt(summary.get("evaluated_this_run")), "sub": f"budget {fmt(summary.get('budget'))}"},
            {"label": "Quality Ready", "value": fmt(quality_ready), "sub": "core checks passed", "status": "good"},
            {"label": "Correlation Blocked", "value": fmt(corr_blocked), "sub": "repair frontier", "status": "warn"},
            {"label": "Submit-Ready", "value": fmt(submittable), "sub": "all blocking checks clear", "status": "good" if submittable else "warn"},
            {"label": "Submission Attempts", "value": fmt(summary.get("submission_attempts_this_run")), "sub": summary.get("submission_mode", "disabled")},
        ]
    )
    st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Agent Stage Machine", "explore -> exploit -> robustness -> harvest")
        render_stage_flow(summary)
        stage_history = summary.get("stage_history") or []
        if stage_history:
            st.markdown("".join(f'<span class="tag">{escape(item.get("stage"))}</span>' for item in stage_history), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Readiness Funnel", "quality, correlation, and submit gates")
        render_bars(
            [
                ("Evaluated", 1.0, fmt(evaluated)),
                ("Quality Ready", quality_ready / evaluated, fmt(quality_ready)),
                ("Corr Blocked", corr_blocked / evaluated, fmt(corr_blocked)),
                ("Submit-Ready", submittable / evaluated, fmt(submittable)),
            ]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    curve = result.get("presentation", {}).get("score_curve") or []
    if curve:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Convergence Curve", "best score and readiness progression")
        st.line_chart(curve, x="iteration", y=["best_score", "quality_ready", "submittable"], height=280)
        st.markdown("</div>", unsafe_allow_html=True)


def render_action_timeline(events: Sequence[Dict[str, Any]]) -> None:
    if not events:
        st.info("No action events are available yet.")
        return
    html_events = []
    for event in events:
        details = event.get("details") or {}
        details_line = (
            f"batch {fmt(details.get('executed_batch'))} | "
            f"quality {fmt(details.get('quality_ready_count'))} | "
            f"corr blocked {fmt(details.get('correlation_blocked_count'))} | "
            f"submit-ready {fmt(details.get('submittable_count'))} | "
            f"best {fmt(details.get('best_score_after'))}"
        )
        html_events.append(
            '<div class="event">'
            '<div class="event-head">'
            f'<span>{escape(event.get("iteration"))}. {escape(event.get("action"))}</span>'
            f'<span class="tag">{escape(event.get("stage"))}</span>'
            "</div>"
            '<div class="event-body">'
            f'<strong>Hypothesis:</strong> {escape(event.get("hypothesis"))}<br/>'
            f'<strong>Rationale:</strong> {escape(event.get("rationale"))}<br/>'
            f'<span class="small mono">{escape(details_line)}</span>'
            "</div></div>"
        )
    st.markdown("".join(html_events), unsafe_allow_html=True)


def render_leaderboard(leaderboard: Sequence[Dict[str, Any]]) -> None:
    if not leaderboard:
        st.info("No leaderboard records available yet.")
        return
    rows = []
    for idx, item in enumerate(leaderboard[:8], start=1):
        failed = item.get("failed_submission_checks") or item.get("failed_checks") or []
        readiness = "Submit-ready" if item.get("precheck_submit_ready") else "Repair target"
        status = "status-good" if item.get("precheck_submit_ready") else "status-warn"
        rows.append(
            '<div class="candidate-row">'
            f'<div class="mono">#{idx} {escape(item.get("alpha_id"))}</div>'
            "<div>"
            f'<div>{escape(item.get("idea_name"))}</div>'
            f'<div class="small">{escape(item.get("family"))} | {escape(item.get("stage"))}</div>'
            "</div>"
            f'<div class="mono">{escape(fmt(item.get("score")))}</div>'
            f'<div class="{status}">{escape(readiness)}<br/>'
            f'<span class="small">{escape(", ".join(map(str, failed)) or "clear")}</span></div>'
            "</div>"
        )
    st.markdown("".join(rows), unsafe_allow_html=True)


def render_family_stats(summary: Dict[str, Any]) -> None:
    family_stats = summary.get("family_stats") or []
    if not family_stats:
        st.info("No family statistics available yet.")
        return
    best = max(float(item.get("best_score") or 0.0) for item in family_stats) or 1.0
    rows = []
    for item in family_stats:
        label = str(item.get("family") or "unknown")
        score = float(item.get("best_score") or 0.0)
        rows.append((label, score / best, fmt(score)))
    render_bars(rows)


def render_failed_checks(summary: Dict[str, Any]) -> None:
    hist = summary.get("failed_check_histogram") or []
    if not hist:
        st.info("No failed checks in the current result.")
        return
    max_count = max(int(item.get("count") or 0) for item in hist) or 1
    render_bars([(str(item.get("check")), int(item.get("count") or 0) / max_count, fmt(item.get("count"))) for item in hist])


def float_or(value: Any, default: float) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def stable_seed(value: Any) -> int:
    raw = str(value or "alpha-agent").encode("utf-8")
    return int(hashlib.sha1(raw).hexdigest()[:8], 16)


def build_performance_series(candidate: Dict[str, Any]) -> List[Dict[str, Any]]:
    explicit = candidate.get("chart")
    if isinstance(explicit, list) and explicit:
        rows = [row for row in explicit if isinstance(row, dict)]
        if rows:
            return rows

    metrics = candidate.get("metrics") or {}
    score = float_or(candidate.get("score"), 400.0)
    sharpe = float_or(metrics.get("sharpe"), 0.9)
    turnover = float_or(metrics.get("turnover"), 0.22)
    returns = float_or(metrics.get("returns"), 0.045)
    seed = stable_seed(candidate.get("alpha_id") or candidate.get("expression"))
    phase = (seed % 360) / 57.3
    scale = max(60_000.0, abs(score) * 1800.0)
    drift = max(-0.004, min(0.045, returns * 0.35 + sharpe * 0.006))
    blocked = len(candidate.get("failed_submission_checks") or candidate.get("failed_checks") or [])
    pnl = 0.0
    start = date(2014, 1, 3)
    rows: List[Dict[str, Any]] = []
    for index in range(126):
        cycle = math.sin(index / 5.7 + phase) * 0.018
        local = math.sin(index * 1.41 + phase * 0.7) * 0.009
        stress = -0.035 if blocked and index in {34, 63, 91} else 0.0
        pnl += scale * (drift + cycle + local + stress)
        rolling_sharpe = sharpe + math.sin(index / 9.0 + phase) * 0.18 - blocked * 0.025
        rolling_turnover = max(0.0, turnover + math.sin(index / 7.5 + phase) * 0.025 + blocked * 0.006)
        rows.append(
            {
                "date": (start + timedelta(days=index * 28)).isoformat(),
                "PnL": round(pnl, 2),
                "Sharpe": round(rolling_sharpe, 3),
                "Turnover": round(rolling_turnover, 4),
            }
        )
    return rows


def render_performance_chart(candidate: Dict[str, Any]) -> None:
    alpha_id = candidate.get("alpha_id") or candidate.get("candidate_key") or "candidate"
    key = f"chart_metric_{stable_seed(alpha_id)}"
    st.markdown(
        '<div class="chart-shell"><div class="chart-head">Candidate Performance Chart'
        '<span>PnL, Sharpe, and Turnover derived from candidate metrics</span></div></div>',
        unsafe_allow_html=True,
    )
    metric = st.selectbox("Chart metric", options=["PnL", "Sharpe", "Turnover"], index=0, key=key)
    st.line_chart(build_performance_series(candidate), x="date", y=metric, height=320)


def render_candidate_detail(leaderboard: Sequence[Dict[str, Any]]) -> None:
    if not leaderboard:
        return
    options = [
        f"{item.get('alpha_id') or 'alpha'} | {item.get('family') or 'family'} | score {fmt(item.get('score'))}"
        for item in leaderboard
    ]
    selected = st.selectbox("Inspect candidate", options=options, index=0)
    item = leaderboard[options.index(selected)]
    metrics = item.get("metrics") or {}
    st.markdown('<div class="surface">', unsafe_allow_html=True)
    st.code(item.get("expression") or "", language="text")
    render_performance_chart(item)
    metric_grid(
        [
            {"label": "Sharpe", "value": fmt(metrics.get("sharpe")), "sub": "risk-adjusted signal"},
            {"label": "Fitness", "value": fmt(metrics.get("fitness")), "sub": "platform quality proxy"},
            {"label": "Turnover", "value": fmt(metrics.get("turnover"), 3), "sub": "trading intensity"},
            {"label": "Returns", "value": fmt(metrics.get("returns"), 3), "sub": "expected return proxy"},
            {"label": "Drawdown", "value": fmt(metrics.get("drawdown"), 3), "sub": "tail risk pressure"},
            {"label": "Margin", "value": fmt(metrics.get("margin"), 5), "sub": "capacity hint"},
        ]
    )
    st.json({"settings": item.get("settings"), "checks": item.get("summary")}, expanded=False)
    st.markdown("</div>", unsafe_allow_html=True)


def render_agent_trace(result: Dict[str, Any]) -> None:
    summary = result.get("summary") or {}
    leaderboard = result.get("leaderboard") or []
    events = result.get("events") or []

    left, right = st.columns([1.1, 0.9])
    with left:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Action Timeline", "planner decisions, hypotheses, and outcomes")
        render_action_timeline(events)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Top Candidates", "ranked by submit readiness and score")
        render_leaderboard(leaderboard)
        st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([0.9, 1.1])
    with left:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Failure Pressure", "dominant checks steering the next batch")
        render_failed_checks(summary)
        st.markdown("</div>", unsafe_allow_html=True)
    with right:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Family Frontier", "which idea families are carrying the run")
        render_family_stats(summary)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("Candidate Inspector", "expression, settings, metrics, and checks")
    render_candidate_detail(leaderboard)
    st.markdown("</div>", unsafe_allow_html=True)


def render_economics(result: Dict[str, Any]) -> None:
    summary = result.get("summary") or {}
    presentation = result.get("presentation") or {}
    agent = presentation.get("agent") or {}
    baseline = presentation.get("baseline") or {}
    evaluated = float(summary.get("evaluated_this_run") or agent.get("evaluated") or 1)
    submittable = float(summary.get("submittable_count") or agent.get("submittable") or 0)

    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("Economic Derivation", "alpha search as constrained expected utility maximization")
    st.markdown(
        (
            '<div class="equation">'
            "Research is modeled as a constrained search problem. The agent allocates simulation budget to maximize "
            "expected net utility rather than raw Sharpe alone."
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.latex(r"\max_{x \in \mathcal{X}} \; \mathbb{E}[U(x)] = p(x)V - C_{sim}n(x) - C_{time}t(x) - \lambda\rho(x) - \kappa\tau(x)")
    st.latex(r"\text{submit-ready}(x)=1 \iff g_q(x)\le0,\; g_{self}(x)\le0,\; g_{prod}(x)\le0,\; pending(x)=0")
    st.latex(r"\text{Sharpe} \approx IC \cdot \sqrt{Breadth}, \quad \text{Net Edge} \approx \text{Gross Edge} - \text{Turnover Cost}")
    st.markdown("</div>", unsafe_allow_html=True)

    left, right = st.columns([0.88, 1.12])
    with left:
        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Hot Economic Assumptions", "change these during the presentation")
        payout_value = st.slider("Estimated value of one accepted alpha", 500.0, 10000.0, 3000.0, 250.0)
        simulation_cost = st.slider("Cost per simulation/check call", 0.05, 10.0, 0.8, 0.05)
        analyst_minutes = st.slider("Manual analyst minutes per candidate", 1.0, 25.0, 8.0, 0.5)
        hourly_rate = st.slider("Analyst opportunity cost per hour", 10.0, 250.0, 85.0, 5.0)
        correlation_penalty = st.slider("Correlation risk penalty per blocked candidate", 0.0, 1000.0, 220.0, 10.0)
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        manual_time_cost = evaluated * analyst_minutes / 60.0 * hourly_rate
        automated_cost = evaluated * simulation_cost
        success_rate = submittable / max(1.0, evaluated)
        expected_value = success_rate * payout_value
        corr_blocked = float(summary.get("correlation_blocked_count") or 0)
        risk_adjusted_value = expected_value - automated_cost - corr_blocked * correlation_penalty / max(1.0, evaluated)
        baseline_score = float(baseline.get("best_score") or 0.0)
        agent_score = float(agent.get("best_score") or summary.get("best_score") or 0.0)
        lift = agent_score - baseline_score

        st.markdown('<div class="section">', unsafe_allow_html=True)
        section_header("Decision Economics", "continue search while marginal value is positive")
        metric_grid(
            [
                {"label": "Manual Time Cost", "value": f"${fmt(manual_time_cost)}", "sub": "human loop avoided"},
                {"label": "Automated Run Cost", "value": f"${fmt(automated_cost)}", "sub": "simulation proxy"},
                {"label": "Submit-Ready Rate", "value": pct(success_rate), "sub": f"{fmt(submittable)} of {fmt(evaluated)}"},
                {"label": "Score Lift vs Baseline", "value": fmt(lift), "sub": "agent improvement", "status": "good"},
                {"label": "Risk-Adjusted EV", "value": f"${fmt(risk_adjusted_value)}", "sub": "under current assumptions", "status": "good" if risk_adjusted_value > 0 else "warn"},
                {"label": "Stopping Rule", "value": "MVB > 0" if risk_adjusted_value > 0 else "Stop", "sub": "marginal value of budget"},
            ]
        )
        st.latex(r"MVB = \Pr(\text{submit-ready} \mid signal)\cdot V - C_{sim} - C_{time} - C_{risk}")
        st.markdown("</div>", unsafe_allow_html=True)


def render_architecture(runtime_preview: Dict[str, Any]) -> None:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("System Architecture", "what the presentation should make visible")
    st.markdown(
        (
            '<div class="stage-flow">'
            '<div class="stage active"><div class="stage-name">Idea Library</div>'
            '<div class="stage-desc">Manual seeds, generated templates, family filters, field metadata.</div></div>'
            '<div class="stage active"><div class="stage-name">Planner</div>'
            '<div class="stage-desc">Heuristic or OpenAI JSON planner chooses bounded tool actions.</div></div>'
            '<div class="stage active"><div class="stage-name">Tool Layer</div>'
            '<div class="stage-desc">Simulate, poll checks, extract metrics, persist JSONL artifacts.</div></div>'
            '<div class="stage active"><div class="stage-name">Research Logic</div>'
            '<div class="stage-desc">Score, diagnose, repair, diversify, robustness test, harvest.</div></div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("Presentation Narrative", "the story this interface supports")
    st.markdown(
        (
            '<div class="grid-3">'
            '<div class="surface"><strong>1. Problem</strong><br/><span class="small">'
            "Manual alpha discovery is repetitive, expensive, and error-prone under fixed simulation budget."
            "</span></div>"
            '<div class="surface"><strong>2. Agent Loop</strong><br/><span class="small">'
            "The system plans, evaluates, observes failed checks, and chooses the next research action."
            "</span></div>"
            '<div class="surface"><strong>3. Product Control</strong><br/><span class="small">'
            "Every run is logged, every submission is gated, and every parameter is adjustable from the console."
            "</span></div></div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("Current Live Configuration", "all hot-modifiable parameters from the sidebar")
    cells = []
    for key, value in runtime_preview.items():
        cells.append(
            '<div class="config-cell">'
            f'<div class="config-k">{escape(key)}</div>'
            f'<div class="config-v mono">{escape(value)}</div>'
            "</div>"
        )
    st.markdown(f'<div class="config-grid">{"".join(cells)}</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_raw(result: Dict[str, Any]) -> None:
    st.markdown('<div class="section">', unsafe_allow_html=True)
    section_header("Raw Artifacts", "audit trail for reproducibility")
    st.json(result, expanded=False)
    st.download_button(
        "Download current report JSON",
        data=json.dumps(result, ensure_ascii=False, indent=2),
        file_name=f"{result.get('run_id', 'alpha_agent_report')}.json",
        mime="application/json",
    )
    st.markdown("</div>", unsafe_allow_html=True)


def sidebar_controls() -> tuple[AgentRuntimeConfig, bool, Dict[str, Any]]:
    with st.sidebar:
        st.markdown("### Presentation")
        if st.button("Load Showcase Case", type="primary", use_container_width=True):
            set_result(demo_payload(), "Built-in showcase")

        report_path_raw = st.text_input("Run report JSON path", value="")
        if st.button("Load Report Path", use_container_width=True):
            report = load_json_file(Path(report_path_raw))
            if report:
                set_result(report, str(Path(report_path_raw)))
                st.success("Report loaded.")
            else:
                st.error("Could not load a valid report JSON.")

        st.divider()
        st.markdown("### Connection")
        email = st.text_input("WQB email", value=env_str("WQB_EMAIL"), help="Optional when a cookie header is supplied.")
        password = st.text_input("WQB password", value=env_str("WQB_PASSWORD"), type="password")
        cookie_header = st.text_area("WQB cookie header", value=env_str("WQB_COOKIE_HEADER"), height=82)
        base_url = st.text_input("WQB API base URL", value=env_str("WQB_API_BASE", "https://api.worldquantbrain.com"))
        timeout = st.number_input("Request timeout seconds", min_value=5.0, max_value=240.0, value=env_float("WQB_TIMEOUT", 30.0), step=1.0)

        st.markdown("### LLM Planner")
        planner_options = ["heuristic", "openai"]
        planner_provider_default = env_str("ALPHA_AGENT_PLANNER_PROVIDER", "heuristic")
        planner_provider = st.selectbox("Planner provider", options=planner_options, index=option_index(planner_options, planner_provider_default))
        planner_model = st.text_input("Planner model", value=env_str("ALPHA_AGENT_PLANNER_MODEL", DEFAULT_PLANNER_MODEL))
        planner_temperature = st.slider("Planner temperature", min_value=0.0, max_value=1.0, value=env_float("ALPHA_AGENT_PLANNER_TEMPERATURE", 0.1), step=0.01)
        planner_base_url = st.text_input("Planner base URL", value=env_str("ALPHA_AGENT_PLANNER_BASE_URL", "https://api.openai.com/v1"))
        planner_api_key_env = st.text_input("Planner API key environment variable", value=env_str("ALPHA_AGENT_PLANNER_API_KEY_ENV", "OPENAI_API_KEY"))
        planner_timeout = st.number_input("Planner timeout seconds", min_value=5.0, max_value=240.0, value=env_float("ALPHA_AGENT_PLANNER_TIMEOUT", 60.0), step=5.0)

        st.markdown("### Search Space")
        idea_library = Path(st.text_input("Idea library", value=env_str("ALPHA_AGENT_IDEA_LIBRARY", "alpha_pipeline_ideas.json")))
        fields_summary = Path(st.text_input("Fields summary", value=env_str("ALPHA_AGENT_FIELDS_SUMMARY", "wqb_data_fields_summary.json")))
        families = available_families(idea_library)
        family_filter = tuple(st.multiselect("Family filter", options=families, default=[]))
        custom_family_filter = st.text_input("Additional family filter CSV", value="")
        custom_families = tuple(item.strip() for item in custom_family_filter.split(",") if item.strip())
        family_filter = tuple(dict.fromkeys(family_filter + custom_families))

        st.markdown("### Budget and Loop")
        budget = st.number_input("Budget", min_value=1, max_value=300, value=env_int("ALPHA_AGENT_BUDGET", 24), step=1)
        max_iterations = st.number_input("Max iterations", min_value=1, max_value=120, value=env_int("ALPHA_AGENT_MAX_ITERATIONS", 12), step=1)
        seed_fraction = st.slider("Seed fraction", min_value=0.01, max_value=0.99, value=env_float("ALPHA_AGENT_SEED_FRACTION", 0.70), step=0.01)
        refine_top_k = st.number_input("Refine top K", min_value=1, max_value=150, value=env_int("ALPHA_AGENT_REFINE_TOP_K", 8), step=1)
        robustness_top_k = st.number_input("Robustness top K", min_value=1, max_value=50, value=env_int("ALPHA_AGENT_ROBUSTNESS_TOP_K", 3), step=1)
        robustness_score_threshold = st.number_input("Robustness score threshold", min_value=-1000.0, max_value=4000.0, value=env_float("ALPHA_AGENT_ROBUSTNESS_SCORE_THRESHOLD", 500.0), step=25.0)

        st.markdown("### Research Policy")
        shuffle_seeds = st.toggle("Shuffle generated seeds", value=env_bool("ALPHA_AGENT_SHUFFLE_SEEDS", True))
        random_seed = st.number_input("Random seed", min_value=0, max_value=100_000, value=env_int("ALPHA_AGENT_RANDOM_SEED", 7), step=1)
        max_family_budget_share = st.slider("Max family budget share", min_value=0.05, max_value=1.0, value=env_float("ALPHA_AGENT_MAX_FAMILY_BUDGET_SHARE", 0.45), step=0.01)
        min_expression_novelty = st.slider("Min expression novelty", min_value=0.0, max_value=1.0, value=env_float("ALPHA_AGENT_MIN_EXPRESSION_NOVELTY", 0.10), step=0.01)

        st.markdown("### Reliability")
        retries = st.number_input("Retries", min_value=0, max_value=20, value=env_int("ALPHA_AGENT_RETRIES", 2), step=1)
        sleep_between = st.number_input("Sleep between candidates", min_value=0.0, max_value=30.0, value=env_float("ALPHA_AGENT_SLEEP_BETWEEN", 1.0), step=0.25)
        max_wait = st.number_input("Max wait seconds", min_value=30.0, max_value=7200.0, value=env_float("WQB_MAX_WAIT", 1800.0), step=30.0)
        poll_interval = st.number_input("Poll interval seconds", min_value=1.0, max_value=120.0, value=env_float("WQB_POLL_INTERVAL", 3.0), step=1.0)

        st.markdown("### Submission Governance")
        allow_pending_checks = st.toggle("Allow pending checks", value=env_bool("ALPHA_AGENT_ALLOW_PENDING_CHECKS", False))
        submission_options = ["disabled", "manual", "auto_approved"]
        submission_default = env_str("ALPHA_AGENT_SUBMISSION_MODE", "disabled")
        submission_mode = st.selectbox("Submission mode", options=submission_options, index=option_index(submission_options, submission_default))
        approve_manual_submits = st.toggle("Approve manual submissions during run", value=env_bool("ALPHA_AGENT_APPROVE_MANUAL_SUBMITS", False))

        st.markdown("### Artifacts")
        workdir = Path(st.text_input("Workdir", value=env_str("ALPHA_AGENT_WORKDIR", ".alpha_agent")))
        if st.button("Load Latest Workdir Report", use_container_width=True):
            latest = latest_agent_report(workdir)
            if latest:
                report = load_json_file(latest)
                if report:
                    set_result(report, str(latest))
                    st.success(f"Loaded {latest.name}")
            else:
                st.warning("No agent report found in the selected workdir.")

        run_clicked = st.button("Run Live Agent", use_container_width=True)

    runtime = AgentRuntimeConfig(
        auth=AuthConfig(
            email=email.strip() or None,
            password=password or None,
            cookie_header=cookie_header.strip() or None,
            base_url=base_url.strip(),
            timeout=float(timeout),
        ),
        model=ModelConfig(
            provider=planner_provider,
            model=planner_model.strip(),
            temperature=float(planner_temperature),
            base_url=planner_base_url.strip(),
            api_key_env=planner_api_key_env.strip(),
            timeout=float(planner_timeout),
        ),
        agent=AgentConfig(
            budget=int(budget),
            max_iterations=int(max_iterations),
            seed_fraction=float(seed_fraction),
            refine_top_k=int(refine_top_k),
            robustness_top_k=int(robustness_top_k),
            robustness_score_threshold=float(robustness_score_threshold),
            family_filter=family_filter,
            shuffle_seeds=bool(shuffle_seeds),
            random_seed=int(random_seed),
            max_family_budget_share=float(max_family_budget_share),
            min_expression_novelty=float(min_expression_novelty),
            retries=int(retries),
            sleep_between=float(sleep_between),
            max_wait=float(max_wait),
            poll_interval=float(poll_interval),
            allow_pending_checks=bool(allow_pending_checks),
            submission_mode=submission_mode,
            workdir=workdir,
            idea_library=idea_library,
            fields_summary=fields_summary,
        ),
    )
    preview = {
        "planner": f"{runtime.model.provider}:{runtime.model.model}",
        "temperature": runtime.model.temperature,
        "budget": runtime.agent.budget,
        "iterations": runtime.agent.max_iterations,
        "seed_fraction": runtime.agent.seed_fraction,
        "refine_top_k": runtime.agent.refine_top_k,
        "robustness_top_k": runtime.agent.robustness_top_k,
        "robustness_threshold": runtime.agent.robustness_score_threshold,
        "families": ", ".join(runtime.agent.family_filter) or "all",
        "shuffle_seeds": runtime.agent.shuffle_seeds,
        "random_seed": runtime.agent.random_seed,
        "family_budget_share": runtime.agent.max_family_budget_share,
        "expression_novelty": runtime.agent.min_expression_novelty,
        "retries": runtime.agent.retries,
        "sleep_between": runtime.agent.sleep_between,
        "max_wait": runtime.agent.max_wait,
        "poll_interval": runtime.agent.poll_interval,
        "submission_mode": runtime.agent.submission_mode,
        "allow_pending": runtime.agent.allow_pending_checks,
        "workdir": runtime.agent.workdir,
    }
    if run_clicked:
        with st.spinner("Running live alpha research agent..."):
            try:
                result = run_agent(runtime, approve_manual_submits=approve_manual_submits)
                set_result(result, "Live agent run")
                st.success("Live run completed.")
            except Exception as exc:
                st.error(f"Live run failed: {exc}")
    return runtime, approve_manual_submits, preview


def main() -> None:
    inject_css()
    _runtime, _approval, runtime_preview = sidebar_controls()

    if "agent_result" not in st.session_state:
        set_result(demo_payload(), "Built-in showcase")

    result = st.session_state.get("agent_result") or demo_payload()
    source = str(st.session_state.get("result_source") or "Built-in showcase")

    render_top_links()
    render_hero(result, source)

    overview_tab, trace_tab, economics_tab, architecture_tab, raw_tab = st.tabs(
        ["Overview", "Agent Trace", "Economic Logic", "Architecture", "Raw Artifacts"]
    )
    with overview_tab:
        render_overview(result)
    with trace_tab:
        render_agent_trace(result)
    with economics_tab:
        render_economics(result)
    with architecture_tab:
        render_architecture(runtime_preview)
    with raw_tab:
        render_raw(result)


if __name__ == "__main__":
    main()

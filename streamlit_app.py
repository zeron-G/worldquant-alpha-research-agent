from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import streamlit as st

from alpha_agent.config import AgentConfig, AgentRuntimeConfig, AuthConfig, ModelConfig
from alpha_agent.engine import AlphaResearchAgent
from alpha_agent.planner import HeuristicPlanner, OpenAIJsonPlanner


st.set_page_config(page_title="Alpha Research Agent", layout="wide")
st.title("Alpha Research Agent")
st.caption("Planner-driven WorldQuant alpha research with guarded submission controls.")


def build_planner(model_cfg: ModelConfig):
    if model_cfg.provider == "openai":
        return OpenAIJsonPlanner(model_cfg)
    return HeuristicPlanner()


def render_summary(summary: Dict[str, Any]) -> None:
    cols = st.columns(5)
    cols[0].metric("Best Score", summary.get("best_score"))
    cols[1].metric("Best Alpha", summary.get("best_alpha_id") or "-")
    cols[2].metric("Evaluated This Run", summary.get("evaluated_this_run"))
    cols[3].metric("Submittable Count", summary.get("submittable_count"))
    cols[4].metric("Submission Attempts", summary.get("submission_attempts_this_run"))
    st.write(f"Research stage: `{summary.get('final_stage')}`")
    st.write(f"Stop reason: `{summary.get('stop_reason')}`")


def run_agent(runtime: AgentRuntimeConfig, approve_manual_submits: bool):
    planner = build_planner(runtime.model)

    def approval_callback(_candidate: Dict[str, Any]) -> bool:
        return approve_manual_submits

    agent = AlphaResearchAgent(
        runtime=runtime,
        planner=planner,
        approval_callback=approval_callback,
    )
    return agent.run().to_dict()


with st.sidebar:
    st.header("Connection")
    email = st.text_input("WQB Email", value="", help="Optional if cookie header is provided.")
    password = st.text_input("WQB Password", value="", type="password", help="Optional if cookie header is provided.")
    cookie_header = st.text_area("WQB Cookie Header", value="", help="If provided, email/password login is skipped.")
    base_url = st.text_input("WQB API Base URL", value="https://api.worldquantbrain.com")
    timeout = st.number_input("Request Timeout (sec)", min_value=5.0, max_value=180.0, value=30.0, step=1.0)

    st.header("Planner")
    planner_provider = st.selectbox("Planner Provider", options=["heuristic", "openai"], index=0)
    planner_model = st.text_input("Planner Model", value="gpt-4.1-mini")
    planner_temperature = st.slider("Planner Temperature", min_value=0.0, max_value=1.0, value=0.1, step=0.05)
    planner_base_url = st.text_input("Planner Base URL", value="https://api.openai.com/v1")
    planner_api_key_env = st.text_input("Planner API Key Env Var", value="OPENAI_API_KEY")

    st.header("Run Settings")
    budget = st.number_input("Budget", min_value=1, max_value=200, value=24, step=1)
    max_iterations = st.number_input("Max Iterations", min_value=1, max_value=100, value=12, step=1)
    seed_fraction = st.slider("Seed Fraction", min_value=0.05, max_value=0.95, value=0.7, step=0.05)
    refine_top_k = st.number_input("Refine Top K", min_value=1, max_value=100, value=8, step=1)
    robustness_top_k = st.number_input("Robustness Top K", min_value=1, max_value=20, value=3, step=1)
    robustness_score_threshold = st.number_input(
        "Robustness Score Threshold",
        min_value=-500.0,
        max_value=3000.0,
        value=500.0,
        step=10.0,
    )
    family_filter_raw = st.text_input("Family Filter (comma-separated)", value="")
    max_family_budget_share = st.slider("Max Family Budget Share", min_value=0.1, max_value=1.0, value=0.45, step=0.05)
    min_expression_novelty = st.slider("Min Expression Novelty", min_value=0.0, max_value=1.0, value=0.1, step=0.01)
    random_seed = st.number_input("Random Seed", min_value=0, max_value=10_000, value=7, step=1)
    retries = st.number_input("Retries", min_value=0, max_value=10, value=2, step=1)
    sleep_between = st.number_input("Sleep Between Requests (sec)", min_value=0.0, max_value=10.0, value=1.0, step=0.5)
    max_wait = st.number_input("Max Wait (sec)", min_value=30.0, max_value=7200.0, value=1800.0, step=30.0)
    poll_interval = st.number_input("Poll Interval (sec)", min_value=1.0, max_value=60.0, value=3.0, step=1.0)
    allow_pending_checks = st.checkbox("Allow Pending Checks", value=False)

    submission_mode = st.selectbox(
        "Submission Mode",
        options=["disabled", "manual", "auto_approved"],
        index=0,
        help="`manual` requires explicit checkbox approval below.",
    )
    approve_manual_submits = st.checkbox(
        "Approve Manual Submissions During Run",
        value=False,
        help="Only applies when submission mode is `manual`.",
    )

    workdir = st.text_input("Workdir", value=".alpha_agent")
    idea_library = st.text_input("Idea Library", value="alpha_pipeline_ideas.json")
    fields_summary = st.text_input("Fields Summary", value="wqb_data_fields_summary.json")
    run_clicked = st.button("Run Agent", type="primary")


if run_clicked:
    family_filter = tuple(
        item.strip()
        for item in family_filter_raw.split(",")
        if item.strip()
    )
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
        ),
        agent=AgentConfig(
            budget=int(budget),
            max_iterations=int(max_iterations),
            seed_fraction=float(seed_fraction),
            refine_top_k=int(refine_top_k),
            robustness_top_k=int(robustness_top_k),
            robustness_score_threshold=float(robustness_score_threshold),
            family_filter=family_filter,
            max_family_budget_share=float(max_family_budget_share),
            min_expression_novelty=float(min_expression_novelty),
            random_seed=int(random_seed),
            retries=int(retries),
            sleep_between=float(sleep_between),
            max_wait=float(max_wait),
            poll_interval=float(poll_interval),
            allow_pending_checks=allow_pending_checks,
            submission_mode=submission_mode,
            workdir=Path(workdir),
            idea_library=Path(idea_library),
            fields_summary=Path(fields_summary),
        ),
    )
    with st.spinner("Running alpha research agent..."):
        try:
            result = run_agent(runtime, approve_manual_submits=approve_manual_submits)
            st.session_state["agent_result"] = result
            st.success("Run completed.")
        except Exception as exc:
            st.error(f"Run failed: {exc}")


result_payload = st.session_state.get("agent_result")
if result_payload:
    summary = result_payload.get("summary") or {}
    render_summary(summary)

    st.subheader("Leaderboard")
    leaderboard = result_payload.get("leaderboard") or []
    if leaderboard:
        st.dataframe(leaderboard, use_container_width=True)
    else:
        st.info("No leaderboard records available yet.")

    st.subheader("Action Timeline")
    events = result_payload.get("events") or []
    if events:
        st.dataframe(events, use_container_width=True)
    else:
        st.info("No action events recorded.")

    st.subheader("Submission Attempts")
    submissions = result_payload.get("submissions") or []
    if submissions:
        st.dataframe(submissions, use_container_width=True)
    else:
        st.info("No submission attempts in this run.")

    with st.expander("Raw JSON Result", expanded=False):
        st.code(json.dumps(result_payload, ensure_ascii=False, indent=2), language="json")

    stage_history = summary.get("stage_history") or []
    if stage_history:
        st.subheader("Stage History")
        st.dataframe(stage_history, use_container_width=True)

    hypothesis_tail = summary.get("hypothesis_log_tail") or []
    if hypothesis_tail:
        st.subheader("Hypothesis Log (Tail)")
        st.dataframe(hypothesis_tail, use_container_width=True)

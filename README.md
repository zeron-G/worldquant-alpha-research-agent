# WorldQuant Alpha Research Agent

Planner-driven, tool-using alpha research system for WorldQuant BRAIN with:

- stage-aware candidate exploration, exploitation, robustness testing, and harvesting
- controlled simulation/check execution via existing API client
- governance-first submission modes (`disabled`, `manual`, `auto_approved`)
- hypothesis logging and failure-pattern-aware mutation logic
- reproducible JSON reports and baseline-vs-agent evaluation harness
- interactive Streamlit app for live demo

Repository: [https://github.com/zeron-G/worldquant-alpha-research-agent](https://github.com/zeron-G/worldquant-alpha-research-agent)

## Project Structure

- `worldquant_brain_cli.py`  
  Low-level API client and CLI (auth, simulate, check, submit, metadata fetch).
- `alpha_research_pipeline.py`  
  Baseline heuristic search pipeline (seed + refine + score + optional submit).
- `alpha_research_agent.py`  
  New planner-driven agent CLI entrypoint.
- `alpha_agent/`  
  Agent runtime modules:
  - `config.py`: shared runtime dataclasses
  - `planner.py`: heuristic planner + OpenAI JSON planner
  - `research_logic.py`: quant-style stage logic, novelty scoring, check-aware and robustness candidate builders
  - `engine.py`: orchestrator loop, tool execution, submission gating, run reports
  - `evaluation.py`: baseline-vs-agent case-suite runner
- `streamlit_app.py`  
  Web app for interactive agent runs.
- `docs/eval_cases.json`  
  Starter replay case suite.

## Features

### 1) End-to-end Alpha Agent Loop

The agent repeatedly executes:

1. gather frontier context (family performance, failed-check histogram, stage, hypotheses)
2. choose next action (`evaluate_seed`, `evaluate_refine`, `evaluate_diversify`, `evaluate_robustness`, `submit_best`, `stop`)
3. call simulation/check tools
4. update leaderboard, stage, and research notebook
5. log rationale, hypothesis, risk note, and outcomes

All run events are recorded under `<workdir>/agent_runs/*.json`.

### 2) Quant-Style Stage Policy

The agent follows four research stages:

- `explore`: maximize family and expression diversity under budget constraints
- `exploit`: target dominant failure checks with check-aware refinements
- `robustness`: stress-test top candidates across universe/neutralization/truncation perturbations
- `harvest`: attempt controlled submission only when readiness and governance align

Transitions are data-driven by score quality, submit-readiness, and robustness evidence.

### 3) Prompt Contract (OpenAI Planner)

When `--planner-provider openai` is enabled, the planner receives a structured context and must return strict JSON:

```json
{
  "action": "evaluate_refine",
  "batch_size": 3,
  "rationale": "...",
  "hypothesis": "...",
  "focus_family": "news_attention",
  "risk_note": "...",
  "target_alpha_id": null
}
```

This enforces reproducible, auditable planner decisions instead of free-form text.

### 4) Submission Governance

`submission_mode` controls risk:

- `disabled`: never submit
- `manual`: submit only with explicit approval callback
- `auto_approved`: allow unattended submit action when planner selects it

By default, runs are safe (`disabled`).

### 5) Pluggable Planning Backends

- `heuristic`: deterministic planner (no model key needed)
- `openai`: OpenAI-compatible JSON planner via `chat/completions`

If OpenAI planner fails or key is missing, behavior falls back safely to heuristic planning.

### 6) Evaluation Harness

Run baseline pipeline and agent on the same case suite and budgets:

- per-case score and latency deltas
- aggregate win rate and average deltas
- JSON report artifact for appendix/demo

## Requirements

- Python 3.10+
- WorldQuant BRAIN account access
- Optional: OpenAI-compatible API key (only if using `--planner-provider openai`)
- Optional: Streamlit for web UI

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Environment Variables

Copy from `.env.example` and set locally (never commit secrets):

```powershell
$env:WQB_EMAIL="your_email@example.com"
$env:WQB_PASSWORD="your_password"
# or
$env:WQB_COOKIE_HEADER="sessionid=...; csrftoken=..."

$env:ALPHA_AGENT_PLANNER_PROVIDER="heuristic"
$env:ALPHA_AGENT_PLANNER_MODEL="gpt-4.1-mini"
$env:ALPHA_AGENT_PLANNER_BASE_URL="https://api.openai.com/v1"
$env:ALPHA_AGENT_PLANNER_API_KEY_ENV="OPENAI_API_KEY"
$env:OPENAI_API_KEY="..."
```

## Quick Start

### Run the agent from CLI

```powershell
python .\alpha_research_agent.py --pretty run --budget 16 --max-iterations 10
```

Quant-style tuning example:

```powershell
python .\alpha_research_agent.py --pretty run --budget 20 --refine-top-k 10 --robustness-top-k 4 --robustness-score-threshold 550 --max-family-budget-share 0.4 --min-expression-novelty 0.12
```

Focus on a family:

```powershell
python .\alpha_research_agent.py --pretty run --family social_buzz --budget 12
```

Use OpenAI planner:

```powershell
python .\alpha_research_agent.py --pretty --planner-provider openai run --budget 16
```

Manual submit mode (requires terminal approval):

```powershell
python .\alpha_research_agent.py --pretty run --submission-mode manual --interactive-approval
```

### Show current leaderboard

```powershell
python .\alpha_research_agent.py --pretty leaderboard --limit 10
```

### Run baseline-vs-agent evaluation

```powershell
python .\alpha_research_agent.py --pretty evaluate --cases .\docs\eval_cases.json
```

Output defaults to:

- `<workdir>/evaluation/report.json`

### Run Streamlit app

```powershell
streamlit run .\streamlit_app.py
```

The app provides:

- auth + planner config
- run controls (budget/iterations/families)
- quant controls (family budget share, novelty threshold, robustness gates)
- submission safety mode controls
- action timeline + stage history + hypothesis log + raw JSON report

## Basic Tests

```powershell
python -m unittest tests\test_planner.py tests\test_research_logic.py
```

## Reproducibility Artifacts

In agent workdir (`.alpha_agent` by default):

- `results.jsonl`: evaluated candidate records
- `submissions.jsonl`: submit attempts
- `state.json`: rolling summary
- `agent_runs/*.json`: full per-run reports with planner decisions and event logs
- `evaluation/report.json`: baseline-vs-agent comparison report

## Legacy Baseline Commands

Baseline scripts remain available:

```powershell
python .\alpha_research_pipeline.py --pretty search --budget 24 --seed-fraction 0.7
python .\alpha_research_pipeline.py --pretty leaderboard --limit 10
python .\alpha_research_pipeline.py --pretty submit-best
```

## Safety Notes

- Never commit credentials, cookies, keys, or private account data.
- Use `.env` and ignored local files for secrets.
- Keep `submission_mode=disabled` for research unless you intentionally enable stronger modes.
- Prefer manual approval for live demos and classroom evaluation.

## Disclaimer

Use responsibly and only with authorized credentials and permissions. Platform behavior and available endpoints may change over time.

## License

[MIT](LICENSE)

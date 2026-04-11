# WorldQuant BRAIN Alpha Research Pipeline

A Python toolkit for researching, simulating, checking, and attempting submission of WorldQuant BRAIN alphas through the same production API flow used by the official frontend.

This repository contains two layers:

- `worldquant_brain_cli.py`: a low-level stdlib-only CLI for authentication, simulation, alpha inspection, checks, and submission.
- `alpha_research_pipeline.py`: a higher-level research pipeline for seed generation, batch evaluation, leaderboard tracking, refinement, and controlled auto-submit attempts.

The code in this repo is designed for repeatable alpha research rather than one-off manual experimentation. The main goal is to shorten the loop from:

1. idea formation
2. expression design
3. parameter search
4. check analysis
5. local refinement
6. submit attempt

## Highlights

- Uses only Python standard library.
- Supports password login or reuse of an existing browser cookie.
- Handles async simulation and async submit polling with `Retry-After`.
- Stores research runs as JSONL for auditability and resumability.
- Separates seed search from refinement search.
- Deduplicates candidates by normalized `expression + settings`.
- Includes a curated idea library with social, news, price reversion, and combo seeds.
- Keeps secrets out of source control via environment-variable based configuration.

## Repository Layout

- `worldquant_brain_cli.py`: raw API client and CLI.
- `alpha_research_pipeline.py`: batch research engine.
- `alpha_pipeline_ideas.json`: manually curated seeds and family templates.
- `wqb_data_fields_summary.json`: cached field-id snapshot used for candidate filtering.
- `docs/API_RESEARCH.md`: endpoint and frontend reverse-engineering notes.
- `docs/PIPELINE.md`: architecture and extension guide.
- `docs/RESULTS_SUMMARY.md`: live-search findings and current best candidates.
- `SECURITY.md`: credential handling and publishing guidance.

## Safety First

This repo intentionally does not include:

- account email addresses
- passwords
- cookies
- local run outputs
- local submission logs
- downloaded frontend bundles

Before publishing, make sure you only configure secrets through environment variables or a local `.env` file that is ignored by git.

## Requirements

- Python 3.10+
- A WorldQuant BRAIN account with API-capable access

## Quick Start

Clone the repo, then set environment variables locally.

```powershell
$env:WQB_EMAIL="your_email@example.com"
$env:WQB_PASSWORD="your_password"
```

Or provide a live browser session cookie instead:

```powershell
$env:WQB_COOKIE_HEADER="sessionid=...; csrftoken=..."
```

Inspect account-visible simulation options:

```powershell
python .\worldquant_brain_cli.py --pretty options
```

Inspect the operator catalog and data-field summary:

```powershell
python .\worldquant_brain_cli.py --pretty operators
python .\worldquant_brain_cli.py --pretty data-fields > wqb_data_fields_summary.json
```

Run a single simulation:

```powershell
python .\worldquant_brain_cli.py --pretty simulate --expression "rank(ts_delta(close, 5))"
```

Check an existing alpha:

```powershell
python .\worldquant_brain_cli.py --pretty check --alpha-id ABC123
```

Attempt submit on an existing alpha:

```powershell
python .\worldquant_brain_cli.py --pretty submit --alpha-id ABC123
```

## Research Pipeline Workflow

Run a seed-heavy search:

```powershell
python .\alpha_research_pipeline.py --pretty search --budget 24 --seed-fraction 0.7
```

Focus on one family:

```powershell
python .\alpha_research_pipeline.py --pretty search --family social_buzz --budget 16
```

Resume and refine the current frontier:

```powershell
python .\alpha_research_pipeline.py --pretty search --family social_buzz --budget 12 --seed-fraction 0.1 --refine-top-k 12
```

Show the current leaderboard:

```powershell
python .\alpha_research_pipeline.py --pretty leaderboard --limit 10
```

Try to submit the best stored candidate that already clears blocking checks:

```powershell
python .\alpha_research_pipeline.py --pretty submit-best
```

## How the Pipeline Thinks

The pipeline is intentionally opinionated:

- Manual seeds get evaluated first because they encode domain knowledge.
- Generated seeds come from reusable family templates in `alpha_pipeline_ideas.json`.
- Results are ranked with a score that rewards Sharpe, Fitness, Returns, Margin, and passing checks.
- Refinement mutations focus on the highest-leverage knobs:
  - `decay`
  - `neutralization`
  - `universe`
  - `truncation`
  - template windows
- If a family reaches the stage where basic quality checks pass but correlation checks fail, the pipeline treats that as a direction-level signal to diversify rather than endlessly over-refine the same family.
- Auto-submit is conservative and only triggers when the candidate clears the blocking research checks already visible from the API.

## Research State Persistence

By default the pipeline writes to `.alpha_pipeline/`:

- `results.jsonl`: one record per evaluated candidate
- `submissions.jsonl`: one record per submit attempt
- `state.json`: latest aggregate state

You can isolate experiments by changing `--workdir`.

## Current Research Findings

The strongest discovered candidates are no longer failing on basic quality metrics. The search has already progressed into the harder stage where:

- Sharpe is above the platform threshold
- Fitness is at or above the threshold
- turnover is inside limits
- weight concentration is under control
- self-correlation is close to or below the threshold

The remaining bottleneck for the strongest combo candidates is usually `PROD_CORRELATION`, not raw alpha quality. See [docs/RESULTS_SUMMARY.md](docs/RESULTS_SUMMARY.md) for the current frontier.

That is also why the pipeline now pivots away from correlation-blocked families and redistributes budget into more orthogonal families such as news, sentiment, fundamentals, and structurally different price combinations.

## Extending the Idea Library

`alpha_pipeline_ideas.json` supports two entry points:

- `manual_seeds`: hand-picked candidates that should always be tried early
- `families`: templated search spaces over fields, windows, signs, and settings grids

This makes it easy to add new research families without changing pipeline code.

## Reverse-Engineering Notes

The implementation is based on live observations from official WorldQuant-owned properties and the production frontend bundle, not an official standalone public API specification.

See:

- [docs/API_RESEARCH.md](docs/API_RESEARCH.md)
- [SECURITY.md](SECURITY.md)

## Disclaimer

Use this repository responsibly and only with credentials and permissions you are authorized to use. Platform behavior, available endpoints, and account capabilities may change over time.

## License

[MIT](LICENSE)

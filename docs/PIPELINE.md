# Pipeline Architecture

This document explains how `alpha_research_pipeline.py` turns a manual research process into a resumable search loop.

## Design Goals

- Preserve a fast inner loop for idea testing
- Keep every evaluated candidate inspectable after the fact
- Avoid re-running the same expression/settings pair
- Separate low-level API logic from high-level research strategy
- Make extension cheap through JSON configuration rather than code edits

## Layers

### API Layer

Implemented in `worldquant_brain_cli.py`.

Responsibilities:

- authentication
- raw request handling
- async simulation polling
- check retrieval
- submit polling
- basic CLI access to platform metadata

### Research Layer

Implemented in `alpha_research_pipeline.py`.

Responsibilities:

- candidate generation
- deduplication
- result persistence
- ranking
- refinement
- optional auto-submit

## Candidate Model

Each candidate has:

- `expression`
- normalized `settings`
- `family`
- `idea_name`
- `stage`
- `priority`
- `parent_key`
- free-form `metadata`

Two identifiers matter:

- `candidate_signature`: hash of normalized `expression + settings`
- `candidate_key`: currently aligned with the same signature

The signature is used for deduplication so that semantically identical candidates are not reevaluated just because they were discovered through different routes.

## Idea Library Structure

The JSON idea library has two sections.

### `default_settings`

Optional top-level settings applied to every manual seed unless that seed overrides them.
This is useful for large curated libraries such as `alpha101_ideas.json`, where all seeds should share the same region, universe, delay, decay, neutralization, truncation, and language settings.

### `manual_seeds`

Used for:

- curated high-conviction ideas
- hand-discovered frontier candidates
- combo expressions worth preserving as first-class starting points

### `families`

Used for templated exploration:

- field lists
- sign choices
- window grids
- template expressions
- settings grids

This makes the search space extensible without touching Python.

## Search Loop

The main `search` command runs in two phases.

### Phase 1: Seed Evaluation

- load manual seeds
- generate templated seeds
- filter by family if requested
- filter unavailable data fields if a local summary exists
- deduplicate by signature
- evaluate a seed slice based on `--budget` and `--seed-fraction`

### Phase 2: Refinement

- build a leaderboard from stored successful results
- take the top `--refine-top-k`
- mutate the highest-leverage settings and windows
- reevaluate only unseen candidates
- if a leading family is blocked only by correlation checks, stop deepening that family and send the leftover budget into more orthogonal seeds

## Refinement Operators

Current refinement focuses on:

- `decay`
- `neutralization`
- `universe`
- `truncation`
- template window shifts

These were chosen because they are both:

- cheap to express
- often impactful on WorldQuant research checks

## Result Storage

Every evaluation is written to JSONL immediately.

### `results.jsonl`

One record per evaluated candidate, including:

- expression
- settings
- alpha id
- metrics
- check summary
- error payload if evaluation failed

### `submissions.jsonl`

One record per submit attempt, including:

- alpha id
- timestamp
- result
- raw submit response or error payload

### `state.json`

Rolling summary:

- result count
- success/error counts
- submittable count
- best candidate key
- best alpha id

## Scoring

The ranking score is heuristic rather than theoretically pure.

It rewards:

- Sharpe
- Fitness
- Returns
- Margin
- passing checks

It penalizes:

- Drawdown
- failed checks
- magnitude of check shortfall where limits and values are available
- production/self correlation failures more heavily than ordinary quality misses

This approach works well for prioritizing the next experiments even when the absolute score has no standalone interpretation.

## Submission Readiness

The pipeline now separates two states that used to be easy to confuse:

- `quality_checks_ready`: the alpha has passed the core quality checks such as Sharpe, fitness, turnover, concentration, and sub-universe Sharpe.
- `precheck_submit_ready`: the alpha has passed both the quality checks and the submission-blocking correlation checks (`SELF_CORRELATION`, `PROD_CORRELATION`), with no pending checks unless explicitly allowed.

This prevents a strong but production-correlated alpha from being ranked as truly submit-ready. Those candidates remain valuable frontier anchors, but they are routed into decorrelation repair instead of submission.

## Why JSONL Instead of a Database

JSONL was chosen because it is:

- simple
- inspectable
- easy to diff
- easy to post-process with Python or shell tools

For this project, transparent records are more valuable than database complexity.

## Extending the Pipeline

Common extension paths:

### Add a new idea family

Edit `alpha_pipeline_ideas.json` and add:

- fields
- windows
- templates
- settings grids

### Add new refinement logic

Edit `build_refinement_candidates()` to add new structural mutations.

### Change ranking behavior

Edit `score_result()` to match your research preferences.

### Change submit policy

Edit the blocking check logic if you want a looser or stricter definition of "submit-ready".

### Change correlation pivot behavior

Edit:

- `should_pivot_away_from_check_payload()`
- `correlation_pivot_families()`
- `prioritize_seed_candidates()`
- `build_diversification_candidates()`

if you want a more or less aggressive strategy for switching directions after self/prod correlation failures.

## Current Limitation

The pipeline is strongest at:

- generating candidates
- evaluating candidates
- managing the frontier

It is weaker at:

- automatically inventing novel decorrelation transforms against unseen production inventory

The agent now includes a dedicated decorrelation repair queue for that final step. It mutates neutralization, truncation, decay, expression wrappers, and two-leg combo weights around quality-ready but correlation-blocked candidates. Curated manual seeds still matter because production correlation is account- and inventory-dependent.

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

This approach works well for prioritizing the next experiments even when the absolute score has no standalone interpretation.

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

## Current Limitation

The pipeline is strongest at:

- generating candidates
- evaluating candidates
- managing the frontier

It is weaker at:

- automatically inventing novel decorrelation transforms against unseen production inventory

That final step still benefits from human-guided hypothesis updates, which is why curated manual seeds remain an important part of the system.

# Live Search Summary

This document summarizes the strongest candidates discovered during live account testing while building the repository.

## Search Progression

The search moved through three stages.

### Stage 1: Single-Signal Discovery

The strongest single-family signal came from social buzz style features:

```text
-ts_mean(scl12_buzz, 5)
```

This family consistently produced good Sharpe but initially failed on:

- `LOW_FITNESS`
- `CONCENTRATED_WEIGHT`

### Stage 2: Parameter Repair

Adjusting:

- `truncation`
- `neutralization`
- moving-average windows

improved the frontier substantially. In particular, increasing truncation to `0.1` improved raw quality metrics, though not enough to clear all checks by itself.

### Stage 3: Two-Factor Combos

Adding a price-reversion leg changed the problem shape:

- quality checks began to pass
- concentration improved
- the remaining blockers shifted from raw quality to correlation checks

## Strongest Frontier Candidate

The strongest candidate discovered during live testing was:

```text
ts_mean(-scl12_buzz, 9) + rank((ts_mean(close, 26) - close) / close)
```

Tested with:

```text
region=USA
universe=TOP3000
delay=1
decay=0
neutralization=SECTOR
truncation=0.08
nanHandling=OFF
```

Observed checks:

- `LOW_SHARPE`: pass
- `LOW_FITNESS`: pass
- `LOW_TURNOVER`: pass
- `HIGH_TURNOVER`: pass
- `CONCENTRATED_WEIGHT`: pass
- `LOW_SUB_UNIVERSE_SHARPE`: pass
- `SELF_CORRELATION`: pass
- `PROD_CORRELATION`: fail

Representative metrics:

- Sharpe: `1.40`
- Fitness: `1.00`
- Turnover: `0.2529`
- Self correlation: `0.6991`
- Prod correlation: `0.8967`

## What This Means

The pipeline is no longer blocked by basic factor quality. It has already reached the harder frontier where:

- the alpha is statistically viable
- the alpha is internally coherent
- the alpha still resembles something already present in production inventory

That is an important milestone because it changes the next optimization target.

## Practical Research Conclusion

The next best use of search budget is not "make Sharpe bigger".

The next best use of search budget is:

- decorrelate from production
- preserve the quality metrics already achieved
- continue from the `social_price_combo` family rather than restarting from weaker seeds

## Recommended Next Search Directions

1. Keep the `social_price_combo` family as a first-class seed family.
2. Search small structural perturbations around the current best combo rather than broad random sweeps.
3. Prefer second-leg variants that change correlation more than they change base alpha quality.
4. Track `PROD_CORRELATION` as the dominant objective once the traditional research checks are already passing.

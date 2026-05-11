# Alpha101 Replication Library

`alpha101_ideas.json` adds all 101 seed expressions from Zura Kakushadze's "101 Formulaic Alphas" paper as a BRAIN-ready idea library.

Source:

- Paper: <https://arxiv.org/abs/1601.00991>
- PDF: <https://arxiv.org/pdf/1601.00991>

## How To Run

CLI:

```powershell
python .\alpha_research_agent.py --pretty --idea-library .\alpha101_ideas.json run --family alpha101 --budget 24 --max-iterations 8
```

Streamlit:

1. Start the app with `python -m streamlit run .\streamlit_app.py`.
2. In the sidebar, choose `Alpha101 replication` under `Idea library preset`.
3. Keep `Submission mode` disabled while screening.
4. Start with a small budget, then increase after syntax and API behavior look clean.

## Translation Policy

The paper's operator names are translated to FASTEXPR-style names used by the rest of this project:

- `delay` -> `ts_delay`
- `delta` -> `ts_delta`
- `sum` -> `ts_sum`
- `product` -> `ts_product`
- `stddev` -> `ts_std_dev`
- `correlation` -> `ts_corr`
- `covariance` -> `ts_covariance`
- `decay_linear` -> `ts_decay_linear`
- `signedpower` -> `signed_power`
- `indneutralize(x, IndClass.level)` -> `group_neutralize(x, level)`

The paper defines fractional time windows as floored integers. The library stores integer windows directly because BRAIN operators require integer lookbacks.

The local field cache only has `adv20`. For Alpha101 formulas that reference other `advN` inputs, the library uses `ts_mean(volume, N)` as a liquidity proxy. This keeps all 101 seeds runnable against the fields currently in the project, but those formulas are compatibility replicas rather than byte-for-byte paper replicas.

## Defaults

The file uses a top-level `default_settings` block:

- `region`: `USA`
- `universe`: `TOP3000`
- `delay`: `1`
- `decay`: `0`
- `neutralization`: `INDUSTRY`
- `truncation`: `0.08`

These defaults are chosen for research screening on BRAIN. Adjust the top-level settings once if you want to test a different universe or neutralization policy across the entire Alpha101 set.

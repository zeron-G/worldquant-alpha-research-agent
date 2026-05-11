# Presentation Frontend Guide

The Streamlit app is designed as an English presentation console for the alpha research agent. It can run without credentials by loading a built-in showcase case, then optionally switch into live WorldQuant BRAIN execution when credentials are available.

## Launch

```powershell
python -m streamlit run .\streamlit_app.py
```

Open the local URL printed by Streamlit, usually:

```text
http://localhost:8501
```

## Recommended Pre Flow

1. Start with the built-in showcase case.
2. Use `Overview` to show the final stage, best score, readiness funnel, and convergence curve.
3. Use `Agent Trace` to explain how the planner moves from exploration to correlation repair and robustness testing.
4. Use `Economic Logic` to show the constrained optimization derivation and adjust cost assumptions live.
5. Use `Architecture` to show the system design and all hot-modifiable parameters.
6. Keep live submission mode as `disabled` during the presentation unless a manual approval demonstration is intentional.

## Hot-Modifiable Controls

The sidebar exposes the parameters that can be changed without editing code:

- connection: email, password, cookie header, API base URL, request timeout
- LLM planner: provider, model, temperature, base URL, API key environment variable, planner timeout
- search space: idea library, fields summary, family filters
- loop budget: budget, max iterations, seed fraction, refine top K, robustness top K, robustness threshold
- research policy: shuffle seeds, random seed, family budget share, minimum expression novelty
- reliability: retries, sleep between candidates, max wait, poll interval
- governance: pending checks, submission mode, manual approval
- artifacts: workdir, latest report loading, explicit report JSON path

## Demo vs Live Mode

Use `Load Showcase Case` for a deterministic, presentation-safe run. It demonstrates:

- a baseline frontier blocked by production correlation
- correlation-aware repair candidates
- robustness validation before harvest
- separation of `quality ready`, `correlation blocked`, and `submit-ready`
- zero live submission attempts

Use `Run Live Agent` only after configuring credentials or a cookie header. Live runs write JSON artifacts to the selected workdir.

## Economic Logic Section

The `Economic Logic` tab frames alpha discovery as a constrained expected utility problem:

```text
max E[U(x)] = p(x)V - C_sim n(x) - C_time t(x) - lambda*rho(x) - kappa*tau(x)
```

It connects the agent design to research economics:

- budget is scarce, so each simulation has opportunity cost
- raw alpha quality is not enough if production correlation blocks submission
- turnover and concentration are economic frictions
- the agent should continue search only while marginal value of budget is positive

## Presentation Safety

The frontend is intentionally safe by default:

- it starts in demo mode
- submission mode defaults to `disabled`
- correlation-failed candidates are repair targets, not submit-ready candidates
- raw artifacts are inspectable before any live action

# API Research Notes

Verified against official WorldQuant-owned properties and the live production frontend on April 7-10, 2026.

## Primary Sources

- Official consultant page: `https://worldquantbrain.com/consultant`
- Production frontend bundle: `https://platform.worldquantbrain.com/static/js/1578.8f1c1c8c.js`
- Platform app shell: `https://platform.worldquantbrain.com/`

## Important Framing

WorldQuant BRAIN does not expose a widely documented public API reference for every endpoint and schema used by the frontend. The client in this repository therefore mixes:

- direct live verification
- official frontend inspection
- conservative implementation choices

Whenever behavior is inferred rather than explicitly documented, the code prefers simple request patterns, explicit polling, and transparent error propagation.

## Verified Endpoint Flow

### 1. Authentication

- Endpoint: `POST /authentication`
- Observed auth mechanism: `Authorization: Basic base64(email:password)`
- Session handling: cookie-backed
- Important caveat: the frontend also contains reCAPTCHA handling, so password-only automation may fail on challenged accounts

### 2. Simulation

- Metadata endpoint: `OPTIONS /simulations`
- Start simulation: `POST /simulations`
- Result flow:
  - response may include `Location`
  - response may include `Retry-After`
  - polling continues until a terminal payload is available

### 3. Alpha Inspection

- Alpha detail: `GET /alphas/{id}`
- Submission checks: `GET /alphas/{id}/check`

### 4. Submission

- Submit request: `POST /alphas/{id}/submit`
- If async: poll `GET /alphas/{id}/submit`

Important: the frontend also references `/submissions`, but that is not the same flow as the main alpha submission button used after a normal simulation.

## Header Versioning Observed in Frontend

- General JSON calls: `Accept: application/json;version=2.0`
- `OPTIONS /simulations`: `Accept: application/json;version=3.0`

This repository follows that behavior.

## Regular Simulation Payload

Observed payload shape:

```json
{
  "type": "REGULAR",
  "settings": {
    "instrumentType": "EQUITY",
    "region": "USA",
    "universe": "TOP3000",
    "delay": 1,
    "decay": 4,
    "neutralization": "SECTOR",
    "truncation": 0.08,
    "pasteurization": "ON",
    "unitHandling": "VERIFY",
    "nanHandling": "ON",
    "language": "FASTEXPR",
    "visualization": false
  },
  "regular": "rank(ts_delta(close, 5))"
}
```

## Response Detail That Matters in Practice

Two details are especially important for robust automation:

### Simulation payloads are async

The immediate simulation response is not the final alpha detail. The implementation must honor:

- `Location`
- `Retry-After`
- follow-up polling

### Final simulation payload can expose the alpha id in different shapes

In live testing, `simulation["alpha"]` may be:

- a string alpha id
- a nested alpha object

The repo client handles both.

## Endpoints Used by This Repo

The CLI and pipeline use:

- `POST /authentication`
- `OPTIONS /simulations`
- `POST /simulations`
- `GET /alphas/{id}`
- `GET /alphas/{id}/check`
- `POST /alphas/{id}/submit`
- `GET /alphas/{id}/submit`
- `GET /operators`
- `GET /data-fields/summary`

## Live Research Observations

The following behaviors were confirmed live while building the pipeline:

- quality blockers often move in stages:
  - early stage: `LOW_SHARPE`, `LOW_FITNESS`, `CONCENTRATED_WEIGHT`
  - later stage: `SELF_CORRELATION`
  - final stage: `PROD_CORRELATION`
- some expressions that look distinct are still highly correlated with existing production or self history
- small parameter changes can move correlation checks more than quality checks

## Caveats

- Endpoint behavior can change without notice.
- Account-specific permissions may limit available settings, data fields, or automation feasibility.
- reCAPTCHA can break headless password login.
- Passing visible research checks is not the same as guaranteed submittability if correlation checks later resolve to failure.

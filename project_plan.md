# Project Plan: WorldQuant Alpha Research Agent

Repository: [https://github.com/zeron-G/worldquant-alpha-research-agent](https://github.com/zeron-G/worldquant-alpha-research-agent)  
Previous repository name: `worldquant-brain-alpha-research-pipeline`  
Current repository name: `worldquant-alpha-research-agent`

## 1. Project title

**WorldQuant Alpha Research Agent: A Controlled GenAI Copilot for Alpha Discovery, Evaluation, and Submission Readiness**

## 2. Target user, workflow, and business value

- **Target user**: Individual quant researcher (or small quant team member) using WorldQuant BRAIN.
- **Recurring workflow improved**: Repeated alpha research loop from hypothesis to simulation, checks, refinement, and final submit/no-submit decision.
- **Workflow boundaries**:
  - **Start**: User provides research objective (family focus, budget, universe preference, risk constraints).
  - **End**: System returns ranked submit-ready candidates plus rationale, and optionally prepares a submission action requiring explicit human approval.
- **Business value**:
  - Reduces repetitive manual iteration time.
  - Increases consistency of candidate screening under fixed resource budgets.
  - Improves researcher productivity by prioritizing promising, check-compliant candidates.

## 3. Problem statement and GenAI fit

This system will automatically run a constrained alpha research cycle by planning candidate generation/refinement steps, calling simulation/check tools, and producing ranked recommendations with transparent reasoning for each next action.

GenAI is a good fit because mutation/refinement decisions depend on interpreting semi-structured check feedback, balancing multiple metrics, and adapting strategy across iterations; static rules alone are often brittle when failure patterns shift. A simpler non-GenAI script can brute-force or rule-search, but it cannot flexibly reason over changing diagnostics and trade-offs with the same efficiency.

## 4. Planned system design and baseline

### Planned architecture/workflow

1. User configures a run in a Streamlit app (`objective`, `family`, `budget`, `max iterations`, `submit mode`).
2. An LLM planner proposes a bounded next-action plan in structured JSON.
3. Tool layer executes allowed actions by wrapping existing pipeline capabilities:
   - simulate alpha
   - fetch check details
   - inspect candidate stats/leaderboard
   - optional submit attempt (human-confirmed only)
4. Agent loop (`plan -> execute -> observe -> reflect`) repeats until budget exhaustion or stop condition.
5. App shows ranked candidates, failure reasons, and a recommended next step.
6. All actions are logged for auditability and replay evaluation.

### Two course concepts integrated (minimum requirement)

- **Tool use / function calling (Week 4)**:  
  The planner will output a constrained action schema (for example, `simulate`, `check`, `mutate`, `stop`) and call explicit tools with validated arguments instead of free-form code execution.
- **Agent loops (Week 4/5)**:  
  The core control flow will implement iterative `plan-execute-reflect` behavior with bounded steps, allowing the agent to adapt candidate strategy after each simulation/check outcome.

### Additional concept included

- **Evaluation design (Week 6)**:  
  A fixed replay test set and rubric-driven metrics will compare agent performance against a simpler baseline under the same budget constraints.

### Baseline to compare against

The baseline is the existing heuristic/rule-based research pipeline (`alpha_research_pipeline.py`) without LLM planning, using fixed seed/refinement logic and existing score ranking.

### App description (what the user sees and does)

The app provides a single run console where the user chooses research parameters, starts an agent run, watches a live action timeline (tool calls, outcomes, and budget usage), and reviews a final leaderboard of candidates. The user can inspect why each candidate was promoted or rejected, download a run report, and explicitly approve or deny any final submission action.

## 5. Evaluation plan

### Success criteria

- Higher rate of submit-ready candidates per fixed budget.
- Faster time-to-first high-quality candidate.
- Better check pass progression (fewer repeated dead-end refinements).
- Safe behavior: no unauthorized/unsafe submission actions.

### Metrics

- **Quality metrics**: Sharpe, Fitness, Returns, Margin, turnover compliance, concentration compliance.
- **Workflow metrics**: submit-ready candidate rate, iterations to threshold, success per API-call budget.
- **Efficiency metrics**: wall-clock latency, number of tool calls, approximate token/API cost.
- **Safety metrics**: refusal correctness, policy-violation attempts blocked, human-approval gate compliance.

### Test set

- A replay set of approximately **30 cases**:
  - 20 historical/synthetic seed scenarios across multiple alpha families.
  - 10 targeted failure-pattern scenarios (correlation block, low fitness, high turnover, invalid expression/operator mismatch).

### Comparison method

- Run agent and baseline on the same case set and same tool-call budget.
- Use fixed random seeds where applicable.
- Report aggregate and per-family results.
- Include qualitative error analysis on at least 10 representative failures.

## 6. Example inputs and failure cases

### Example inputs/use cases (3-5)

1. "Search for low-turnover alphas in `social_buzz` with budget 24 and prioritize Sharpe > 1.25."
2. "Given this check failure report, suggest 3 parameter mutations likely to reduce correlation risk."
3. "Run a balanced search across `news`, `sentiment`, and `fundamentals`, then return top 5 candidates."
4. "Evaluate this manual expression and explain if it is worth refinement or should be dropped."
5. "Find candidates that satisfy fitness and concentration constraints before any submit recommendation."

### Likely failure/edge cases (at least 2)

1. Agent proposes invalid operators/fields not supported by current platform metadata.
2. Agent over-focuses on one family and wastes budget despite repeated correlation blocking.
3. API throttling/timeouts create incomplete observation signals and unstable decisions.
4. Authentication/session expiration interrupts long runs mid-loop.

## 7. Risks and governance

### Where the system can fail

- Incorrect interpretation of check diagnostics leading to poor mutation choices.
- Cost overrun if loops are not tightly bounded.
- False confidence in "almost pass" candidates.

### Where it should not be trusted

- It should **not** be trusted for fully autonomous unattended submission in production.
- It should **not** be treated as guaranteed alpha discovery.

### Controls and boundaries

- Human-in-the-loop gate for all submission actions (mandatory explicit confirmation).
- Action limits per run (max iterations, max tool calls, max spend/time budget).
- Strict tool allowlist and argument validation.
- Full run logging for audit/replay.
- Refusal rules when credentials are missing, checks are inconclusive, or risk thresholds are violated.

### Data, privacy, and cost concerns

- No credentials, cookies, or private account data committed to git.
- Use environment variables and ignored local config files for secrets.
- Track cost per run; enforce hard stop on budget/time limits.

## 8. Plan for the Week 6 check-in

By Week 6, the project will include:

- **Running app component**: Streamlit prototype that can run a bounded agent loop (`plan -> simulate/check -> reflect`) and display action logs + ranked outputs.
- **Evaluation in place**: First-pass test harness with at least 12 replay cases and core metrics (quality + efficiency + safety).
- **Baseline comparison available**: Initial side-by-side results against the existing heuristic pipeline on the same subset, including pass-rate and latency/cost differences.

## 9. (Optional) Pair request

Not requesting a pair at this stage. Scope is intentionally constrained for an individual project.

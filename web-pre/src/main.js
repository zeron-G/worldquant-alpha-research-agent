import "./styles.css";

const REPOSITORY_URL = "https://github.com/zeron-G/worldquant-alpha-research-agent";
const PERSONAL_URL = "https://rongzegao.com";

const result = {
  run_id: "alpha_service_showcase_2026",
  started_at: "2026-05-10T14:00:00-0400",
  finished_at: "2026-05-10T14:06:18-0400",
  report_path: "built-in service showcase",
  summary: {
    run_id: "alpha_service_showcase_2026",
    started_at: "2026-05-10T14:00:00-0400",
    finished_at: "2026-05-10T14:06:18-0400",
    budget: 24,
    evaluated_count: 47,
    evaluated_this_run: 21,
    seed_evaluated_this_run: 12,
    submission_attempts_this_run: 0,
    best_score: 1288.4,
    best_alpha_id: "A-DEMO-7421",
    quality_ready_count: 7,
    correlation_blocked_count: 4,
    submittable_count: 2,
    iterations_executed: 5,
    stop_reason: "Service showcase completed with submission mode disabled.",
    submission_mode: "disabled",
    final_stage: "harvest",
    stage_history: [
      { iteration: 1, stage: "explore", reason: "Early run prioritizes broad exploration." },
      { iteration: 3, stage: "exploit", reason: "Quality frontier is blocked by production correlation." },
      { iteration: 4, stage: "robustness", reason: "Submit-ready frontier found; collect robustness evidence." },
      { iteration: 5, stage: "harvest", reason: "Submit-ready alpha exists with robustness checks completed." },
    ],
    family_stats: [
      {
        family: "social_price_repair",
        attempts: 9,
        ok_count: 9,
        submittable_count: 2,
        best_score: 1288.4,
        avg_score: 721.2,
        ok_rate: 1.0,
        corr_fail_rate: 0.22,
        run_count: 9,
        family_cap_reached: false,
      },
      {
        family: "social_price_combo",
        attempts: 7,
        ok_count: 7,
        submittable_count: 0,
        best_score: 846.1,
        avg_score: 544.7,
        ok_rate: 1.0,
        corr_fail_rate: 0.57,
        run_count: 7,
        family_cap_reached: false,
      },
      {
        family: "news_price_combo",
        attempts: 5,
        ok_count: 5,
        submittable_count: 0,
        best_score: 612.7,
        avg_score: 390.4,
        ok_rate: 1.0,
        corr_fail_rate: 0.0,
        run_count: 5,
        family_cap_reached: false,
      },
    ],
    failed_check_histogram: [
      { check: "PROD_CORRELATION", count: 4 },
      { check: "LOW_FITNESS", count: 3 },
      { check: "CONCENTRATED_WEIGHT", count: 2 },
      { check: "LOW_SUB_UNIVERSE_SHARPE", count: 1 },
    ],
    hypothesis_log_tail: [
      {
        iteration: 3,
        stage: "exploit",
        action: "evaluate_refine",
        hypothesis: "Group ranking and neutralization can reduce production correlation.",
        rationale: "Target the dominant failure check instead of blind local search.",
        focus_family: "social_price_combo",
        risk_note: "Do not submit correlation-failed candidates.",
      },
      {
        iteration: 4,
        stage: "robustness",
        action: "evaluate_robustness",
        hypothesis: "Strong candidates should survive universe and neutralization perturbations.",
        rationale: "Validate stability before harvest.",
        focus_family: "social_price_repair",
        risk_note: "Stress tests can reveal fragile alphas.",
      },
    ],
  },
  leaderboard: [
    {
      alpha_id: "A-DEMO-7421",
      family: "social_price_repair",
      idea_name: "repair_social_group_rank_close36_industry.corr_neutral_subindustry",
      stage: "repair_correlation_neutralization",
      expression: "ts_mean(-scl12_buzz, 9) + group_rank((ts_mean(close, 36) - close) / close, industry)",
      settings: {
        region: "USA",
        universe: "TOP3000",
        delay: 1,
        decay: 2,
        neutralization: "SUBINDUSTRY",
        truncation: 0.08,
      },
      score: 1288.4,
      metrics: {
        sharpe: 1.58,
        fitness: 1.13,
        turnover: 0.218,
        returns: 0.074,
        drawdown: 0.032,
        margin: 0.00093,
      },
      failed_checks: [],
      failed_blocking_checks: [],
      failed_correlation_checks: [],
      failed_submission_checks: [],
      quality_checks_ready: true,
      precheck_submit_ready: true,
      summary: { passed: 9, failed: [], pending: [], warning: [], total: 9 },
    },
    {
      alpha_id: "A-DEMO-6118",
      family: "social_price_combo",
      idea_name: "combo_social9_close26_sector_t008",
      stage: "manual_seed",
      expression: "ts_mean(-scl12_buzz, 9) + rank((ts_mean(close, 26) - close) / close)",
      settings: {
        region: "USA",
        universe: "TOP3000",
        delay: 1,
        decay: 0,
        neutralization: "SECTOR",
        truncation: 0.08,
      },
      score: 846.1,
      metrics: {
        sharpe: 1.4,
        fitness: 1.0,
        turnover: 0.253,
        returns: 0.065,
        drawdown: 0.038,
        margin: 0.00076,
      },
      failed_checks: ["PROD_CORRELATION"],
      failed_blocking_checks: [],
      failed_correlation_checks: ["PROD_CORRELATION"],
      failed_submission_checks: ["PROD_CORRELATION"],
      quality_checks_ready: true,
      precheck_submit_ready: false,
      summary: { passed: 8, failed: ["PROD_CORRELATION"], pending: [], warning: [], total: 9 },
    },
    {
      alpha_id: "A-DEMO-5904",
      family: "news_price_combo",
      idea_name: "news_plus_vwap.sentiment_score.w20",
      stage: "generated_seed",
      expression: "ts_mean(news_sentiment_score, 20) + rank((ts_mean(vwap, 20) - close) / close)",
      settings: {
        region: "USA",
        universe: "TOP3000",
        delay: 1,
        decay: 4,
        neutralization: "INDUSTRY",
        truncation: 0.05,
      },
      score: 612.7,
      metrics: {
        sharpe: 1.19,
        fitness: 0.82,
        turnover: 0.341,
        returns: 0.052,
        drawdown: 0.045,
        margin: 0.00061,
      },
      failed_checks: ["LOW_FITNESS"],
      failed_blocking_checks: ["LOW_FITNESS"],
      failed_correlation_checks: [],
      failed_submission_checks: ["LOW_FITNESS"],
      quality_checks_ready: false,
      precheck_submit_ready: false,
      summary: { passed: 7, failed: ["LOW_FITNESS"], pending: [], warning: [], total: 8 },
    },
  ],
  events: [
    {
      iteration: 1,
      stage: "explore",
      action: "evaluate_seed",
      rationale: "Explore broad families before overfitting to early winners.",
      hypothesis: "Diverse seeds improve the probability of finding an orthogonal signal.",
      risk_note: "Preserve budget across families.",
      details: {
        executed_batch: 6,
        ok_count: 6,
        quality_ready_count: 1,
        correlation_blocked_count: 0,
        submittable_count: 0,
        best_score_after: 402.8,
      },
    },
    {
      iteration: 2,
      stage: "explore",
      action: "evaluate_seed",
      rationale: "Continue sampling social, news, and price-reversion families.",
      hypothesis: "Manual social-price seeds may dominate single-signal templates.",
      risk_note: "Watch concentration and production correlation.",
      details: {
        executed_batch: 6,
        ok_count: 6,
        quality_ready_count: 2,
        correlation_blocked_count: 1,
        submittable_count: 0,
        best_score_after: 846.1,
      },
    },
    {
      iteration: 3,
      stage: "exploit",
      action: "evaluate_refine",
      rationale: "Quality frontier is correlation-blocked; run decorrelation repairs before robustness harvest.",
      hypothesis: "Group ranking and neutralization can lower production correlation while preserving signal quality.",
      risk_note: "Do not mark correlation-failed candidates as submission-ready.",
      details: {
        executed_batch: 5,
        ok_count: 5,
        quality_ready_count: 4,
        correlation_blocked_count: 2,
        submittable_count: 1,
        best_score_after: 1182.6,
      },
    },
    {
      iteration: 4,
      stage: "robustness",
      action: "evaluate_robustness",
      rationale: "Stress-test the submit-ready frontier across settings perturbations.",
      hypothesis: "A durable candidate should remain viable under universe and neutralization changes.",
      risk_note: "Robustness tests consume budget but reduce false confidence.",
      details: {
        executed_batch: 4,
        ok_count: 4,
        quality_ready_count: 3,
        correlation_blocked_count: 1,
        submittable_count: 2,
        best_score_after: 1288.4,
      },
    },
    {
      iteration: 5,
      stage: "harvest",
      action: "stop",
      rationale: "Service mode stops before any live submission.",
      hypothesis: "The agent has produced a ranked, auditable submit-ready frontier.",
      risk_note: "Submission mode remains disabled for classroom demonstration.",
      details: {
        executed_batch: 0,
        ok_count: 0,
        quality_ready_count: 7,
        correlation_blocked_count: 4,
        submittable_count: 2,
        best_score_after: 1288.4,
      },
    },
  ],
  submissions: [],
  state: {
    result_count: 47,
    ok_count: 44,
    error_count: 3,
    quality_ready_count: 7,
    correlation_blocked_count: 4,
    submittable_count: 2,
    best_alpha_id: "A-DEMO-7421",
    best_score: 1288.4,
  },
  service: {
    source: "Built-in service case",
    score_curve: [
      { iteration: 1, best_score: 402.8, submittable: 0, quality_ready: 1 },
      { iteration: 2, best_score: 846.1, submittable: 0, quality_ready: 2 },
      { iteration: 3, best_score: 1182.6, submittable: 1, quality_ready: 4 },
      { iteration: 4, best_score: 1288.4, submittable: 2, quality_ready: 7 },
      { iteration: 5, best_score: 1288.4, submittable: 2, quality_ready: 7 },
    ],
    baseline: {
      evaluated: 21,
      best_score: 846.1,
      quality_ready: 2,
      submittable: 0,
      corr_blocked: 3,
    },
    agent: {
      evaluated: 21,
      best_score: 1288.4,
      quality_ready: 7,
      submittable: 2,
      corr_blocked: 4,
    },
  },
};

const runtimePreview = {
  planner: "heuristic:gpt5.5",
  temperature: 0.1,
  budget: 24,
  iterations: 12,
  seed_fraction: 0.7,
  refine_top_k: 8,
  robustness_top_k: 3,
  robustness_threshold: 500,
  families: "all",
  shuffle_seeds: true,
  random_seed: 7,
  family_budget_share: 0.45,
  expression_novelty: 0.1,
  retries: 2,
  sleep_between: 1,
  max_wait: 1800,
  poll_interval: 3,
  submission_mode: "disabled",
  allow_pending: false,
  workdir: ".alpha_agent",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmt(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "-";
  const number = Number(value);
  if (!Number.isFinite(number)) return String(value);
  if (Math.abs(number - Math.round(number)) < 1e-9) {
    return Math.round(number).toLocaleString("en-US");
  }
  return number.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function pct(value) {
  return `${Math.max(0, Math.min(1, value)) * 100}%`;
}

function sectionHeader(title, subtitle = "") {
  return `<div class="section-title"><h2>${escapeHtml(title)}</h2><span>${escapeHtml(subtitle)}</span></div>`;
}

function metricGrid(items) {
  return `<div class="metric-grid">${items
    .map((item) => {
      const statusClass =
        item.status === "good" ? "status-good" : item.status === "warn" ? "status-warn" : item.status === "danger" ? "status-danger" : "";
      return `<div class="metric">
        <div class="metric-label">${escapeHtml(item.label)}</div>
        <div class="metric-value ${statusClass}">${escapeHtml(item.value)}</div>
        <div class="metric-sub">${escapeHtml(item.sub)}</div>
      </div>`;
    })
    .join("")}</div>`;
}

function bars(rows) {
  return rows
    .map(
      ([label, ratio, value]) => `<div class="bar-row">
        <div>${escapeHtml(label)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct(ratio)};"></div></div>
        <div class="mono">${escapeHtml(value)}</div>
      </div>`
    )
    .join("");
}

function lineChart(rows, series, xKey) {
  const width = 920;
  const height = 260;
  const pad = { left: 46, right: 24, top: 18, bottom: 34 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const values = series.flatMap((item) => rows.map((row) => Number(row[item.key]) || 0));
  const min = Math.min(0, ...values);
  const max = Math.max(1, ...values);
  const y = (value) => pad.top + innerH - ((value - min) / Math.max(1, max - min)) * innerH;
  const x = (index) => pad.left + (index / Math.max(1, rows.length - 1)) * innerW;
  const grid = [0, 0.25, 0.5, 0.75, 1]
    .map((ratio) => {
      const gy = pad.top + innerH * ratio;
      const label = fmt(max - (max - min) * ratio, 0);
      return `<line x1="${pad.left}" y1="${gy}" x2="${width - pad.right}" y2="${gy}" class="chart-grid" />
        <text x="8" y="${gy + 4}" class="chart-label">${label}</text>`;
    })
    .join("");
  const paths = series
    .map((item) => {
      const points = rows.map((row, index) => `${x(index).toFixed(1)},${y(Number(row[item.key]) || 0).toFixed(1)}`).join(" ");
      return `<polyline points="${points}" fill="none" stroke="${item.color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round" />`;
    })
    .join("");
  const xLabels = rows
    .map((row, index) => `<text x="${x(index)}" y="${height - 8}" class="chart-label" text-anchor="middle">${escapeHtml(row[xKey])}</text>`)
    .join("");
  const legend = series
    .map(
      (item, index) => `<g transform="translate(${pad.left + index * 155}, 8)">
        <circle cx="0" cy="0" r="4" fill="${item.color}"></circle>
        <text x="10" y="4" class="chart-label">${escapeHtml(item.label)}</text>
      </g>`
    )
    .join("");
  return `<svg class="line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="line chart">
    ${grid}
    ${paths}
    ${xLabels}
    ${legend}
  </svg>`;
}

function stableSeed(text) {
  let hash = 0;
  for (const char of String(text)) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
}

function buildPerformanceSeries(candidate) {
  const metrics = candidate.metrics || {};
  const sharpe = Number(metrics.sharpe) || 1;
  const turnover = Number(metrics.turnover) || 0.2;
  const returns = Number(metrics.returns) || 0.04;
  const scale = 220000 + Math.max(0, Number(candidate.score) || 0) * 120;
  const phase = (stableSeed(candidate.alpha_id || "candidate") % 628) / 100;
  const drift = Math.max(-0.004, Math.min(0.045, returns * 0.35 + sharpe * 0.006));
  const blocked = (candidate.failed_submission_checks || candidate.failed_checks || []).length;
  const rows = [];
  let pnl = 0;
  let current = new Date("2014-01-03T00:00:00Z");
  for (let index = 0; index < 126; index += 1) {
    const cycle = Math.sin(index / 5.7 + phase) * 0.018;
    const local = Math.sin(index * 1.41 + phase * 0.7) * 0.009;
    const stress = blocked && [34, 63, 91].includes(index) ? -0.035 : 0;
    pnl += scale * (drift + cycle + local + stress);
    rows.push({
      date: current.toISOString().slice(0, 10),
      PnL: Math.round(pnl * 100) / 100,
      Sharpe: Math.round((sharpe + Math.sin(index / 9 + phase) * 0.18 - blocked * 0.025) * 1000) / 1000,
      Turnover: Math.round(Math.max(0, turnover + Math.sin(index / 7.5 + phase) * 0.025 + blocked * 0.006) * 10000) / 10000,
    });
    current = new Date(current.getTime() + 28 * 24 * 60 * 60 * 1000);
  }
  return rows;
}

function performanceChart(candidate, metric = "PnL") {
  const rows = buildPerformanceSeries(candidate).filter((_, index) => index % 8 === 0);
  const color = metric === "PnL" ? "#3dd6b3" : metric === "Sharpe" ? "#f4c95d" : "#ff9f6e";
  return lineChart(rows, [{ key: metric, label: metric, color }], "date");
}

function renderSidebar() {
  const input = (label, value, type = "text") => `<label class="side-control"><span>${label}</span><input type="${type}" value="${escapeHtml(value)}" readonly /></label>`;
  const area = (label, value) => `<label class="side-control"><span>${label}</span><textarea readonly>${escapeHtml(value)}</textarea></label>`;
  const select = (label, value) => `<label class="side-control"><span>${label}</span><select><option>${escapeHtml(value)}</option></select></label>`;
  return `<aside data-testid="stSidebar" class="sidebar">
    <h3>Alpha Console</h3>
    <button class="primary-side" type="button">Load Showcase Case</button>
    ${input("Run report JSON path", "")}
    <button type="button">Load Report Path</button>
    <hr />
    <h3>Connection</h3>
    ${input("WQB email", "")}
    ${input("WQB password", "", "password")}
    ${area("WQB cookie header", "")}
    ${input("WQB API base URL", "https://api.worldquantbrain.com")}
    ${input("Request timeout seconds", "30")}
    <h3>LLM Planner</h3>
    ${select("Planner provider", "heuristic")}
    ${input("Planner model", "gpt5.5")}
    ${input("Planner temperature", "0.10")}
    ${input("Planner base URL", "https://api.openai.com/v1")}
    ${input("Planner API key environment variable", "OPENAI_API_KEY")}
    ${input("Planner timeout seconds", "60")}
    <h3>Search Space</h3>
    ${select("Idea library preset", "Core search library")}
    ${input("Idea library", "alpha_pipeline_ideas.json")}
    ${input("Fields summary", "wqb_data_fields_summary.json")}
    ${input("Additional family filter CSV", "")}
    <h3>Budget and Loop</h3>
    ${input("Budget", "24")}
    ${input("Max iterations", "12")}
    ${input("Seed fraction", "0.70")}
    ${input("Refine top K", "8")}
    ${input("Robustness top K", "3")}
    ${input("Robustness score threshold", "500")}
    <h3>Research Policy</h3>
    ${input("Shuffle generated seeds", "true")}
    ${input("Random seed", "7")}
    ${input("Max family budget share", "0.45")}
    ${input("Min expression novelty", "0.10")}
    <h3>Reliability</h3>
    ${input("Retries", "2")}
    ${input("Sleep between candidates", "1.0")}
    ${input("Max wait seconds", "1800")}
    ${input("Poll interval seconds", "3")}
    <h3>Submission Governance</h3>
    ${input("Allow pending checks", "false")}
    ${select("Submission mode", "disabled")}
    ${input("Approve manual submissions during run", "false")}
    <h3>Artifacts</h3>
    ${input("Workdir", ".alpha_agent")}
    <button type="button">Load Latest Workdir Report</button>
    <button type="button">Run Live Agent</button>
  </aside>`;
}

function renderTopLinks() {
  return `<div class="top-links">
    <div class="top-brand">Alpha Research Agent</div>
    <div class="top-nav">
      <a href="${REPOSITORY_URL}" target="_blank" rel="noopener noreferrer">GitHub Repository</a>
      <a href="${PERSONAL_URL}" target="_blank" rel="noopener noreferrer">rongzegao.com</a>
    </div>
  </div>`;
}

function renderHero() {
  const summary = result.summary;
  const strip = [
    ["Run Source", "Built-in service"],
    ["Final Stage", summary.final_stage],
    ["Best Score", fmt(summary.best_score)],
    ["Submit-Ready", fmt(summary.submittable_count)],
  ];
  return `<section class="hero">
    <div class="eyebrow"><span class="pulse-dot"></span>Alpha Console</div>
    <div class="hero-title">Alpha Research Agent</div>
    <div class="hero-copy">A controlled alpha discovery system that plans experiments, diagnoses failed checks, repairs correlation risk, validates robustness, and ranks submission-ready candidates.</div>
    <div class="hero-strip">${strip
      .map(([label, value]) => `<div class="strip-item"><div class="strip-k">${escapeHtml(label)}</div><div class="strip-v">${escapeHtml(value)}</div></div>`)
      .join("")}</div>
  </section>`;
}

function renderStageFlow(summary) {
  const stages = [
    ["explore", "Diversify across families and expression templates."],
    ["exploit", "Target dominant failed checks with local and structural repairs."],
    ["robustness", "Stress-test the frontier under setting perturbations."],
    ["harvest", "Prepare a governed submit/no-submit decision."],
  ];
  return `<div class="stage-flow">${stages
    .map(([name, desc]) => `<div class="stage${name === summary.final_stage ? " active" : ""}">
      <div class="stage-name">${name}</div>
      <div class="stage-desc">${desc}</div>
    </div>`)
    .join("")}</div>`;
}

function renderOverview() {
  const summary = result.summary;
  const evaluated = Math.max(1, Number(summary.evaluated_this_run || summary.evaluated_count || 1));
  const curve = result.service.score_curve;
  return `<section class="section">
    ${sectionHeader("Executive Overview", "live run state")}
    ${metricGrid([
      { label: "Best Score", value: fmt(summary.best_score), sub: summary.best_alpha_id, status: "good" },
      { label: "Evaluated This Run", value: fmt(summary.evaluated_this_run), sub: `budget ${fmt(summary.budget)}` },
      { label: "Quality Ready", value: fmt(summary.quality_ready_count), sub: "core checks passed", status: "good" },
      { label: "Correlation Blocked", value: fmt(summary.correlation_blocked_count), sub: "repair frontier", status: "warn" },
      { label: "Submit-Ready", value: fmt(summary.submittable_count), sub: "all blocking checks clear", status: "good" },
      { label: "Submission Attempts", value: fmt(summary.submission_attempts_this_run), sub: summary.submission_mode },
    ])}
  </section>
  <div class="grid-2">
    <section class="section">
      ${sectionHeader("Agent Stage Machine", "explore -> exploit -> robustness -> harvest")}
      ${renderStageFlow(summary)}
      <div class="tag-strip">${summary.stage_history.map((item) => `<span class="tag">${escapeHtml(item.stage)}</span>`).join("")}</div>
    </section>
    <section class="section">
      ${sectionHeader("Readiness Funnel", "quality, correlation, and submit gates")}
      ${bars([
        ["Evaluated", 1, fmt(evaluated)],
        ["Quality Ready", summary.quality_ready_count / evaluated, fmt(summary.quality_ready_count)],
        ["Corr Blocked", summary.correlation_blocked_count / evaluated, fmt(summary.correlation_blocked_count)],
        ["Submit-Ready", summary.submittable_count / evaluated, fmt(summary.submittable_count)],
      ])}
    </section>
  </div>
  <section class="section">
    ${sectionHeader("Convergence Curve", "best score and readiness progression")}
    <div class="chart-shell">${lineChart(
      curve,
      [
        { key: "best_score", label: "best_score", color: "#3dd6b3" },
        { key: "quality_ready", label: "quality_ready", color: "#f4c95d" },
        { key: "submittable", label: "submittable", color: "#5be49b" },
      ],
      "iteration"
    )}</div>
  </section>`;
}

function renderActionTimeline(events) {
  return events
    .map((event) => {
      const details = event.details || {};
      const detailsLine = `batch ${fmt(details.executed_batch)} | quality ${fmt(details.quality_ready_count)} | corr blocked ${fmt(
        details.correlation_blocked_count
      )} | submit-ready ${fmt(details.submittable_count)} | best ${fmt(details.best_score_after)}`;
      return `<div class="event">
        <div class="event-head"><span>${escapeHtml(event.iteration)}. ${escapeHtml(event.action)}</span><span class="tag">${escapeHtml(event.stage)}</span></div>
        <div class="event-body">
          <strong>Hypothesis:</strong> ${escapeHtml(event.hypothesis)}<br />
          <strong>Rationale:</strong> ${escapeHtml(event.rationale)}<br />
          <span class="small mono">${escapeHtml(detailsLine)}</span>
        </div>
      </div>`;
    })
    .join("");
}

function renderLeaderboard(leaderboard, clickable = false) {
  return leaderboard
    .slice(0, 8)
    .map((item, index) => {
      const failed = item.failed_submission_checks || item.failed_checks || [];
      const readiness = item.precheck_submit_ready ? "Submit-ready" : "Repair target";
      const status = item.precheck_submit_ready ? "status-good" : "status-warn";
      const attr = clickable ? ` role="button" tabindex="0" data-candidate="${index}"` : "";
      return `<div class="candidate-row"${attr}>
        <div class="mono">#${index + 1} ${escapeHtml(item.alpha_id)}</div>
        <div>
          <div>${escapeHtml(item.idea_name)}</div>
          <div class="small">${escapeHtml(item.family)} | ${escapeHtml(item.stage)}</div>
        </div>
        <div class="mono">${escapeHtml(fmt(item.score))}</div>
        <div class="${status}">${readiness}<br /><span class="small">${escapeHtml(failed.join(", ") || "clear")}</span></div>
      </div>`;
    })
    .join("");
}

function renderFamilyStats(summary) {
  const best = Math.max(...summary.family_stats.map((item) => Number(item.best_score) || 0), 1);
  return bars(summary.family_stats.map((item) => [item.family, Number(item.best_score) / best, fmt(item.best_score)]));
}

function renderFailedChecks(summary) {
  const maxCount = Math.max(...summary.failed_check_histogram.map((item) => Number(item.count) || 0), 1);
  return bars(summary.failed_check_histogram.map((item) => [item.check, Number(item.count) / maxCount, fmt(item.count)]));
}

function renderCandidateDetail(index = 0, metric = "PnL") {
  const item = result.leaderboard[index] || result.leaderboard[0];
  const metrics = item.metrics || {};
  return `<div class="surface candidate-detail">
    <label class="inspect-select">Inspect candidate
      <select id="candidate-select">
        ${result.leaderboard
          .map((candidate, optionIndex) => {
            const label = `${candidate.alpha_id} | ${candidate.family} | score ${fmt(candidate.score)}`;
            return `<option value="${optionIndex}"${optionIndex === index ? " selected" : ""}>${escapeHtml(label)}</option>`;
          })
          .join("")}
      </select>
    </label>
    <pre class="code-block">${escapeHtml(item.expression)}</pre>
    <div class="chart-shell">
      <div class="chart-head">Candidate Performance Chart
        <span>PnL, Sharpe, and Turnover derived from candidate metrics</span>
      </div>
      <label class="chart-select">Chart metric
        <select id="metric-select">
          ${["PnL", "Sharpe", "Turnover"].map((name) => `<option value="${name}"${name === metric ? " selected" : ""}>${name}</option>`).join("")}
        </select>
      </label>
      ${performanceChart(item, metric)}
    </div>
    ${metricGrid([
      { label: "Sharpe", value: fmt(metrics.sharpe), sub: "risk-adjusted signal" },
      { label: "Fitness", value: fmt(metrics.fitness), sub: "platform quality proxy" },
      { label: "Turnover", value: fmt(metrics.turnover, 3), sub: "trading intensity" },
      { label: "Returns", value: fmt(metrics.returns, 3), sub: "expected return proxy" },
      { label: "Drawdown", value: fmt(metrics.drawdown, 3), sub: "tail risk pressure" },
      { label: "Margin", value: fmt(metrics.margin, 5), sub: "capacity hint" },
    ])}
    <details class="json-block">
      <summary>settings and checks</summary>
      <pre>${escapeHtml(JSON.stringify({ settings: item.settings, checks: item.summary }, null, 2))}</pre>
    </details>
  </div>`;
}

function renderAgentTrace() {
  const summary = result.summary;
  return `<div class="grid-2 trace-grid">
    <section class="section">
      ${sectionHeader("Action Timeline", "planner decisions, hypotheses, and outcomes")}
      ${renderActionTimeline(result.events)}
    </section>
    <section class="section">
      ${sectionHeader("Top Candidates", "ranked by submit readiness and score")}
      ${renderLeaderboard(result.leaderboard, true)}
    </section>
  </div>
  <div class="grid-2">
    <section class="section">
      ${sectionHeader("Failure Pressure", "dominant checks steering the next batch")}
      ${renderFailedChecks(summary)}
    </section>
    <section class="section">
      ${sectionHeader("Family Frontier", "which idea families are carrying the run")}
      ${renderFamilyStats(summary)}
    </section>
  </div>
  <section class="section">
    ${sectionHeader("Candidate Inspector", "expression, settings, metrics, and checks")}
    <div id="candidate-detail">${renderCandidateDetail()}</div>
  </section>`;
}

function renderEconomics() {
  return `<section class="section">
    ${sectionHeader("Economic Derivation", "alpha search as constrained expected utility maximization")}
    <div class="equation">Research is modeled as a constrained search problem. The agent allocates simulation budget to maximize expected net utility rather than raw Sharpe alone.</div>
    <div class="math-block">
      <span class="math-op">max</span><span class="math-expr">E[U(x)] = p(x)V - C<sub>sim</sub> n(x) - C<sub>time</sub> t(x) - &lambda;&rho;(x) - &kappa;&tau;(x)</span>
    </div>
    <div class="math-block">
      <span class="math-expr">submit-ready(x) = 1 &iff; g<sub>q</sub>(x) &le; 0, g<sub>self</sub>(x) &le; 0, g<sub>prod</sub>(x) &le; 0, pending(x) = 0</span>
    </div>
    <div class="math-block">
      <span class="math-expr">Sharpe &asymp; IC &middot; &radic;Breadth, &nbsp; Net Edge &asymp; Gross Edge - Turnover Cost</span>
    </div>
  </section>
  <div class="grid-2 economics-grid">
    <section class="section">
      ${sectionHeader("Hot Economic Assumptions", "tune these live")}
      ${slider("payout", "Estimated value of one accepted alpha", 500, 10000, 3000, 250, "$")}
      ${slider("simulation", "Cost per simulation/check call", 0.05, 10, 0.8, 0.05, "$")}
      ${slider("minutes", "Manual analyst minutes per candidate", 1, 25, 8, 0.5, "")}
      ${slider("hourly", "Analyst opportunity cost per hour", 10, 250, 85, 5, "$")}
      ${slider("penalty", "Correlation risk penalty per blocked candidate", 0, 1000, 220, 10, "$")}
    </section>
    <section class="section">
      ${sectionHeader("Decision Economics", "continue search while marginal value is positive")}
      <div id="economics-metrics"></div>
      <div class="math-block compact">
        <span class="math-expr">MVB = Pr(submit-ready &mid; signal) &middot; V - C<sub>sim</sub> - C<sub>time</sub> - C<sub>risk</sub></span>
      </div>
    </section>
  </div>`;
}

function slider(id, label, min, max, value, step, prefix) {
  return `<label class="range-control">
    <span>${escapeHtml(label)}</span>
    <input id="${id}" type="range" min="${min}" max="${max}" value="${value}" step="${step}" data-prefix="${prefix}" />
    <output id="${id}-value">${prefix}${fmt(value, step < 1 ? 2 : 0)}</output>
  </label>`;
}

function updateEconomics() {
  const get = (id) => Number(document.getElementById(id)?.value || 0);
  const summary = result.summary;
  const agent = result.service.agent;
  const baseline = result.service.baseline;
  const evaluated = Number(summary.evaluated_this_run || agent.evaluated || 1);
  const submittable = Number(summary.submittable_count || agent.submittable || 0);
  const payoutValue = get("payout");
  const simulationCost = get("simulation");
  const analystMinutes = get("minutes");
  const hourlyRate = get("hourly");
  const correlationPenalty = get("penalty");
  const manualTimeCost = (evaluated * analystMinutes * hourlyRate) / 60;
  const automatedCost = evaluated * simulationCost;
  const successRate = submittable / Math.max(1, evaluated);
  const expectedValue = successRate * payoutValue;
  const riskAdjustedValue = expectedValue - automatedCost - (Number(summary.correlation_blocked_count || 0) * correlationPenalty) / Math.max(1, evaluated);
  const lift = Number(agent.best_score || summary.best_score || 0) - Number(baseline.best_score || 0);
  const metrics = metricGrid([
    { label: "Manual Time Cost", value: `$${fmt(manualTimeCost)}`, sub: "human loop avoided" },
    { label: "Automated Run Cost", value: `$${fmt(automatedCost)}`, sub: "simulation proxy" },
    { label: "Submit-Ready Rate", value: `${Math.round(successRate * 100)}%`, sub: `${fmt(submittable)} of ${fmt(evaluated)}` },
    { label: "Score Lift vs Baseline", value: fmt(lift), sub: "agent improvement", status: "good" },
    {
      label: "Risk-Adjusted EV",
      value: `$${fmt(riskAdjustedValue)}`,
      sub: "under current assumptions",
      status: riskAdjustedValue > 0 ? "good" : "warn",
    },
    { label: "Stopping Rule", value: riskAdjustedValue > 0 ? "MVB > 0" : "Stop", sub: "marginal value of budget" },
  ]);
  const target = document.getElementById("economics-metrics");
  if (target) target.innerHTML = metrics;
  for (const id of ["payout", "simulation", "minutes", "hourly", "penalty"]) {
    const input = document.getElementById(id);
    const output = document.getElementById(`${id}-value`);
    if (input && output) output.textContent = `${input.dataset.prefix || ""}${fmt(Number(input.value), Number(input.step) < 1 ? 2 : 0)}`;
  }
}

function renderArchitecture() {
  const cells = Object.entries(runtimePreview)
    .map(
      ([key, value]) => `<div class="config-cell">
        <div class="config-k">${escapeHtml(key)}</div>
        <div class="config-v mono">${escapeHtml(value)}</div>
      </div>`
    )
    .join("");
  return `<section class="section">
    ${sectionHeader("System Architecture", "what the service exposes")}
    <div class="stage-flow">
      <div class="stage active"><div class="stage-name">Idea Library</div><div class="stage-desc">Manual seeds, generated templates, family filters, field metadata.</div></div>
      <div class="stage active"><div class="stage-name">Planner</div><div class="stage-desc">Heuristic or OpenAI JSON planner chooses bounded tool actions.</div></div>
      <div class="stage active"><div class="stage-name">Tool Layer</div><div class="stage-desc">Simulate, poll checks, extract metrics, persist JSONL artifacts.</div></div>
      <div class="stage active"><div class="stage-name">Research Logic</div><div class="stage-desc">Score, diagnose, repair, diversify, robustness test, harvest.</div></div>
    </div>
  </section>
  <section class="section">
    ${sectionHeader("Product Narrative", "the story this interface supports")}
    <div class="grid-3">
      <div class="surface"><strong>1. Problem</strong><br /><span class="small">Manual alpha discovery is repetitive, expensive, and error-prone under fixed simulation budget.</span></div>
      <div class="surface"><strong>2. Agent Loop</strong><br /><span class="small">The system plans, evaluates, observes failed checks, and chooses the next research action.</span></div>
      <div class="surface"><strong>3. Product Control</strong><br /><span class="small">Every run is logged, every submission is gated, and every parameter is adjustable from the console.</span></div>
    </div>
  </section>
  <section class="section">
    ${sectionHeader("Current Live Configuration", "all hot-modifiable parameters from the sidebar")}
    <div class="config-grid">${cells}</div>
  </section>`;
}

function renderRaw() {
  return `<section class="section">
    ${sectionHeader("Raw Artifacts", "audit trail for reproducibility")}
    <details class="json-block" open>
      <summary>alpha_service_showcase_2026.json</summary>
      <pre>${escapeHtml(JSON.stringify(result, null, 2))}</pre>
    </details>
    <button id="download-json" type="button">Download current report JSON</button>
  </section>`;
}

const tabs = [
  ["overview", "Overview", renderOverview],
  ["trace", "Agent Trace", renderAgentTrace],
  ["economics", "Economic Logic", renderEconomics],
  ["architecture", "Architecture", renderArchitecture],
  ["raw", "Raw Artifacts", renderRaw],
];

function renderApp() {
  document.querySelector("#app").innerHTML = `<div class="st-static-app">
    ${renderSidebar()}
    <main class="block-container">
      ${renderTopLinks()}
      ${renderHero()}
      <nav class="tabs" aria-label="Service tabs">
        ${tabs.map(([id, label], index) => `<button type="button" data-tab="${id}" aria-selected="${index === 0}">${label}</button>`).join("")}
      </nav>
      ${tabs.map(([id, , renderer], index) => `<div class="tab-panel${index === 0 ? " active" : ""}" id="tab-${id}">${renderer()}</div>`).join("")}
    </main>
  </div>`;

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-tab]").forEach((item) => item.setAttribute("aria-selected", String(item === button)));
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));
      document.getElementById(`tab-${button.dataset.tab}`)?.classList.add("active");
      if (button.dataset.tab === "economics") updateEconomics();
    });
  });

  document.querySelectorAll(".range-control input").forEach((input) => input.addEventListener("input", updateEconomics));
  updateEconomics();
  bindCandidateInspector();
  document.getElementById("download-json")?.addEventListener("click", () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.run_id}.json`;
    link.click();
    URL.revokeObjectURL(url);
  });
}

function bindCandidateInspector() {
  const detail = document.getElementById("candidate-detail");
  if (!detail) return;
  const refresh = () => {
    const candidateIndex = Number(document.getElementById("candidate-select")?.value || 0);
    const metric = document.getElementById("metric-select")?.value || "PnL";
    detail.innerHTML = renderCandidateDetail(candidateIndex, metric);
    bindCandidateInspector();
  };
  document.getElementById("candidate-select")?.addEventListener("change", refresh);
  document.getElementById("metric-select")?.addEventListener("change", refresh);
  document.querySelectorAll("[data-candidate]").forEach((row) => {
    row.addEventListener("click", () => {
      detail.innerHTML = renderCandidateDetail(Number(row.dataset.candidate || 0), "PnL");
      bindCandidateInspector();
      detail.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });
}

renderApp();

import "./styles.css";

const candidates = [
  {
    id: "A-DEMO-7421",
    family: "social_price_repair",
    score: 1288.4,
    sharpe: 1.58,
    fitness: 1.12,
    turnover: 0.25,
    status: "submit-ready",
    expression:
      "ts_mean(-scl12_buzz, 9) + group_rank((ts_mean(close, 30) - close) / close, industry)",
  },
  {
    id: "B-EDGE-0312",
    family: "rank_price_boundary",
    score: 660.23,
    sharpe: 1.44,
    fitness: 1.02,
    turnover: 0.26,
    status: "self-corr watch",
    expression:
      "0.9 * ts_mean(-scl12_buzz, 9) + rank((ts_mean(close, 32) - close) / close)",
  },
  {
    id: "C-ALPHA-0101",
    family: "alpha101_repair",
    score: 210.95,
    sharpe: 1.71,
    fitness: 0.81,
    turnover: 0.6,
    status: "fitness repair",
    expression: "-1 * ((close - open) / ((high - low) + 0.001))",
  },
];

const events = [
  ["09:12", "Replicated Alpha101 seed library", "101 FASTEXPR candidates staged"],
  ["10:26", "Found social/price frontier", "self-correlation at 0.7003"],
  ["11:05", "Tested production decorrelation", "open-volume leg did not lower prod corr"],
  ["13:21", "Rank-price boundary", "fitness 1.00 but prod-corr repair needed"],
];

const curve = [2, 12, 21, 39, 57, 88, 120, 168, 244, 319, 420, 540, 660, 820, 1010, 1288];
const drawdown = [0, -1, -2, -1, -3, -5, -2, -4, -6, -5, -3, -2, -1, -2, -1, 0];

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("en-US", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(value);
}

function sparkline(values, color = "var(--accent)") {
  const width = 340;
  const height = 116;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = values
    .map((value, index) => {
      const x = (index / (values.length - 1)) * width;
      const y = height - ((value - min) / Math.max(1, max - min)) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="score trend">
    <defs>
      <linearGradient id="lineFill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity=".34"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <polyline points="${points}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
    <polygon points="0,${height} ${points} ${width},${height}" fill="url(#lineFill)"/>
  </svg>`;
}

function rows() {
  return candidates
    .map(
      (candidate, index) => `
      <button class="candidate-row ${index === 0 ? "is-active" : ""}" data-candidate="${index}">
        <span class="rank">#${index + 1}</span>
        <span>
          <strong>${candidate.id}</strong>
          <small>${candidate.family}</small>
        </span>
        <span class="mono">${formatNumber(candidate.score)}</span>
        <span class="state">${candidate.status}</span>
      </button>`
    )
    .join("");
}

function eventRows() {
  return events
    .map(
      ([time, title, detail]) => `
      <li>
        <span>${time}</span>
        <strong>${title}</strong>
        <small>${detail}</small>
      </li>`
    )
    .join("");
}

function renderCandidate(candidate) {
  document.querySelector("[data-score]").textContent = formatNumber(candidate.score);
  document.querySelector("[data-sharpe]").textContent = candidate.sharpe.toFixed(2);
  document.querySelector("[data-fitness]").textContent = candidate.fitness.toFixed(2);
  document.querySelector("[data-turnover]").textContent = candidate.turnover.toFixed(2);
  document.querySelector("[data-expression]").textContent = candidate.expression;
  document.querySelector("[data-family]").textContent = candidate.family;
  document.querySelector("[data-state]").textContent = candidate.status;
}

document.querySelector("#app").innerHTML = `
  <main class="app-shell">
    <header class="topbar">
      <a class="brand" href="#overview" aria-label="Alpha Research Agent">
        <span class="brand-mark">A</span>
        <span>Alpha Research Agent</span>
      </a>
      <nav aria-label="Project links">
        <a href="https://github.com/zeron-G/worldquant-alpha-research-agent" target="_blank" rel="noreferrer">GitHub</a>
        <a href="https://rongzegao.com" target="_blank" rel="noreferrer">rongzegao.com</a>
      </nav>
    </header>

    <section class="hero" id="overview">
      <div class="hero-copy">
        <p class="section-label">presentation console</p>
        <h1>Alpha search, explained as a live research system.</h1>
        <p>
          A lightweight pre-deploy shell for showing the agent's frontier:
          candidate generation, quality checks, correlation pressure, and
          submission readiness without exposing credentials or backend tools.
        </p>
        <div class="hero-actions">
          <a href="#leaderboard" class="primary-action">View frontier</a>
          <a href="#architecture" class="secondary-action">Architecture</a>
        </div>
      </div>
      <div class="hero-visual" aria-label="Agent run state">
        <div class="terminal-card">
          <div class="terminal-head">
            <span></span><span></span><span></span>
            <strong>run state</strong>
          </div>
          <pre>planner: gpt5.5
budget: 24 candidates
stage: harvest
best: A-DEMO-7421
checks: quality pass, corr pass
action: submit-ready</pre>
        </div>
        <div class="orbit-card">
          <span>quality</span>
          <strong>6 / 8</strong>
          <small>checks passing</small>
        </div>
      </div>
    </section>

    <section class="metric-grid" aria-label="Run metrics">
      <article><span>Best Score</span><strong data-score>1,288.40</strong><small>frontier objective</small></article>
      <article><span>Sharpe</span><strong data-sharpe>1.58</strong><small>risk-adjusted signal</small></article>
      <article><span>Fitness</span><strong data-fitness>1.12</strong><small>submission threshold</small></article>
      <article><span>Turnover</span><strong data-turnover>0.25</strong><small>capacity-aware</small></article>
    </section>

    <section class="dashboard-grid">
      <article class="panel span-7">
        <div class="panel-heading">
          <span>Score convergence</span>
          <strong>quality frontier</strong>
        </div>
        <div class="chart-shell">${sparkline(curve)}</div>
      </article>
      <article class="panel span-5">
        <div class="panel-heading">
          <span>Risk pressure</span>
          <strong>drawdown proxy</strong>
        </div>
        <div class="chart-shell danger">${sparkline(drawdown, "var(--warn)")}</div>
      </article>
    </section>

    <section class="dashboard-grid" id="leaderboard">
      <article class="panel span-7">
        <div class="panel-heading">
          <span>Candidate frontier</span>
          <strong data-family>social_price_repair</strong>
        </div>
        <div class="candidate-list">${rows()}</div>
      </article>
      <article class="panel span-5">
        <div class="panel-heading">
          <span>Latest expression</span>
          <strong data-state>submit-ready</strong>
        </div>
        <code data-expression></code>
      </article>
    </section>

    <section class="timeline" aria-label="Agent trace">
      <div>
        <p class="section-label">agent trace</p>
        <h2>Planner decisions stay auditable.</h2>
      </div>
      <ol>${eventRows()}</ol>
    </section>

    <section class="architecture" id="architecture">
      <div>
        <p class="section-label">architecture</p>
        <h2>Static pre shell, production agent behind it.</h2>
        <p>
          This deployment intentionally omits live credentials and simulation
          execution. The production research code remains in the repository;
          the pre site is a standalone frontend artifact for demos.
        </p>
      </div>
      <div class="architecture-map">
        <span>Idea library</span>
        <span>Planner</span>
        <span>Simulation</span>
        <span>Check summary</span>
        <span>Submit gate</span>
      </div>
    </section>
  </main>
`;

renderCandidate(candidates[0]);

document.querySelectorAll("[data-candidate]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-candidate]").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    renderCandidate(candidates[Number(button.dataset.candidate)]);
  });
});

// State
let DATA = null;
let currentApp = "employee";
let activeCharts = [];

function destroyActiveCharts() {
    activeCharts.forEach(c => {
        try { c.destroy(); } catch (_) {}
    });
    activeCharts = [];
}

// Label maps
const ISSUE_LABELS = {
    app_crash_freeze:   "💥 App Crash/Freeze",
    login_auth:         "🔐 Login/Auth",
    booking_failure:    "📅 Booking Failure",
    wrong_assignment:   "🚗 Wrong Assignment",
    tracking_inaccurate:"📍 Tracking Issues",
    driver_behaviour:   "👤 Driver Behaviour",
    safety_concern:     "🛡️ Safety Concern",
    late_pickup:        "⏰ Late Pickup",
    notification_issue: "🔔 Notification Issue",
    ui_ux_poor:         "🎨 UI/UX Issues",
    performance_slow:   "🐢 Slow Performance",
    update_regression:  "📱 Update Regression",
    feature_request:    "💡 Feature Request",
    billing_payment:    "💳 Billing/Payment",
    positive_feedback:  "👍 Positive",
    other:              "📝 Other",
};

const STAGE_LABELS = {
    booking:          "📅 Booking",
    assignment:       "🚗 Assignment",
    pickup_tracking:  "📍 Pickup & Tracking",
    safety:           "🛡️ Safety",
    ride_experience:  "🚙 Ride Experience",
    dropoff:          "🏠 Dropoff",
    issue_resolution: "📞 Issue Resolution",
    app_general:      "📱 App General",
    other:            "📝 Other",
};

// Chart colours
const COLORS = {
    indigo:  "rgba(99, 102, 241, 0.8)",
    violet:  "rgba(167, 139, 250, 0.8)",
    emerald: "rgba(52, 211, 153, 0.8)",
    amber:   "rgba(251, 191, 36, 0.8)",
    rose:    "rgba(251, 113, 133, 0.8)",
    cyan:    "rgba(34, 211, 238, 0.8)",
    orange:  "rgba(251, 146, 60, 0.8)",
    sky:     "rgba(56, 189, 248, 0.8)",
    lime:    "rgba(163, 230, 53, 0.8)",
    fuchsia: "rgba(232, 121, 249, 0.8)",
};

const STAR_COLORS = {
    1: "rgba(239, 68, 68, 0.8)",
    2: "rgba(251, 146, 60, 0.8)",
    3: "rgba(251, 191, 36, 0.8)",
    4: "rgba(52, 211, 153, 0.7)",
    5: "rgba(34, 197, 94, 0.8)",
};


//  Data loading
async function loadData() {
    try {
        const resp = await fetch("../data/analysis_output.json");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        DATA = await resp.json();
        render();
    } catch (e) {
        document.getElementById("app").innerHTML = `
            <div class="error-state">
                <h2>⚠️ Could not load analysis data</h2>
                <p style="margin-top:12px; color: var(--text-secondary);">
                    Run the pipeline first from the project root:<br>
                    <code style="background:var(--bg-card);padding:4px 8px;border-radius:6px;margin-top:8px;display:inline-block;">
                        python run_pipeline.py
                    </code>
                </p>
                <p style="margin-top:12px;color:var(--text-muted);font-size:0.85rem;">${e.message}</p>
            </div>`;
    }
}


// Render orchestration
function getAppData() {
    if (currentApp === "combined") return null;
    return DATA?.apps?.[currentApp];
}

function switchApp(app) {
    currentApp = app;
    render();
}
// Expose to inline onclick handlers
window.switchApp = switchApp;

function render() {
    destroyActiveCharts();
    const appData = getAppData();
    const container = document.getElementById("app");

    container.innerHTML = [
        renderHero(),
        renderTabs(),
        currentApp === "combined" ? renderCombinedView() : renderAppView(appData),
        renderFooter(),
    ].join("");

    requestAnimationFrame(() => {
        if (currentApp === "combined") initCombinedCharts();
        else if (appData) initCharts(appData);
    });
}


// Section renderers
function renderHero() {
    const generated = DATA?.generated_at
        ? new Date(DATA.generated_at).toLocaleDateString("en-IN", {
              day: "numeric", month: "short", year: "numeric",
              hour: "2-digit", minute: "2-digit",
          })
        : "Unknown";

    const emp = DATA?.apps?.employee;
    const drv = DATA?.apps?.driver;

    return `
    <header class="hero fade-in">
        <div class="hero-badge">Live Intelligence</div>
        <h1>Play Store Review Intelligence</h1>
        <p>Real-time analysis of employee and driver app reviews — tied to the commute journey</p>
        <div class="hero-meta">
            <div class="hero-meta-item">
                <span>📊</span>
                <span class="value">${DATA?.total_reviews?.toLocaleString() || 0}</span>
                <span>reviews analyzed</span>
            </div>
            ${emp ? `<div class="hero-meta-item">
                <span>📱</span><span>Employee App</span>
                <span class="value" style="color:${emp.overall_avg_rating >= 4 ? "var(--accent-emerald)" : "var(--accent-amber)"}">
                    ⭐ ${emp.overall_avg_rating}
                </span>
            </div>` : ""}
            ${drv ? `<div class="hero-meta-item">
                <span>🚗</span><span>Driver App</span>
                <span class="value" style="color:${drv.overall_avg_rating >= 4 ? "var(--accent-emerald)" : "var(--accent-rose)"}">
                    ⭐ ${drv.overall_avg_rating}
                </span>
            </div>` : ""}
            <div class="hero-meta-item">
                <span>🕐</span><span>Updated</span>
                <span class="value">${generated}</span>
            </div>
        </div>
    </header>`;
}

function renderTabs() {
    const tabs = [
        { key: "employee", icon: "📱", label: "Employee App" },
        { key: "driver",   icon: "🚗", label: "Driver App" },
        { key: "combined", icon: "📊", label: "Combined View" },
    ];
    return `
    <div class="tab-bar fade-in stagger-1">
        ${tabs.map(t => `
            <button class="tab-btn ${currentApp === t.key ? "active" : ""}"
                    onclick="switchApp('${t.key}')">
                ${t.icon} ${t.label}
            </button>`).join("")}
    </div>`;
}


// Per-app view
function renderAppView(data) {
    if (!data) return '<div class="error-state"><p>No data for this app.</p></div>';

    return `
        ${renderScoreCards(data)}
        <div class="charts-grid fade-in stagger-3">
            <div class="chart-card">
                <h3>Rating Trend Over Time</h3>
                <div class="chart-subtitle">Monthly average rating from reviews</div>
                <div class="chart-wrapper"><canvas id="trendChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Star Distribution</h3>
                <div class="chart-subtitle">Current rating breakdown</div>
                <div class="chart-wrapper"><canvas id="starChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Issues by Journey Stage</h3>
                <div class="chart-subtitle">Where in the commute do problems occur?</div>
                <div class="chart-wrapper"><canvas id="journeyChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Rating Impact by Issue Type</h3>
                <div class="chart-subtitle">Which issues drag ratings down the most?</div>
                <div class="chart-wrapper"><canvas id="impactChart"></canvas></div>
            </div>
            <div class="chart-card full-width">
                <h3>Issue Volume Over Time</h3>
                <div class="chart-subtitle">How issue categories evolve month over month</div>
                <div class="chart-wrapper"><canvas id="issueTimeChart" style="max-height:360px"></canvas></div>
            </div>
        </div>
        ${renderRecommendations(data.prioritized_recommendations, data.app_label)}
        ${renderTopReviews(data.top_reviews)}
        ${renderDevReplyStats(data.dev_reply_stats)}`;
}


// Combined view
function renderCombinedView() {
    return `
        ${renderCombinedScoreCards()}
        <div class="charts-grid fade-in stagger-3">
            <div class="chart-card">
                <h3>Employee vs Driver: Rating Comparison</h3>
                <div class="chart-subtitle">Monthly average rating side by side</div>
                <div class="chart-wrapper"><canvas id="compareChart"></canvas></div>
            </div>
            <div class="chart-card">
                <h3>Issue Distribution Across Apps</h3>
                <div class="chart-subtitle">Which issues affect which app more?</div>
                <div class="chart-wrapper"><canvas id="compareIssueChart"></canvas></div>
            </div>
        </div>
        ${renderRecommendations(DATA?.combined_recommendations || [], "Both Apps")}`;
}


// Score cards
function renderScoreCards(data) {
    const impact  = data.rating_impact_by_issue || {};
    const negList = Object.entries(impact)
        .filter(([k, v]) => v.rating_gap > 0 && k !== "positive_feedback")
        .sort((a, b) => b[1].weighted_drag - a[1].weighted_drag);
    const worst = negList[0];

    const journey    = data.journey_breakdown || {};
    const worstStage = Object.entries(journey)
        .filter(([k]) => k !== "other")
        .sort((a, b) => b[1].negative_pct - a[1].negative_pct)[0];

    const ratingColor = v =>
        v >= 4 ? "var(--accent-emerald)" : v >= 3 ? "var(--accent-amber)" : "var(--accent-rose)";

    return `
    <div class="score-cards fade-in stagger-2">
        <div class="score-card">
            <div class="label">Average Rating</div>
            <div class="value" style="color:${ratingColor(data.overall_avg_rating)}">${data.overall_avg_rating}</div>
            <div class="sub">from ${data.total_reviews} reviews</div>
        </div>
        <div class="score-card">
            <div class="label">Total Reviews</div>
            <div class="value">${data.total_reviews?.toLocaleString()}</div>
            <div class="sub">in dataset</div>
        </div>
        <div class="score-card">
            <div class="label">Biggest Drag</div>
            <div class="value" style="font-size:1.1rem;color:var(--accent-rose)">
                ${worst ? (ISSUE_LABELS[worst[0]] || worst[0]) : "N/A"}
            </div>
            <div class="sub">${worst ? `${worst[1].count} reviews, avg ${worst[1].avg_rating}★` : ""}</div>
        </div>
        <div class="score-card">
            <div class="label">Worst Journey Stage</div>
            <div class="value" style="font-size:1.1rem;color:var(--accent-amber)">
                ${worstStage ? (STAGE_LABELS[worstStage[0]] || worstStage[0]) : "N/A"}
            </div>
            <div class="sub">${worstStage ? `${worstStage[1].negative_pct}% negative` : ""}</div>
        </div>
        <div class="score-card">
            <div class="label">Dev Reply Rate</div>
            <div class="value" style="color:${(data.dev_reply_stats?.reply_rate_pct || 0) > 30 ? "var(--accent-emerald)" : "var(--accent-rose)"}">
                ${data.dev_reply_stats?.reply_rate_pct || 0}%
            </div>
            <div class="sub">${data.dev_reply_stats?.replied_count || 0} of ${data.total_reviews} replied</div>
        </div>
    </div>`;
}

function renderCombinedScoreCards() {
    const emp = DATA?.apps?.employee;
    const drv = DATA?.apps?.driver;
    return `
    <div class="score-cards score-cards-4 fade-in stagger-2">
        <div class="score-card">
            <div class="label">Employee App Rating</div>
            <div class="value" style="color:var(--accent-emerald)">${emp?.overall_avg_rating || "—"}</div>
            <div class="sub">${emp?.total_reviews || 0} reviews</div>
        </div>
        <div class="score-card">
            <div class="label">Driver App Rating</div>
            <div class="value" style="color:var(--accent-orange)">${drv?.overall_avg_rating || "—"}</div>
            <div class="sub">${drv?.total_reviews || 0} reviews</div>
        </div>
        <div class="score-card">
            <div class="label">Total Reviews</div>
            <div class="value">${DATA?.total_reviews?.toLocaleString() || 0}</div>
            <div class="sub">across both apps</div>
        </div>
        <div class="score-card">
            <div class="label">Rating Gap</div>
            <div class="value" style="color:var(--accent-rose)">
                ${emp && drv ? (emp.overall_avg_rating - drv.overall_avg_rating).toFixed(2) : "—"}
            </div>
            <div class="sub">employee − driver</div>
        </div>
    </div>`;
}


// Recommendations table
function renderRecommendations(recs, appLabel) {
    if (!recs?.length) return "";

    const maxDrag = Math.max(...recs.map(x => x.weighted_drag));
    const rows = recs.slice(0, 15).map(r => {
        const rank     = r.overall_rank || r.rank;
        const rankCls  = rank === 1 ? "r1" : rank === 2 ? "r2" : rank === 3 ? "r3" : "rn";
        const appCls   = r.app?.includes("Driver") ? "driver" : "employee";
        const barWidth = maxDrag > 0 ? Math.round((r.weighted_drag / maxDrag) * 100) : 0;

        return `
        <tr>
            <td><span class="rank-badge ${rankCls}">${rank}</span></td>
            <td><span class="issue-tag">${ISSUE_LABELS[r.issue] || r.issue}</span></td>
            <td><span class="app-tag ${appCls}">${r.app}</span></td>
            <td>${r.count}</td>
            <td>${r.avg_rating}★</td>
            <td>
                <div class="impact-bar">
                    <span>${r.weighted_drag.toFixed(3)}</span>
                    <div class="bar-bg"><div class="bar-fill" style="width:${barWidth}%"></div></div>
                </div>
            </td>
            <td>${r.share_pct}%</td>
        </tr>`;
    }).join("");

    return `
    <div class="recs-section fade-in stagger-4">
        <h2>🎯 Prioritized Recommendations</h2>
        <p class="recs-subtitle">Ranked by weighted rating drag — fix the top items first to maximize rating improvement for ${appLabel}</p>
        <div class="table-responsive">
            <table class="rec-table">
                <thead><tr>
                    <th>Rank</th><th>Issue</th><th>App</th>
                    <th>Reviews</th><th>Avg ★</th><th>Rating Drag</th><th>Share</th>
                </tr></thead>
                <tbody>${rows}</tbody>
            </table>
        </div>
    </div>`;
}


// Top reviews
function renderTopReviews(reviews) {
    if (!reviews?.length) return "";

    const cards = reviews.map(r => {
        const stars = "⭐".repeat(r.rating) + "☆".repeat(5 - r.rating);
        const date  = r.review_date
            ? new Date(r.review_date).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
            : "";
        return `
        <div class="review-card">
            <div class="review-stars">${stars}</div>
            <div class="review-text">${escapeHtml(r.text)}</div>
            <div class="review-meta">
                <span><span class="issue-tag" style="font-size:0.7rem">${ISSUE_LABELS[r.issue_type] || r.issue_type}</span></span>
                <span>${date}</span>
                <span class="thumbs-up">👍 ${r.thumbs_up}</span>
            </div>
        </div>`;
    }).join("");

    return `
    <div class="fade-in stagger-5">
        <h2 style="font-size:1.3rem;font-weight:700;margin-bottom:16px">📣 Most Upvoted Reviews</h2>
        <p class="recs-subtitle" style="margin-bottom:20px">Reviews that other users found helpful — strong signal</p>
        <div class="reviews-grid">${cards}</div>
    </div>`;
}


// Dev reply stats
function renderDevReplyStats(stats) {
    if (!stats) return "";
    const repliedAvgText = stats.replied_count > 0 
        ? `${stats.replied_avg_rating}★ vs ${stats.unreplied_avg_rating}★`
        : `None (vs ${stats.unreplied_avg_rating}★)`;

    return `
    <div class="chart-card fade-in stagger-5" style="margin-bottom:32px">
        <h3>Developer Response Analysis</h3>
        <div class="chart-subtitle">Reply patterns and their effect on ratings</div>
        <div class="dev-stat-grid">
            <div class="dev-stat">
                <div class="stat-value" style="color:${stats.reply_rate_pct > 30 ? "var(--accent-emerald)" : "var(--accent-rose)"}">${stats.reply_rate_pct}%</div>
                <div class="stat-label">Response Rate</div>
            </div>
            <div class="dev-stat">
                <div class="stat-value" style="color:var(--accent-indigo)">${stats.replied_count}</div>
                <div class="stat-label">Replied</div>
            </div>
            <div class="dev-stat">
                <div class="stat-value" style="color:var(--text-secondary)">${stats.unreplied_count}</div>
                <div class="stat-label">No Reply</div>
            </div>
            <div class="dev-stat">
                <div class="stat-value" style="color:var(--accent-amber)">${repliedAvgText}</div>
                <div class="stat-label">Replied vs Unreplied Avg</div>
            </div>
        </div>
    </div>`;
}


// Footer
function renderFooter() {
    return `
    <footer class="footer">
        <p>MoveInSync Play Store Intelligence Dashboard · Generated by automated pipeline</p>
        <p style="margin-top:4px">Rerun: <code>python run_pipeline.py</code></p>
    </footer>`;
}


// Charts
const CHART_DEFAULTS = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { labels: { color: "#94a3b8", font: { family: "Inter", size: 11 } } },
    },
    scales: {
        x: { ticks: { color: "#64748b", font: { family: "Inter", size: 10 } }, grid: { color: "rgba(255,255,255,0.04)" } },
        y: { ticks: { color: "#64748b", font: { family: "Inter", size: 10 } }, grid: { color: "rgba(255,255,255,0.04)" } },
    },
};

function initCharts(data) {
    chartTrend(data);
    chartStars(data);
    chartJourney(data);
    chartImpact(data);
    chartIssueTime(data);
}

function initCombinedCharts() {
    chartCompare();
    chartCompareIssues();
}

function chartTrend(data) {
    const el = document.getElementById("trendChart");
    if (!el) return;
    const months  = Object.keys(data.monthly_trends || {});
    const ratings = months.map(m => data.monthly_trends[m].avg_rating);
    const counts  = months.map(m => data.monthly_trends[m].count);

    const c = new Chart(el, {
        type: "line",
        data: {
            labels: months,
            datasets: [
                { label: "Avg Rating", data: ratings, borderColor: COLORS.indigo, backgroundColor: "rgba(99,102,241,0.1)", fill: true, tension: 0.4, pointRadius: 3, yAxisID: "y" },
                { label: "Review Count", data: counts, borderColor: COLORS.amber, fill: false, tension: 0.4, pointRadius: 2, borderDash: [5, 5], yAxisID: "y1" },
            ],
        },
        options: {
            ...CHART_DEFAULTS,
            scales: {
                ...CHART_DEFAULTS.scales,
                y:  { ...CHART_DEFAULTS.scales.y, min: 1, max: 5, position: "left" },
                y1: { ...CHART_DEFAULTS.scales.y, position: "right", grid: { drawOnChartArea: false } },
            },
        },
    });
    activeCharts.push(c);
}

function chartStars(data) {
    const el = document.getElementById("starChart");
    if (!el) return;
    const dist = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    Object.values(data.monthly_trends || {}).forEach(m =>
        Object.entries(m.star_dist || {}).forEach(([s, c]) => { dist[s] = (dist[s] || 0) + c; })
    );
    const c = new Chart(el, {
        type: "doughnut",
        data: {
            labels: ["1★", "2★", "3★", "4★", "5★"],
            datasets: [{ data: [dist[1], dist[2], dist[3], dist[4], dist[5]], backgroundColor: [STAR_COLORS[1], STAR_COLORS[2], STAR_COLORS[3], STAR_COLORS[4], STAR_COLORS[5]], borderWidth: 0, hoverOffset: 8 }],
        },
        options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "right", labels: { color: "#94a3b8", font: { family: "Inter", size: 12 }, padding: 16 } } }, cutout: "65%" },
    });
    activeCharts.push(c);
}

function chartJourney(data) {
    const el = document.getElementById("journeyChart");
    if (!el) return;
    const stages  = Object.keys(data.journey_breakdown || {}).filter(s => s !== "other");
    const counts  = stages.map(s => data.journey_breakdown[s].count);
    const avgRat  = stages.map(s => data.journey_breakdown[s].avg_rating);
    const labels  = stages.map(s => STAGE_LABELS[s] || s);
    const palette = Object.values(COLORS);

    const c = new Chart(el, {
        type: "bar",
        data: {
            labels,
            datasets: [
                { label: "Reviews", data: counts, backgroundColor: stages.map((_, i) => palette[i % palette.length]), borderRadius: 6, yAxisID: "y" },
                { label: "Avg Rating", data: avgRat, type: "line", borderColor: COLORS.amber, pointBackgroundColor: COLORS.amber, tension: 0.4, yAxisID: "y1" },
            ],
        },
        options: {
            ...CHART_DEFAULTS,
            scales: {
                ...CHART_DEFAULTS.scales,
                y:  { ...CHART_DEFAULTS.scales.y, position: "left" },
                y1: { ...CHART_DEFAULTS.scales.y, min: 1, max: 5, position: "right", grid: { drawOnChartArea: false } },
            },
        },
    });
    activeCharts.push(c);
}

function chartImpact(data) {
    const el = document.getElementById("impactChart");
    if (!el) return;
    const issues = Object.entries(data.rating_impact_by_issue || {})
        .filter(([k, v]) => k !== "positive_feedback" && v.weighted_drag > 0)
        .sort((a, b) => b[1].weighted_drag - a[1].weighted_drag)
        .slice(0, 10);

    const c = new Chart(el, {
        type: "bar",
        data: {
            labels: issues.map(([k]) => (ISSUE_LABELS[k] || k).replace(/^.+? /, "")),
            datasets: [{ label: "Weighted Rating Drag", data: issues.map(([, v]) => v.weighted_drag), backgroundColor: "rgba(251,113,133,0.6)", borderColor: "rgba(251,113,133,0.9)", borderWidth: 1, borderRadius: 6 }],
        },
        options: { ...CHART_DEFAULTS, indexAxis: "y" },
    });
    activeCharts.push(c);
}

function chartIssueTime(data) {
    const el = document.getElementById("issueTimeChart");
    if (!el) return;
    const months = Object.keys(data.issue_trends || {});
    const totals = {};
    Object.values(data.issue_trends || {}).forEach(iss =>
        Object.entries(iss).forEach(([k, c]) => {
            if (k !== "positive_feedback" && k !== "other") totals[k] = (totals[k] || 0) + c;
        })
    );
    const top = Object.entries(totals).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([k]) => k);
    const palette = Object.values(COLORS);

    const c = new Chart(el, {
        type: "line",
        data: {
            labels: months,
            datasets: top.map((iss, i) => ({
                label: (ISSUE_LABELS[iss] || iss).replace(/^.+? /, ""),
                data: months.map(m => (data.issue_trends[m] || {})[iss] || 0),
                borderColor: palette[i % palette.length],
                fill: false, tension: 0.4, pointRadius: 2,
            })),
        },
        options: {
            ...CHART_DEFAULTS,
            plugins: { legend: { position: "bottom", labels: { color: "#94a3b8", font: { family: "Inter", size: 10 }, padding: 12, usePointStyle: true } } },
        },
    });
    activeCharts.push(c);
}

function chartCompare() {
    const el = document.getElementById("compareChart");
    if (!el) return;
    const empT = DATA?.apps?.employee?.monthly_trends || {};
    const drvT = DATA?.apps?.driver?.monthly_trends   || {};
    const months = [...new Set([...Object.keys(empT), ...Object.keys(drvT)])].sort();

    const c = new Chart(el, {
        type: "line",
        data: {
            labels: months,
            datasets: [
                { label: "Employee App", data: months.map(m => empT[m]?.avg_rating || null), borderColor: COLORS.emerald, backgroundColor: "rgba(52,211,153,0.08)", fill: true, tension: 0.4, spanGaps: true },
                { label: "Driver App",   data: months.map(m => drvT[m]?.avg_rating || null), borderColor: COLORS.orange,  backgroundColor: "rgba(251,146,60,0.08)",  fill: true, tension: 0.4, spanGaps: true },
            ],
        },
        options: { ...CHART_DEFAULTS, scales: { ...CHART_DEFAULTS.scales, y: { ...CHART_DEFAULTS.scales.y, min: 1, max: 5 } } },
    });
    activeCharts.push(c);
}

function chartCompareIssues() {
    const el = document.getElementById("compareIssueChart");
    if (!el) return;
    const empI = DATA?.apps?.employee?.rating_impact_by_issue || {};
    const drvI = DATA?.apps?.driver?.rating_impact_by_issue   || {};
    const all  = [...new Set([...Object.keys(empI), ...Object.keys(drvI)])].filter(k => k !== "positive_feedback");

    const c = new Chart(el, {
        type: "bar",
        data: {
            labels: all.map(k => (ISSUE_LABELS[k] || k).replace(/^.+? /, "")),
            datasets: [
                { label: "Employee App", data: all.map(k => empI[k]?.count || 0), backgroundColor: COLORS.emerald, borderRadius: 4 },
                { label: "Driver App",   data: all.map(k => drvI[k]?.count || 0), backgroundColor: COLORS.orange,  borderRadius: 4 },
            ],
        },
        options: { ...CHART_DEFAULTS, indexAxis: "y" },
    });
    activeCharts.push(c);
}


// Helpers
function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str || "";
    return d.innerHTML;
}


// Boot
loadData();

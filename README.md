# MoveInSync — Play Store Review Intelligence & Journey Analytics

An end-to-end intelligence pipeline and interactive analytics dashboard built for **Forward Deployed Engineering (FDE) at MoveInSync**.

In enterprise employee transport, Play Store reviews aren't just vanity metrics. When corporate commuters experience friction at 8:00 AM on a rainy Monday, client HR and transport desks get flooded with escalations. This project transforms raw, unstructured Play Store feedback into a living operational intelligence system — diagnosing *why* ratings drop across the commute journey and providing prioritized, code-level solutions.

---

## 📸 Dashboard Walkthrough

### 1. Employee App Intelligence (`com.moveinsync.ets`)
Tracks ratings, identifies the biggest drags on customer satisfaction, maps complaints across commute stages, and surfaces the most-upvoted reviews.

![Employee App Dashboard](screenshots/employee_app_dashboard.png)

---

### 2. Cross-App Comparison & Combined Intelligence
Compares the Employee App (**3.79★**) against the Driver Partner App (**2.71★**), highlighting shared systemic issues and fleet-wide priorities.

![Combined View Dashboard](screenshots/combined_view_dashboard.png)

---

### 3. Driver Partner App Intelligence (`com.moveinsync.driver.dco`)
Uncovers the root cause behind the Driver App's critically low rating: driver document submission failures during onboarding.

![Driver App Dashboard](screenshots/driver_app_dashboard.png)

---

### 4. Focused Charts & Commute Journey Breakdown
Interactive monthly rating trends, star distributions, journey stage complaint heatmaps, and issue drag rankings.

![Dashboard Hero & Charts](screenshots/dashboard_hero_and_charts.png)

---

## 💡 The Problem: Why Ratings Drop

Ratings don't drop because employees dislike the concept of corporate cabs. Hundreds of 5-star reviews praise comfortable cabs, safe night dropoffs, and disciplined drivers.

Ratings collapse at **high-anxiety transition points in the daily commute**:

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Self-Booking   │───►│ Cab Assignment  │───►│ Pickup & Track  │───►│ In-Ride & Safety│───►│Dropoff & Support│
│ 100% Negative   │    │ Smooth / Auto   │    │ 60% Negative    │    │ 66.7% Negative  │    │ 50% Negative    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

1. **Self-Booking Failures (100% Negative):** Self-booking is MoveInSync's primary flow. If an employee tries to book a cab right before the roster cutoff and the request fails silently or gives a generic error, they are stranded without transport.
2. **Update Regressions (Biggest Overall Drag):** When an app update introduces a launch crash or corrupts the local session, employees cannot open the app to verify their morning cab, triggering sudden spikes in 1★ reviews.
3. **Boarding & OTP Friction (Safety Gating):** Well-intentioned safety reminders (e.g. a mandatory seatbelt popup) are currently positioned right in front of the Boarding OTP, forcing extra taps while the commuter is rushing into the cab.
4. **Live Tracking Drift:** Inaccurate driver locations and jumpy ETAs leave commuters waiting outside without knowing which campus gate the cab is parked at.

---

## 🎯 Prioritization: The Weighted Rating Drag Model

Instead of counting raw issue frequency (which favors minor, noisy gripes), issues are prioritized using **Weighted Rating Drag**:

$$\text{Rating Drag} = \frac{\text{Issue Review Count}}{\text{Total Reviews}} \times (\text{Overall Average} - \text{Issue Average Rating})$$

- **High-impact 1-star blockers** (like an app update that won't open) score high because they pull the average down sharply.
- **Mild 3-star or 4-star cosmetic suggestions** score low because they don't drag down the app store health.

| Priority | Issue Category | Impacted Stage | Avg Rating | Weighted Drag | Root Cause & Fix |
|:---:|:---|:---|:---:|:---:|:---|
| **P0** | **Update Regressions** | App Launch | 1.0★ | **0.211** | Staged releases (1% → 5% → 20% → 100%) & cold-start smoke tests |
| **P1** | **UI/UX Friction** | Boarding & OTP | 1.33★ | **0.139** | Remove seatbelt popup before OTP; show OTP in persistent notification |
| **P2** | **Booking Failures** | Self-Booking | 1.0★ | **0.105** | Actionable cutoff error messages & offline request queuing |
| **P3** | **Tracking Inaccuracy** | Pickup | 2.0★ | **0.101** | Dead-reckoning location smoothing & corporate campus gate geofencing |

Fixing just the top 3 issues recovers an estimated **+0.45 rating points**, elevating the Employee App from **3.79★ to ~4.25★**.

---

## 🏗️ Architecture & Pipeline Flow

The project is built as a repeatable, automated system rather than a static one-time report:

```text
 1. SCRAPE                   2. TAG                     3. ANALYZE                4. SERVE
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ Google Play      │──────►│ Gemini Flash LLM │──────►│ Statistical      │──────►│ Interactive      │
│ Scraper          │       │ JSON Batching    │       │ Drag & Ranking   │       │ Dashboard +      │
│ (Incremental)    │       │ (Taxonomy Map)   │       │ Engine           │       │ Strategy Memo    │
└──────────────────┘       └──────────────────┘       └──────────────────┘       └──────────────────┘
```

- **`pipeline/collect_reviews.py`**: Scrapes reviews for both employee and driver apps, appending only new reviews to avoid duplicates.
- **`pipeline/tag_reviews.py`**: Sends unclassified reviews to Google Gemini (`gemini-2.5-flash-lite` or `gemini-2.0-flash`) in token-efficient JSON batches, tagging each review by **commute journey stage**, **issue type**, and **sentiment**.
- **`pipeline/analyze_reviews.py`**: Calculates monthly rating trends, star distributions, developer reply statistics, and weighted rating drag rankings, saving output to `data/analysis_output.json`.
- **`pipeline/generate_memo.py`**: Generates the executive strategy document ([`RECOMMENDATION.md`](RECOMMENDATION.md)).
- **`dashboard/`**: Dark-mode frontend built with clean HTML5, CSS Grid/Flexbox, and Chart.js.

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- A Google Gemini API key ([free tier from Google AI Studio](https://aistudio.google.com/))

### 2. Setup Environment
```bash
# Clone the repository
git clone https://github.com/Anurag-Basuri/moveinsync.git
cd moveinsync

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\Activate.ps1
# On macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Your Gemini API Key
Create a `.env` file from the provided template:
```bash
# Copy template
cp .env.example .env
```
Open `.env` in any text editor and add your key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

---

## 💻 Running the Pipeline

### Option A: Complete Pipeline (End-to-End)
Scrapes new reviews, tags untagged reviews with Gemini, recalculates metrics, regenerates the memo, and launches the dashboard:
```bash
python run_pipeline.py
```

### Option B: Fast Tagging & Analysis (Skip Scraping)
If you already have reviews in `data/` and want to test tagging on a subset:
```bash
# Tag a batch of 30 reviews and update dashboard
python run_pipeline.py --skip-collect --limit 30
```

### Option C: Launch Dashboard Directly
The dashboard is served via a lightweight local server to allow client-side fetching of `data/analysis_output.json`:
```bash
python run_pipeline.py --serve
```
Open your browser at **[http://localhost:8000/dashboard/index.html](http://localhost:8000/dashboard/index.html)**.

---

## ⚙️ CLI Reference

| Flag | Description | Default |
|:---|:---|:---|
| `--skip-collect` | Skip Play Store scraping (use existing raw CSVs) | `False` |
| `--limit N` | Limit the number of untagged reviews to process | All untagged |
| `--full` | Retag all reviews from scratch (bypasses cache) | `False` |
| `--serve` | Start local HTTP server to host the dashboard | `False` |
| `--port N` | Port number for the dashboard server | `8000` |
| `--no-open` | Prevent browser from auto-opening | `False` |

---

## 📂 Project Organization

```text
moveinsync/
├── dashboard/                  # Interactive visual dashboard
│   ├── index.html              # HTML structure & semantic layout
│   ├── styles.css              # Custom dark-theme styling, glassmorphism & responsive grid
│   └── app.js                  # Reactive state, Chart.js instances & tab controller
├── data/                       # CSV datasets and JSON analysis artifacts
│   ├── reviews_com.moveinsync.ets.csv         # Employee app raw reviews
│   ├── reviews_com.moveinsync.driver.dco.csv  # Driver app raw reviews
│   ├── tagged_reviews.csv                     # LLM-tagged dataset
│   └── analysis_output.json                   # Aggregated statistics consumed by dashboard
├── pipeline/                   # Modular Python pipeline
│   ├── collect_reviews.py      # Step 1: Incremental Play Store scraper
│   ├── tag_reviews.py          # Step 2: Gemini batch tagging engine
│   ├── analyze_reviews.py      # Step 3: Statistical metrics & drag ranker
│   ├── generate_memo.py        # Step 4: Executive memo builder
│   └── config.py               # Shared constants, paths & taxonomy
├── screenshots/                # High-resolution dashboard captures
├── .env.example                # Safe environment variable template
├── .gitignore                  # Git ignore rules (secrets, venvs, pycache)
├── RECOMMENDATION.md           # Executive recommendation memo for leadership
├── requirements.txt            # Python dependencies
└── run_pipeline.py             # Single CLI orchestrator
```

---

## 📄 Key Takeaways for Leadership

- **The Executive Memo:** Detailed root-cause explanations and a 30-60-90 day engineering execution plan can be found in [`RECOMMENDATION.md`](RECOMMENDATION.md).
- **The Dashboard:** Live interactive charts, tab comparisons, and upvoted reviews can be explored in the [`dashboard/`](dashboard/) application.
- **Repeatability:** Every time a new version is released, running `python run_pipeline.py` immediately tracks whether user sentiment improved or regressed.

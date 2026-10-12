# MoveInSync — Play Store Review Intelligence

An automated intelligence pipeline and interactive analytics dashboard designed for Forward Deployed Engineering (FDE) at **MoveInSync**. 

This system ingests Play Store reviews across both the **MoveInSync Employee App** (`com.moveinsync.ets`) and the **Driver Partner App** (`com.moveinsync.driver.dco`), analyzes sentiment, maps user complaints to critical commute journey stages, computes weighted rating drag, and produces prioritized, actionable product recommendations alongside an executive strategy memo (`RECOMMENDATION.md`).

---

## 📸 Dashboard Preview

### 1. Employee App Intelligence
![Employee App Dashboard](screenshots/employee_app_dashboard.png)

### 2. Cross-App Comparison & Combined Intelligence
![Combined View Dashboard](screenshots/combined_view_dashboard.png)

### 3. Driver App Intelligence
![Driver App Dashboard](screenshots/driver_app_dashboard.png)

### 4. Live Charts & Journey Impact View
![Dashboard Hero & Charts](screenshots/dashboard_hero_and_charts.png)

---

## 🚀 Key Capabilities

- **Automated Review Collection**: Scrapes historical and recent reviews with incremental sync to avoid duplicate ingestion.
- **LLM-Powered Journey Tagging**: Uses Google Gemini (`gemini-2.5-flash-lite` / `gemini-2.0-flash`) in high-throughput JSON batches to tag reviews against:
  - **Issue Categories**: App crash/freeze, booking failures, wrong assignments, tracking inaccuracies, driver behaviour, safety concerns, notification issues, UI/UX regressions, etc.
  - **Commute Journey Stages**: Booking, Assignment, Pickup & Tracking, Ride Experience, Dropoff, Issue Resolution, App General.
- **Weighted Rating Drag Prioritization**: Ranks issues using weighted drag:
  $$\text{Drag} = \frac{\text{Issue Volume}}{\text{Total Reviews}} \times (\text{Overall Avg} - \text{Issue Avg})$$
- **Automated Strategic Memo**: Synthesizes findings into `RECOMMENDATION.md` structured for product managers and engineering leads.
- **Interactive Dark-Mode Dashboard**: Fast, responsive frontend powered by Chart.js featuring rating trends, doughnut star distribution, journey stage breakdowns, and developer response analytics.

---

## 🛠️ Project Structure

```text
moveinsync/
├── dashboard/               # Frontend interactive dashboard
│   ├── index.html           # Dashboard HTML shell
│   ├── styles.css           # Premium dark-mode design system & animations
│   └── app.js               # Reactive state, Chart.js visualizations & tab handling
├── data/                    # Review datasets & analysis artifacts
│   ├── reviews_com.moveinsync.ets.csv         # Raw employee reviews
│   ├── reviews_com.moveinsync.driver.dco.csv  # Raw driver reviews
│   ├── tagged_reviews.csv                     # LLM-categorized reviews
│   └── analysis_output.json                   # Aggregated metrics consumed by dashboard
├── pipeline/                # Python pipeline modules
│   ├── collect_reviews.py   # Scraper using google-play-scraper
│   ├── tag_reviews.py       # Gemini batch tagging engine
│   ├── analyze_reviews.py   # Statistical analysis & ranking calculation
│   ├── generate_memo.py     # Markdown memo generator
│   └── config.py            # Taxonomy, thresholds & configuration
├── screenshots/             # High-resolution dashboard captures
├── .env.example             # Template for API keys
├── .gitignore               # Ignored secrets, virtual environments & caches
├── RECOMMENDATION.md        # Generated strategic recommendation memo
├── requirements.txt         # Python dependencies
└── run_pipeline.py          # Unified CLI orchestrator
```

---

## ⚡ Quickstart

### 1. Clone & Setup Environment
```bash
git clone https://github.com/Anurag-Basuri/moveinsync.git
cd moveinsync
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Gemini API Key
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Edit `.env` and add your API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Run Pipeline
```bash
# Run the complete end-to-end pipeline
python run_pipeline.py

# Or skip review scraping to analyze existing dataset with a tag limit:
python run_pipeline.py --skip-collect --limit 100
```

### 4. Launch the Dashboard
```bash
python run_pipeline.py --serve
```
Open [http://localhost:8000/dashboard/index.html](http://localhost:8000/dashboard/index.html) in your browser.

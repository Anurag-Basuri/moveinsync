# Analyzes tagged reviews, quantifies rating drag, and prepares dashboard data
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pipeline.config import DATA


# Load tagged reviews from CSV and convert numeric fields
def load_tagged():
    path = DATA / "tagged_reviews.csv"
    if not path.exists():
        sys.exit(f"Missing {path}. Run: python -m pipeline.tag_reviews")
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["rating"] = int(r["rating"]) if r.get("rating") else 0
        r["thumbs_up"] = int(r["thumbs_up"]) if r.get("thumbs_up") else 0
    return rows


# Load store rating snapshots if available
def load_snapshots():
    path = DATA / "snapshots.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# Calculate how much each issue type pulls down the overall rating
def rating_impact(rows):
    overall_avg = sum(r["rating"] for r in rows) / max(len(rows), 1)
    by_issue = defaultdict(list)
    for r in rows:
        by_issue[r.get("issue_type", "other")].append(r["rating"])

    results = {}
    total = len(rows)
    for issue, ratings in by_issue.items():
        avg = sum(ratings) / len(ratings)
        gap = overall_avg - avg
        share = len(ratings) / total
        results[issue] = {
            "count": len(ratings),
            "avg_rating": round(avg, 2),
            "rating_gap": round(gap, 2),
            "share_pct": round(share * 100, 1),
            "weighted_drag": round(gap * share, 3),
        }
    return results, overall_avg


# Group reviews by commute journey stage and check sentiment distributions
def journey_breakdown(rows):
    by_stage = defaultdict(list)
    for r in rows:
        by_stage[r.get("journey_stage", "other")].append(r)

    results = {}
    for stage, stage_rows in by_stage.items():
        ratings = [r["rating"] for r in stage_rows]
        sentiments = Counter(r.get("sentiment", "neutral") for r in stage_rows)
        neg = sentiments.get("very_negative", 0) + sentiments.get("negative", 0)
        results[stage] = {
            "count": len(stage_rows),
            "avg_rating": round(sum(ratings) / max(len(ratings), 1), 2),
            "negative_pct": round(neg / max(len(stage_rows), 1) * 100, 1),
            "sentiment_dist": dict(sentiments),
        }
    return results


# Aggregate monthly rating averages and star counts
def time_trends(rows):
    by_month = defaultdict(list)
    for r in rows:
        d = r.get("review_date", "")
        if not d:
            continue
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            by_month[dt.strftime("%Y-%m")].append(r["rating"])
        except (ValueError, AttributeError):
            continue

    return {
        k: {
            "count": len(v),
            "avg_rating": round(sum(v) / len(v), 2),
            "star_dist": dict(Counter(v)),
        }
        for k, v in sorted(by_month.items())
    }


# Track how issue volumes shift month by month
def issue_trends(rows):
    by_month_issue = defaultdict(lambda: defaultdict(int))
    for r in rows:
        d = r.get("review_date", "")
        if not d:
            continue
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            by_month_issue[dt.strftime("%Y-%m")][r.get("issue_type", "other")] += 1
        except (ValueError, AttributeError):
            continue
    return {m: dict(v) for m, v in sorted(by_month_issue.items())}


# Find the most upvoted reviews to surface what users care about most
def top_reviews(rows, n=10):
    return [
        {
            "text": r.get("text", "")[:200],
            "rating": r["rating"],
            "thumbs_up": r["thumbs_up"],
            "issue_type": r.get("issue_type", ""),
            "journey_stage": r.get("journey_stage", ""),
            "review_date": r.get("review_date", ""),
            "app_id": r.get("app_id", ""),
        }
        for r in sorted(rows, key=lambda r: r["thumbs_up"], reverse=True)[:n]
    ]


# Check developer reply rate and rating differences
def dev_reply_analysis(rows):
    with_reply = [r for r in rows if r.get("dev_reply", "").strip()]
    without_reply = [r for r in rows if not r.get("dev_reply", "").strip()]
    return {
        "replied_count": len(with_reply),
        "unreplied_count": len(without_reply),
        "reply_rate_pct": round(len(with_reply) / max(len(rows), 1) * 100, 1),
        "replied_avg_rating": round(
            sum(r["rating"] for r in with_reply) / max(len(with_reply), 1), 2
        ),
        "unreplied_avg_rating": round(
            sum(r["rating"] for r in without_reply) / max(len(without_reply), 1), 2
        ),
    }


# Spot versions that triggered a wave of negative reviews
def version_analysis(rows):
    by_version = defaultdict(list)
    for r in rows:
        v = r.get("app_version", "").strip()
        if v:
            by_version[v].append(r["rating"])

    return {
        v: {
            "count": len(ratings),
            "avg_rating": round(sum(ratings) / len(ratings), 2),
            "star_dist": dict(Counter(ratings)),
        }
        for v, ratings in by_version.items() if len(ratings) >= 3
    }


# Rank issues by weighted rating drag to prioritize fixes
def prioritized_recommendations(impact_data, app_label):
    recs = []
    for issue, data in impact_data.items():
        if issue in ("positive_feedback", "other", "feature_request"):
            continue
        if data["weighted_drag"] <= 0:
            continue
        recs.append({
            "issue": issue,
            "priority_score": round(data["weighted_drag"] * 1000 + data["count"] * 0.1, 1),
            "count": data["count"],
            "avg_rating": data["avg_rating"],
            "weighted_drag": data["weighted_drag"],
            "share_pct": data["share_pct"],
            "app": app_label,
        })
    recs.sort(key=lambda x: x["priority_score"], reverse=True)
    for i, r in enumerate(recs):
        r["rank"] = i + 1
    return recs


# Run all analysis cuts for a single app
def analyze_app(rows, app_id, app_label):
    impact, overall_avg = rating_impact(rows)
    return {
        "app_id": app_id,
        "app_label": app_label,
        "total_reviews": len(rows),
        "overall_avg_rating": round(overall_avg, 2),
        "rating_impact_by_issue": impact,
        "journey_breakdown": journey_breakdown(rows),
        "monthly_trends": time_trends(rows),
        "issue_trends": issue_trends(rows),
        "top_reviews": top_reviews(rows),
        "dev_reply_stats": dev_reply_analysis(rows),
        "version_analysis": version_analysis(rows),
        "prioritized_recommendations": prioritized_recommendations(impact, app_label),
    }


# Main analysis runner that writes out analysis_output.json
def main():
    tagged = load_tagged()
    snapshots = load_snapshots()

    employee_rows = [r for r in tagged if "driver" not in r.get("app_id", "").lower()]
    driver_rows = [r for r in tagged if "driver" in r.get("app_id", "").lower()]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_reviews": len(tagged),
        "apps": {},
        "snapshots": snapshots,
    }

    if employee_rows:
        output["apps"]["employee"] = analyze_app(
            employee_rows, "com.moveinsync.ets", "Employee App"
        )
    if driver_rows:
        output["apps"]["driver"] = analyze_app(
            driver_rows, "com.moveinsync.driver.dco", "Driver App"
        )

    all_recs = []
    for app_data in output["apps"].values():
        all_recs.extend(app_data["prioritized_recommendations"])
    all_recs.sort(key=lambda x: x["priority_score"], reverse=True)
    for i, r in enumerate(all_recs):
        r["overall_rank"] = i + 1
    output["combined_recommendations"] = all_recs

    out_path = DATA / "analysis_output.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Analysis saved -> {out_path}")
    print(f"  {len(tagged)} reviews analyzed, {len(all_recs)} recommendations ranked")


if __name__ == "__main__":
    main()

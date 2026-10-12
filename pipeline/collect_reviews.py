# Scrapes public Play Store reviews and saves rating snapshots
import argparse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from google_play_scraper import Sort
from google_play_scraper import app as gp_app
from google_play_scraper import reviews as gp_reviews
from google_play_scraper import search as gp_search

from pipeline.config import APPS, DATA, REVIEW_FIELDS, SNAPSHOT_FIELDS


# Search the Play Store for candidate MoveInSync apps
def discover(country, lang):
    seen = set()
    for query in ("MoveInSync", "MoveInSync driver", "MoveInSync One"):
        for result in gp_search(query, n_hits=15, lang=lang, country=country):
            app_id = result.get("appId") or ""
            if not app_id or app_id in seen:
                continue
            seen.add(app_id)
            title = (result.get("title") or "")[:40]
            dev = (result.get("developer") or "")[:25]
            score = result.get("score") or "?"
            print(f"{str(app_id):<45} {str(title):<40} {str(dev):<25}  {score}")


# Paginate through Play Store reviews until we hit reviews we already have
def fetch_reviews(app_id, lang, country, known_ids, page_size=200, pause=1.0):
    new_reviews = []
    continuation_token = None
    page = 0

    while True:
        # Retry with exponential backoff if the network or API hiccups
        for attempt in range(4):
            try:
                batch, continuation_token = gp_reviews(
                    app_id,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=page_size,
                    continuation_token=continuation_token,
                )
                break
            except Exception as e:
                wait_time = 2 ** attempt * 2
                print(f"  retry {attempt + 1}/4 in {wait_time}s ({type(e).__name__})")
                time.sleep(wait_time)
        else:
            print("  giving up after retries; saving what we collected so far")
            return new_reviews

        if not batch:
            return new_reviews

        page += 1
        fresh = [r for r in batch if r["reviewId"] not in known_ids]
        new_reviews.extend(fresh)
        print(f"  page {page}: {len(batch)} fetched, {len(fresh)} new, {len(new_reviews)} total new")

        # Stop early if all reviews on this page are already known
        if known_ids and not fresh:
            return new_reviews

        # Stop when there are no more pages
        if continuation_token is None:
            return new_reviews

        time.sleep(pause)


# Format a raw review into our CSV structure
def to_row(app_id, review, timestamp):
    review_date = review["at"].isoformat() if review.get("at") else ""
    reply_date = review["repliedAt"].isoformat() if review.get("repliedAt") else ""

    return {
        "app_id": app_id,
        "review_id": review["reviewId"],
        "rating": review["score"],
        "text": (review.get("content") or "").replace("\r", " "),
        "thumbs_up": review.get("thumbsUpCount", 0),
        "app_version": review.get("appVersion") or review.get("reviewCreatedVersion") or "",
        "review_date": review_date,
        "dev_reply": (review.get("replyContent") or "").replace("\r", " "),
        "dev_reply_date": reply_date,
        "collected_at": timestamp,
    }


# Read a CSV file into a list of row dicts
def load_csv(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# Write rows out to a CSV file with the given header columns
def save_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


# Save current store metrics like star rating and review count
def snapshot(app_id, lang, country, timestamp):
    meta = gp_app(app_id, lang=lang, country=country)
    histogram = (meta.get("histogram") or [0] * 5) + [0] * 5
    row = {
        "collected_at": timestamp,
        "app_id": app_id,
        "title": meta.get("title"),
        "score": meta.get("score"),
        "ratings": meta.get("ratings"),
        "reviews": meta.get("reviews"),
        "star1": histogram[0],
        "star2": histogram[1],
        "star3": histogram[2],
        "star4": histogram[3],
        "star5": histogram[4],
        "version": meta.get("version"),
        "updated": meta.get("updated"),
    }
    snapshot_path = DATA / "snapshots.csv"
    existing_rows = load_csv(snapshot_path)
    save_csv(snapshot_path, existing_rows + [row], SNAPSHOT_FIELDS)
    print(f"  store: {meta.get('score'):.2f} stars, {meta.get('ratings')} ratings, {meta.get('reviews')} reviews")
    return meta


# Run review collection from the command line
def main():
    parser = argparse.ArgumentParser(description="Collect MoveInSync Play Store reviews")
    parser.add_argument("--discover", action="store_true", help="Search for MoveInSync apps")
    parser.add_argument("--apps", nargs="+", default=APPS, help="Package IDs to scrape")
    parser.add_argument("--country", default="in")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--full", action="store_true", help="Ignore saved data and re-fetch everything")
    args = parser.parse_args()

    if args.discover:
        return discover(args.country, args.lang)

    DATA.mkdir(exist_ok=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for app_id in args.apps:
        print(f"\n== {app_id} ==")
        csv_path = DATA / f"reviews_{app_id}.csv"
        existing = [] if args.full else load_csv(csv_path)
        known_ids = {r["review_id"] for r in existing}
        meta = snapshot(app_id, args.lang, args.country, now)
        fresh_raw = fetch_reviews(app_id, args.lang, args.country, known_ids)
        fresh_rows = [to_row(app_id, r, now) for r in fresh_raw]
        merged = sorted(fresh_rows + existing, key=lambda r: r["review_date"], reverse=True)
        save_csv(csv_path, merged, REVIEW_FIELDS)
        print(f"  saved {len(merged)} reviews ({len(fresh_rows)} new) -> {csv_path}")
        total = meta.get("reviews") or 0
        if total:
            coverage = 100 * len(merged) / total
            print(f"  coverage: {len(merged)} of ~{total} ({coverage:.0f}%)")


if __name__ == "__main__":
    main()

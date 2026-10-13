# Tag reviews with journey stage, issue type, and sentiment using Gemini
import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from google import genai

from pipeline.config import (
    DATA, ISSUE_TYPES, JOURNEY_STAGES, SENTIMENTS, TAGGED_FIELDS, load_api_key,
)

# Prompt giving Gemini context about MoveInSync and our taxonomy
PROMPT_TEMPLATE = """You are a product analyst for MoveInSync, an employee transportation management app.

Analyze each review and tag it with:
1. **journey_stage**: Which stage of the employee commute journey does this review primarily relate to?
   Options: {stages}

2. **issue_type**: What specific issue (if any) is the reviewer describing?
   Options: {issues}

3. **sentiment**: Overall sentiment of the review.
   Options: {sentiments}

4. **summary**: A 5-10 word summary of what the reviewer is saying.

IMPORTANT CONTEXT:
- MoveInSync handles employee cab/shuttle transport for corporates
- "Self-booking" is the primary flow: employee books their own ride based on shift
- The journey is: booking → assignment → pickup/tracking → safety checks → ride → dropoff → issue resolution
- The driver app is used by cab/shuttle drivers assigned through MoveInSync

For DRIVER APP reviews, adapt the journey stages:
- "booking" → trip/job assignment from driver's perspective
- "pickup_tracking" → navigation to pickup, finding passenger
- "safety" → OTP collection, verification from driver side
- "ride_experience" → during the trip
- "dropoff" → completing the trip
- "issue_resolution" → driver raising issues, contacting support
- For driver onboarding, document upload, registration, or vehicle attachment issues, tag as issue_type: "driver_onboarding" and journey_stage: "app_general" or "issue_resolution".

Respond ONLY with a JSON array. Each element must have:
{{"review_id": "...", "journey_stage": "...", "issue_type": "...", "sentiment": "...", "summary": "..."}}

Reviews to analyze:
{reviews}
"""


# Read all raw review CSV files from the data folder
def load_reviews():
    all_rows = []
    for path in sorted(DATA.glob("reviews_*.csv")):
        with path.open(encoding="utf-8", newline="") as f:
            all_rows.extend(list(csv.DictReader(f)))
    return all_rows


# Load already tagged reviews so we can skip them
def load_tagged():
    path = DATA / "tagged_reviews.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        return {r["review_id"]: r for r in csv.DictReader(f)}


# Save all tagged reviews to CSV
def save_tagged(rows):
    path = DATA / "tagged_reviews.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=TAGGED_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  saved {len(rows)} tagged reviews -> {path}")


# Format a batch of reviews into the LLM prompt
def build_prompt(batch):
    formatted_reviews = []
    for r in batch:
        text = r.get("text", "").strip() or "(no text, rating only)"
        app_label = "DRIVER APP" if "driver" in r["app_id"].lower() else "EMPLOYEE APP"
        formatted_reviews.append(f'ID: {r["review_id"]} | App: {app_label} | Rating: {r["rating"]}/5\n"{text}"')

    return PROMPT_TEMPLATE.format(
        stages=", ".join(JOURNEY_STAGES),
        issues=", ".join(ISSUE_TYPES),
        sentiments=", ".join(SENTIMENTS),
        reviews="\n\n".join(formatted_reviews),
    )


# Extract JSON array from Gemini's response, stripping markdown fences if present
def parse_response(text):
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return None


# Send a batch to Gemini and retry if we hit rate limits or glitches
def tag_batch(client, model_name, batch, max_retries=3):
    prompt = build_prompt(batch)
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            parsed = parse_response(response.text)
            if parsed and isinstance(parsed, list):
                return parsed
            print(f"  could not parse response on attempt {attempt + 1}, retrying...")
        except Exception as e:
            wait_time = 2 ** attempt * 3
            print(f"  retry {attempt + 1}/{max_retries} in {wait_time}s ({type(e).__name__}: {e})")
            time.sleep(wait_time)
    return None


# Main tagging workflow
def main():
    parser = argparse.ArgumentParser(description="Tag reviews using Gemini")
    parser.add_argument("--retag", action="store_true", help="Re-tag all reviews from scratch")
    parser.add_argument("--batch-size", type=int, default=15, help="Reviews per API call")
    parser.add_argument("--limit", type=int, default=0, help="Max reviews to tag (0 for all)")
    parser.add_argument("--sample-per-month", type=int, default=0, help="Sample N reviews per month across recent history")
    parser.add_argument("--months-back", type=int, default=12, help="Number of recent months to sample from")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Gemini model name")
    args = parser.parse_args()

    api_key = load_api_key()
    if not api_key:
        sys.exit(
            "Gemini API key not found.\n"
            "  Option 1: Create a .env file in the project root with GEMINI_API_KEY=your-key\n"
            "  Option 2: Set the environment variable: $env:GEMINI_API_KEY = 'your-key'"
        )

    client = genai.Client(api_key=api_key)
    model_name = args.model

    raw_reviews = load_reviews()
    print(f"Loaded {len(raw_reviews)} total reviews from data/")

    already_tagged = {} if args.retag else load_tagged()
    
    if args.sample_per_month > 0:
        # Sample across multiple recent months for rich time-series trends
        driver_reviews = [r for r in raw_reviews if "driver" in r.get("app_id", "").lower()]
        emp_reviews = [r for r in raw_reviews if "driver" not in r.get("app_id", "").lower()]
        
        # Group employee reviews by month
        from collections import defaultdict
        by_month = defaultdict(list)
        for r in emp_reviews:
            d = r.get("review_date", "")[:7]
            if d:
                by_month[d].append(r)
        
        recent_months = sorted(by_month.keys())[-args.months_back:]
        sampled = []
        for m in recent_months:
            m_reviews = by_month[m]
            # Prioritize reviews with meaningful text
            with_text = [r for r in m_reviews if len(r.get("text", "").strip()) >= 15]
            without_text = [r for r in m_reviews if len(r.get("text", "").strip()) < 15]
            
            # Sort with_text to ensure diverse star ratings
            by_star = defaultdict(list)
            for r in with_text:
                by_star[r.get("rating", "3")].append(r)
            
            star_sample = []
            # Round-robin pick across star ratings (1, 2, 3, 4, 5)
            stars = ["1", "2", "3", "4", "5"]
            idx = 0
            while len(star_sample) < args.sample_per_month and any(by_star.values()):
                st = stars[idx % len(stars)]
                if by_star[st]:
                    star_sample.append(by_star[st].pop(0))
                idx += 1
                if idx > 100:  # safety
                    break
            
            # If still need more to hit target, fill from remaining
            if len(star_sample) < args.sample_per_month:
                remaining = with_text + without_text
                for r in remaining:
                    if r not in star_sample:
                        star_sample.append(r)
                    if len(star_sample) >= args.sample_per_month:
                        break
            sampled.extend(star_sample)
            
        # Combine all driver reviews + sampled employee reviews
        combined = driver_reviews + sampled
        to_tag = [r for r in combined if r["review_id"] not in already_tagged]
    else:
        to_tag = [r for r in raw_reviews if r["review_id"] not in already_tagged]
        if args.limit > 0:
            to_tag = to_tag[:args.limit]
            
    print(f"  {len(already_tagged)} already tagged, {len(to_tag)} to tag")

    if not to_tag:
        print("Nothing to tag. Use --retag to re-tag everything.")
        return

    tagged_map = dict(already_tagged)
    batch_size = args.batch_size
    total_batches = (len(to_tag) + batch_size - 1) // batch_size

    for i in range(0, len(to_tag), batch_size):
        batch = to_tag[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"\n  batch {batch_num}/{total_batches} ({len(batch)} reviews)...")

        results = tag_batch(client, model_name, batch)
        if not results:
            print(f"  batch {batch_num} failed, skipping")
            continue

        result_map = {r["review_id"]: r for r in results}
        for rev in batch:
            rid = rev["review_id"]
            tag = result_map.get(rid, {})
            tagged_row = dict(rev)
            tagged_row["journey_stage"] = tag.get("journey_stage", "other")
            tagged_row["issue_type"] = tag.get("issue_type", "other")
            tagged_row["sentiment"] = tag.get("sentiment", "neutral")
            tagged_row["summary"] = tag.get("summary", "")

            # Fall back to safe defaults if taxonomy tags don't match
            if tagged_row["journey_stage"] not in JOURNEY_STAGES:
                tagged_row["journey_stage"] = "other"
            if tagged_row["issue_type"] not in ISSUE_TYPES:
                tagged_row["issue_type"] = "other"
            if tagged_row["sentiment"] not in SENTIMENTS:
                tagged_row["sentiment"] = "neutral"

            tagged_map[rid] = tagged_row

        matched = sum(1 for rev in batch if rev["review_id"] in result_map)
        print(f"  {matched}/{len(batch)} tagged successfully")

        # Save after every batch so progress is never lost
        save_tagged(list(tagged_map.values()))
        time.sleep(1)

    print(f"\nDone. {len(tagged_map)} total tagged reviews saved.")


if __name__ == "__main__":
    main()

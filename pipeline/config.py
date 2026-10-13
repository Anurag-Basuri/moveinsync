# Central config for paths, app IDs, and taxonomy
import os
from pathlib import Path

# Base directory paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA = PROJECT_ROOT / "data"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

# Target app package IDs
APPS = [
    "com.moveinsync.ets",            # Employee app
    "com.moveinsync.driver.dco",     # Driver partner app
]

# CSV schema fields
REVIEW_FIELDS = [
    "app_id", "review_id", "rating", "text", "thumbs_up", "app_version",
    "review_date", "dev_reply", "dev_reply_date", "collected_at",
]

SNAPSHOT_FIELDS = [
    "collected_at", "app_id", "title", "score", "ratings", "reviews",
    "star1", "star2", "star3", "star4", "star5", "version", "updated",
]

TAGGED_FIELDS = REVIEW_FIELDS + ["journey_stage", "issue_type", "sentiment", "summary"]

# Commute journey stages from the case study
JOURNEY_STAGES = [
    "booking",
    "assignment",
    "pickup_tracking",
    "safety",
    "ride_experience",
    "dropoff",
    "issue_resolution",
    "app_general",
    "other",
]

# Issue categories
ISSUE_TYPES = [
    "app_crash_freeze",
    "login_auth",
    "booking_failure",
    "wrong_assignment",
    "tracking_inaccurate",
    "driver_behaviour",
    "safety_concern",
    "late_pickup",
    "notification_issue",
    "ui_ux_poor",
    "performance_slow",
    "update_regression",
    "feature_request",
    "billing_payment",
    "driver_onboarding",
    "positive_feedback",
    "other",
]

# Sentiment scale
SENTIMENTS = ["very_negative", "negative", "neutral", "positive", "very_positive"]


# Look for GEMINI_API_KEY in environment, .env, or .env.example
def load_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        return key

    for filename in (".env", ".env.example"):
        env_file = PROJECT_ROOT / filename
        if not env_file.exists():
            continue
        with env_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k == "GEMINI_API_KEY" and v and not v.startswith("your_"):
                    os.environ["GEMINI_API_KEY"] = v
                    return v
    return None


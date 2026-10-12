# One-command runner for the MoveInSync analysis pipeline
import argparse
import http.server
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

# Add project root to path so pipeline package can be imported
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
from pipeline.config import load_api_key


# Run a shell command for a pipeline step and log progress
def run_step(cmd, desc):
    print(f"\n{'=' * 60}")
    print(f"  {desc}")
    print(f"{'=' * 60}\n")
    result = subprocess.run(cmd, shell=True, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print(f"\n  [!] {desc} exited with code {result.returncode}")
    return result.returncode


# Start a simple local HTTP server so the dashboard can fetch data JSON
def serve_dashboard(port=8000):
    handler = http.server.SimpleHTTPRequestHandler
    httpd = http.server.HTTPServer(("localhost", port), handler)
    url = f"http://localhost:{port}/dashboard/index.html"
    print(f"\n  Dashboard running at: {url}")
    print("  Press Ctrl+C to stop.\n")
    webbrowser.open(url)
    httpd.serve_forever()


# Parse command-line flags and orchestrate each pipeline step
def main():
    parser = argparse.ArgumentParser(description="MoveInSync Play Store Review Pipeline")
    parser.add_argument("--full", action="store_true", help="Re-fetch and re-tag all reviews from scratch")
    parser.add_argument("--skip-collect", action="store_true", help="Skip review collection")
    parser.add_argument("--skip-tag", action="store_true", help="Skip LLM tagging step")
    parser.add_argument("--skip-analyze", action="store_true", help="Skip analysis step")
    parser.add_argument("--skip-memo", action="store_true", help="Skip memo generation")
    parser.add_argument("--limit", type=int, default=0, help="Max reviews to tag (e.g. 50 or 100 for testing)")
    parser.add_argument("--serve", action="store_true", help="Just open and serve the dashboard")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--port", type=int, default=8000, help="Local server port")
    args = parser.parse_args()

    # If the user only wants to view the dashboard
    if args.serve:
        os.chdir(str(PROJECT_ROOT))
        serve_dashboard(args.port)
        return

    # Check for API key before running the tagging step
    if not args.skip_tag:
        key = load_api_key()
        if not key:
            print("\n  [!] Gemini API key not found!")
            print("  Create a .env file:  copy .env.example .env")
            print("  Then edit .env and paste your key.\n")
            sys.exit(1)

    full_flag = "--full" if args.full else ""
    retag_flag = "--retag" if args.full else ""
    limit_flag = f"--limit {args.limit}" if args.limit > 0 else ""

    # Step 1: Scrape reviews from the Play Store
    if not args.skip_collect:
        run_step(
            f"python -m pipeline.collect_reviews {full_flag}",
            "Step 1/4: Collecting Play Store reviews",
        )

    # Step 2: Tag reviews with Gemini
    if not args.skip_tag:
        run_step(
            f"python -m pipeline.tag_reviews {retag_flag} {limit_flag}".strip(),
            "Step 2/4: Tagging reviews with Gemini",
        )

    # Step 3: Run quantitative impact analysis
    if not args.skip_analyze:
        run_step(
            "python -m pipeline.analyze_reviews",
            "Step 3/4: Analyzing and generating insights",
        )

    # Step 4: Generate executive recommendation memo
    if not args.skip_memo:
        run_step(
            "python -m pipeline.generate_memo",
            "Step 4/4: Generating recommendation memo",
        )

    print(f"\n{'=' * 60}")
    print("  Pipeline finished successfully!")
    print(f"{'=' * 60}\n")
    print("  Artifacts:")
    print("    Recommendation:  RECOMMENDATION.md")
    print("    Dashboard:       dashboard/index.html")
    print("    Data folder:     data/")
    print("    Analysis JSON:   data/analysis_output.json\n")

    # Start dashboard server and open in browser
    if not args.no_open:
        os.chdir(str(PROJECT_ROOT))
        serve_dashboard(args.port)


if __name__ == "__main__":
    main()

import os
import sys
import json
import time
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://www.sarkariresult.com/latestjob/"
SENT_JOBS_FILE = "sent_jobs.json"
MAX_HISTORY = 10000  # Large enough to hold all active and archive jobs (~4000 items = ~250KB)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
    "Referer": "https://www.sarkariresult.com/",
}


def load_sent_jobs():
    """Load previously notified job URLs from sent_jobs.json."""
    if not os.path.exists(SENT_JOBS_FILE):
        return []
    try:
        with open(SENT_JOBS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"[WARN] Error reading {SENT_JOBS_FILE}: {e}. Starting fresh.")
        return []


def save_sent_jobs(jobs_list):
    """Save notified job URLs back to sent_jobs.json, keeping the latest MAX_HISTORY."""
    recent_jobs = jobs_list[-MAX_HISTORY:]
    with open(SENT_JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(recent_jobs, f, indent=2, ensure_ascii=False)


def fetch_latest_jobs():
    """Scrape job postings from Sarkari Result latest jobs page."""
    print(f"[INFO] Fetching {TARGET_URL}...")
    try:
        response = requests.get(TARGET_URL, headers=HEADERS, timeout=25)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Failed to fetch page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    seen_urls_in_page = set()

    # Sarkari Result's primary job lists are inside .entry-content or #post
    container = (
        soup.find("div", class_="entry-content")
        or soup.find("div", id="post")
        or soup.find("div", class_="post")
        or soup
    )

    # Extract all lists inside the content area
    for ul in container.find_all("ul"):
        for li in ul.find_all("li"):
            a_tag = li.find("a")
            if not a_tag:
                continue

            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "").strip()

            if not title or not href:
                continue

            full_url = urljoin(TARGET_URL, href)

            # Ignore generic navigation or non-job links
            if (
                len(title) < 8
                or full_url.rstrip("/").endswith("/latestjob")
                or full_url.startswith("javascript:")
                or full_url.endswith("#")
            ):
                continue

            # Avoid duplicates on the same page
            if full_url in seen_urls_in_page:
                continue
            seen_urls_in_page.add(full_url)

            jobs.append({
                "title": title,
                "url": full_url
            })

    print(f"[INFO] Found {len(jobs)} total jobs on Sarkari Result.")
    return jobs


def send_discord_webhook(webhook_url, payload):
    """Send payload to Discord with retry logic."""
    for attempt in range(3):
        try:
            resp = requests.post(webhook_url, json=payload, timeout=15)
            if resp.status_code == 429:
                retry_after = resp.json().get("retry_after", 2)
                print(f"[WARN] Rate limited by Discord. Waiting {retry_after}s...")
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[ERROR] Discord post error (attempt {attempt + 1}): {e}")
            time.sleep(2)
    return False


def notify_new_job(webhook_url, job):
    """Format and send a single job notification embed to Discord."""
    embed = {
        "title": f"📢 {job['title']}",
        "url": job["url"],
        "description": "A new government job notification has been published on **Sarkari Result**.",
        "color": 0x2ECC71,  # Emerald Green
        "fields": [
            {
                "name": "🔗 Apply / Official Details",
                "value": f"[Click here to view notification]({job['url']})",
                "inline": False,
            }
        ],
        "footer": {
            "text": "Sarkari Result Alerts • Automated Bot"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = {
        "username": "Sarkari Job Alerts",
        "avatar_url": "https://www.sarkariresult.com/favicon.ico",
        "embeds": [embed]
    }

    return send_discord_webhook(webhook_url, payload)


def send_initialization_ping(webhook_url, total_existing):
    """Notify the user on Discord when the bot is first initialized."""
    embed = {
        "title": "🟢 Sarkari Result Alert Bot Activated!",
        "description": (
            "The bot has successfully connected to this channel.\n\n"
            f"• **Current baseline**: `{total_existing}` existing jobs recorded.\n"
            "• **Status**: Active & monitoring.\n"
            "• **Next**: You will receive notifications here whenever a brand new job is posted!"
        ),
        "color": 0x3498DB,  # Sky Blue
        "footer": {
            "text": "Sarkari Result Alerts"
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    payload = {
        "username": "Sarkari Job Alerts",
        "avatar_url": "https://www.sarkariresult.com/favicon.ico",
        "embeds": [embed]
    }
    send_discord_webhook(webhook_url, payload)


def main():
    webhook_url = (
        os.environ.get("DISCORD_BOT_TOKEN", "").strip()
        or os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    )

    # Fallback to local .env file if available
    if not webhook_url and os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("DISCORD_BOT_TOKEN=") or line.startswith("DISCORD_WEBHOOK_URL="):
                        webhook_url = line.split("=", 1)[1].strip("'\" ")
                        break
        except Exception as e:
            print(f"[WARN] Failed to read .env file: {e}")

    if not webhook_url:
        print("[ERROR] DISCORD_BOT_TOKEN / DISCORD_WEBHOOK_URL is not set!")
        sys.exit(1)

    sent_urls = load_sent_jobs()
    sent_urls_set = set(sent_urls)
    current_jobs = fetch_latest_jobs()

    if not current_jobs:
        print("[WARN] No jobs could be parsed from the website. Exiting.")
        return

    # COLD-START: If running for the very first time with empty history
    if not sent_urls:
        print("[INFO] First run detected. Seeding baseline database without spamming.")
        all_current_urls = [job["url"] for job in current_jobs]
        save_sent_jobs(all_current_urls)
        send_initialization_ping(webhook_url, len(all_current_urls))
        print("[INFO] Initial baseline established and Discord confirmed.")
        return

    # Find jobs that have never been sent before
    new_jobs = [job for job in current_jobs if job["url"] not in sent_urls_set]

    if not new_jobs:
        print("[INFO] No new jobs found. Everything is up-to-date!")
        return

    print(f"[INFO] Found {len(new_jobs)} NEW jobs! Sending Discord notifications...")

    # Limit to latest 10 per run to prevent burst rate limits
    new_jobs_to_send = new_jobs[:10]

    for job in new_jobs_to_send:
        print(f"[NOTIFY] Sending: {job['title']}")
        success = notify_new_job(webhook_url, job)
        if success:
            sent_urls.append(job["url"])
            sent_urls_set.add(job["url"])
        time.sleep(1.5)  # Respect Discord rate limits

    # Save the updated history back
    save_sent_jobs(sent_urls)
    print("[INFO] Sent jobs saved successfully.")


if __name__ == "__main__":
    main()

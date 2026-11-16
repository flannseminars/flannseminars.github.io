#!/usr/bin/env python3
"""Post a Discord reminder ~1 hour before each FLaNN talk.

Reads data/schedule.csv (the same file the website renders), so the site
stays the single source of truth. Meant to run hourly from GitHub Actions.

Env vars (set as repo secrets):
  DISCORD_WEBHOOK_URL  - Discord channel webhook
  ZOOM_URL             - standing Zoom link
"""
import csv
import os
import sys
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

import requests

CSV_PATH = os.environ.get("CSV_PATH", "data/schedule.csv")
ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
DEFAULT_TIME = time(11, 0)  # "every Monday at 11:00 AM (ET) unless specified"

# Post when the talk starts between 30 and 90 minutes from now.
# With an hourly cron this fires exactly once per talk as long as
# GitHub's scheduling delay stays under 30 minutes (it usually does).
WINDOW = (timedelta(minutes=30), timedelta(minutes=90))


def fmt_hour(dt: datetime) -> str:
    s = dt.strftime("%-I:%M %p").replace(":00", "")
    return s


def talk_start(row: dict) -> datetime | None:
    try:
        day = datetime.strptime(row["Date"].strip(), "%B %d, %Y").date()
    except ValueError:
        return None
    # Optional "Time" column (e.g. "2:00 PM") overrides the default.
    t = DEFAULT_TIME
    if row.get("Time", "").strip():
        t = datetime.strptime(row["Time"].strip(), "%I:%M %p").time()
    return datetime.combine(day, t, tzinfo=ET)


def message(row: dict, start: datetime) -> str:
    presenter = " ".join(row["Presenter"].split())
    title = " ".join(row["Topic"].split())  # CSV titles can contain newlines
    local = fmt_hour(start)
    tz = start.strftime("%Z")  # EST or EDT
    gmt = fmt_hour(start.astimezone(UTC))
    lines = [
        f'Today, we will have {presenter} presenting "{title}"! '
        f"See you in an hour at {local} {tz} ({gmt} GMT)!",
        "",
        f"Zoom: {os.environ['ZOOM_URL']}",
    ]
    if row.get("URL", "").strip():
        lines.append(f"Paper link: {row['URL'].strip()}")
    return "\n".join(lines)


def main() -> None:
    now = datetime.now(UTC)
    dry_run = "--dry-run" in sys.argv
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row.get("Presenter", "").strip() or not row.get("Topic", "").strip():
                continue  # empty placeholder weeks
            start = talk_start(row)
            if start is None:
                continue
            if WINDOW[0] < start - now <= WINDOW[1]:
                text = message(row, start)
                if dry_run:
                    print(text)
                    continue
                r = requests.post(os.environ["DISCORD_WEBHOOK_URL"], json={"content": text})
                r.raise_for_status()
                print("Posted:", row["Topic"])


if __name__ == "__main__":
    main()

"""Scrape the public contribution calendar into data/contributions.json.

No token, no GraphQL: GitHub serves the calendar as plain HTML at
https://github.com/users/<username>/contributions - the same fragment the
profile page itself renders. Day counts live in the <tool-tip> elements that
reference each cell by id.

    python scripts/fetch_contributions.py [username]
"""

import datetime as dt
import json
import pathlib
import re
import sys
from collections import defaultdict

import requests
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"
URL = "https://github.com/users/{}/contributions"
UA = "Mozilla/5.0 (compatible; profile-art/1.0; +https://github.com/{})"


def fetch(username):
    r = requests.get(
        URL.format(username),
        headers={"User-Agent": UA.format(username), "Accept": "text/html"},
        timeout=30,
    )
    r.raise_for_status()
    return r.text


def parse(html):
    soup = BeautifulSoup(html, "html.parser")

    # tool-tip -> "4 contributions on March 3rd." / "No contributions on ..."
    counts = {}
    for tip in soup.select("tool-tip[for]"):
        text = tip.get_text(" ", strip=True)
        m = re.match(r"^(No|[\d,]+)\s+contribution", text)
        if m:
            counts[tip["for"]] = 0 if m.group(1) == "No" else int(m.group(1).replace(",", ""))

    days = []
    for cell in soup.select("td.ContributionCalendar-day[data-date]"):
        date = cell["data-date"]
        days.append(
            {
                "date": date,
                "level": int(cell.get("data-level", 0)),
                "count": counts.get(cell.get("id", ""), 0),
            }
        )
    days.sort(key=lambda d: d["date"])

    heading = soup.find(id="js-contribution-activity-description")
    total_text = heading.get_text(" ", strip=True) if heading else ""
    m = re.search(r"([\d,]+)\s+contributions?", total_text)
    total = int(m.group(1).replace(",", "")) if m else sum(d["count"] for d in days)

    return days, total


def streaks(days):
    """Current streak counts back from the last day that could still be active."""
    cur = longest = run = 0
    for day in days:
        run = run + 1 if day["count"] > 0 else 0
        longest = max(longest, run)

    today = dt.date.today().isoformat()
    for day in reversed(days):
        if day["date"] > today:          # calendar can run a few days ahead
            continue
        if day["count"] > 0:
            cur += 1
        elif cur or day["date"] != today:  # an empty today does not break it yet
            break
    return cur, longest


def main():
    username = sys.argv[1] if len(sys.argv) > 1 else json.loads(
        (ROOT / "config.json").read_text(encoding="utf-8")
    )["username"]

    days, total = parse(fetch(username))
    if not days:
        sys.exit("no day cells found - GitHub may have changed the markup")

    monthly = defaultdict(int)
    for day in days:
        monthly[day["date"][:7]] += day["count"]

    best = max(days, key=lambda d: d["count"])
    cur, longest = streaks(days)

    payload = {
        "username": username,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "total": total,
        "stats": {
            "current_streak": cur,
            "longest_streak": longest,
            "best_day": {"date": best["date"], "count": best["count"]},
            "active_days": sum(1 for d in days if d["count"] > 0),
            "monthly": dict(sorted(monthly.items())),
        },
        "days": days,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  {len(days)} days, {total} contributions, "
          f"streak {cur} (longest {longest})")


if __name__ == "__main__":
    main()

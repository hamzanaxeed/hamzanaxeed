
import json
import os
import urllib.request
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "hamzanaxeed"
TOKEN = os.environ["GH_STATS_TOKEN"]

now = datetime.now(timezone.utc)
current_year = now.year
today = now.date()

QUERY = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    createdAt
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
  }
}
"""


def fetch_year_stats(year):
    start = f"{year}-01-01T00:00:00Z"

    if year == current_year:
        end = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        end = f"{year}-12-31T23:59:59Z"

    payload = {
        "query": QUERY,
        "variables": {
            "username": USERNAME,
            "from": start,
            "to": end
        }
    }

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json"
        },
        method="POST"
    )

    with urllib.request.urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))

    if "errors" in result:
        raise RuntimeError(f"GitHub GraphQL error: {result['errors']}")

    user = result["data"]["user"]

    if user is None:
        raise RuntimeError(f"GitHub user '{USERNAME}' was not found.")

    return user


# --------------------------------------------------
# Fetch all yearly contribution data
# --------------------------------------------------

user = fetch_year_stats(current_year)

created_at = datetime.fromisoformat(
    user["createdAt"].replace("Z", "+00:00")
)

first_year = created_at.year

all_time = {
    "contributions": 0,
    "commits": 0,
    "issues": 0,
    "pull_requests": 0,
    "reviews": 0
}

yearly = {
    "contributions": 0,
    "commits": 0,
    "issues": 0,
    "pull_requests": 0,
    "reviews": 0
}

contribution_days = {}

for year in range(first_year, current_year + 1):

    # Reuse the current-year result already fetched.
    year_user = user if year == current_year else fetch_year_stats(year)

    stats = year_user["contributionsCollection"]
    calendar = stats["contributionCalendar"]

    values = {
        "contributions": calendar["totalContributions"],
        "commits": stats["totalCommitContributions"],
        "issues": stats["totalIssueContributions"],
        "pull_requests": stats["totalPullRequestContributions"],
        "reviews": stats["totalPullRequestReviewContributions"]
    }

    for key, value in values.items():
        all_time[key] += value

        if year == current_year:
            yearly[key] = value

    # Collect daily contributions for streak calculations.
    for week in calendar["weeks"]:
        for day in week["contributionDays"]:
            day_date = date.fromisoformat(day["date"])

            if created_at.date() <= day_date <= today:
                contribution_days[day_date] = day["contributionCount"]


# --------------------------------------------------
# Calculate current and longest contribution streak
# --------------------------------------------------

active_dates = sorted(
    day for day, count in contribution_days.items()
    if count > 0
)

longest_streak = 0
current_run = 0
previous_date = None

for active_date in active_dates:

    if previous_date == active_date - timedelta(days=1):
        current_run += 1
    else:
        current_run = 1

    longest_streak = max(longest_streak, current_run)
    previous_date = active_date


# Current streak is valid if the last active day was today
# or yesterday.
current_streak = 0

if active_dates:
    last_active = active_dates[-1]

    if last_active >= today - timedelta(days=1):
        current_streak = 1
        check_date = last_active - timedelta(days=1)

        while check_date in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)


# --------------------------------------------------
# Generate table-style SVG
# --------------------------------------------------

rows = [
    ("Total Contributions", all_time["contributions"], yearly["contributions"]),
    ("Total Commits", all_time["commits"], yearly["commits"]),
    ("Total Pull Requests", all_time["pull_requests"], yearly["pull_requests"]),
    ("Total Issues", all_time["issues"], yearly["issues"]),
    ("PR Reviews", all_time["reviews"], yearly["reviews"]),
    ("Current Streak", f"{current_streak} days", "—"),
    ("Longest Streak", f"{longest_streak} days", "—")
]

row_height = 36
height = 112 + len(rows) * row_height + 24

svg_parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="760" height="{height}" viewBox="0 0 760 {height}">',
    '<rect width="760" height="100%" rx="12" fill="#0d1117"/>',
    '<text x="28" y="35" fill="#ffffff" font-family="Arial" font-size="21" font-weight="bold">GitHub Statistics</text>',
    f'<text x="28" y="58" fill="#8b949e" font-family="Arial" font-size="12">All-time activity and {current_year} contributions</text>',
    '<rect x="20" y="76" width="720" height="34" rx="5" fill="#161b22"/>',
    '<g font-family="Arial" font-size="12" font-weight="bold" fill="#8b949e">',
    '<text x="36" y="98">STATISTIC</text>',
    '<text x="430" y="98" text-anchor="middle">ALL-TIME</text>',
    f'<text x="640" y="98" text-anchor="middle">{current_year}</text>',
    '</g>'
]

for index, (label, all_value, year_value) in enumerate(rows):

    y = 110 + index * row_height
    background = "#161b22" if index % 2 == 0 else "#0d1117"

    svg_parts.append(
        f'<rect x="20" y="{y}" width="720" height="{row_height}" fill="{background}"/>'
    )

    svg_parts.append(
        f'<text x="36" y="{y + 23}" fill="#c9d1d9" font-family="Arial" font-size="13">{escape(label)}</text>'
    )

    svg_parts.append(
        f'<text x="430" y="{y + 23}" fill="#58a6ff" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold">{escape(str(all_value))}</text>'
    )

    svg_parts.append(
        f'<text x="640" y="{y + 23}" fill="#3fb950" text-anchor="middle" font-family="Arial" font-size="13" font-weight="bold">{escape(str(year_value))}</text>'
    )

svg_parts.append(
    f'<text x="28" y="{height - 10}" fill="#8b949e" font-family="Arial" font-size="10">Source: GitHub GraphQL API • Updated {escape(now.strftime("%Y-%m-%d %H:%M UTC"))}</text>'
)

svg_parts.append("</svg>")

output = Path("assets/yearly-stats.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(svg_parts), encoding="utf-8")


# --------------------------------------------------
# Console output
# --------------------------------------------------

print(f"GitHub statistics updated for {USERNAME}")
print(f"All-time contributions: {all_time['contributions']:,}")
print(f"{current_year} contributions: {yearly['contributions']:,}")
print(f"All-time commits: {all_time['commits']:,}")
print(f"{current_year} commits: {yearly['commits']:,}")
print(f"All-time pull requests: {all_time['pull_requests']:,}")
print(f"All-time issues: {all_time['issues']:,}")
print(f"Current streak: {current_streak} days")
print(f"Longest streak: {longest_streak} days")
print(f"SVG generated: {output}")

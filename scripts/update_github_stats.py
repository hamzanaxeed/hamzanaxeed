import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "hamzanaxeed"
TOKEN = os.environ["GH_STATS_TOKEN"]

now = datetime.now(timezone.utc)
year = now.year

start_date = f"{year}-01-01T00:00:00Z"
end_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")

query = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
      }
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
    }
  }
}
"""

payload = {
    "query": query,
    "variables": {
        "username": USERNAME,
        "from": start_date,
        "to": end_date
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

stats = user["contributionsCollection"]

contributions = stats["contributionCalendar"]["totalContributions"]
commits = stats["totalCommitContributions"]
issues = stats["totalIssueContributions"]
pull_requests = stats["totalPullRequestContributions"]
reviews = stats["totalPullRequestReviewContributions"]

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="720" height="190" viewBox="0 0 720 190">
  <rect width="720" height="190" rx="12" fill="#0d1117"/>
  <text x="28" y="38" fill="#ffffff" font-family="Arial, sans-serif" font-size="20" font-weight="bold">GitHub Activity — {year}</text>
  <text x="28" y="62" fill="#8b949e" font-family="Arial, sans-serif" font-size="12">January 1 – {escape(now.strftime("%B %d, %Y"))}</text>

  <g font-family="Arial, sans-serif">
    <rect x="24" y="82" width="210" height="82" rx="9" fill="#161b22"/>
    <text x="42" y="112" fill="#8b949e" font-size="12">TOTAL CONTRIBUTIONS</text>
    <text x="42" y="145" fill="#3fb950" font-size="29" font-weight="bold">{contributions:,}</text>

    <rect x="246" y="82" width="210" height="82" rx="9" fill="#161b22"/>
    <text x="264" y="112" fill="#8b949e" font-size="12">COMMITS</text>
    <text x="264" y="145" fill="#58a6ff" font-size="29" font-weight="bold">{commits:,}</text>

    <rect x="468" y="82" width="228" height="82" rx="9" fill="#161b22"/>
    <text x="486" y="112" fill="#8b949e" font-size="12">PULL REQUESTS</text>
    <text x="486" y="145" fill="#d2a8ff" font-size="29" font-weight="bold">{pull_requests:,}</text>
  </g>

  <text x="28" y="182" fill="#8b949e" font-family="Arial, sans-serif" font-size="10">Issues opened: {issues:,}  •  PR reviews: {reviews:,}  •  Source: GitHub GraphQL API</text>
</svg>
"""

output = Path("assets/yearly-stats.svg")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(svg, encoding="utf-8")

print(f"Updated {year} statistics:")
print(f"Contributions: {contributions}")
print(f"Commits: {commits}")
print(f"Issues: {issues}")
print(f"Pull requests: {pull_requests}")
print(f"PR reviews: {reviews}")
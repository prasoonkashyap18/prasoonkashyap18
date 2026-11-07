#!/usr/bin/env python3
"""Generate self-hosted GitHub analytics cards from GitHub GraphQL."""
import datetime as dt
import html
import json
import os
import urllib.request

USERNAME = "prasoonkashyap18"
TOKEN = os.environ["PROFILE_STATS_TOKEN"]
END = dt.datetime.now(dt.timezone.utc).date()
START = END - dt.timedelta(days=364)

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""
payload = {
    "query": QUERY,
    "variables": {
        "login": USERNAME,
        "from": f"{START.isoformat()}T00:00:00Z",
        "to": f"{END.isoformat()}T23:59:59Z",
    },
}
request = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps(payload).encode(),
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "profile-github-analytics",
    },
)
with urllib.request.urlopen(request, timeout=30) as response:
    response_data = json.load(response)
if response_data.get("errors"):
    raise RuntimeError("GitHub GraphQL error: " + json.dumps(response_data["errors"]))

user = response_data["data"]["user"]
calendar = user["contributionsCollection"]["contributionCalendar"]
contribution_days = {
    dt.date.fromisoformat(day["date"]): day["contributionCount"]
    for week in calendar["weeks"] for day in week["contributionDays"]
}
total_contributions = calendar["totalContributions"]
today_or_yesterday = END if contribution_days.get(END, 0) else END - dt.timedelta(days=1)
current_streak = 0
cursor = today_or_yesterday
while contribution_days.get(cursor, 0) > 0:
    current_streak += 1
    cursor -= dt.timedelta(days=1)
longest_streak = 0
run = 0
for day in sorted(contribution_days):
    if contribution_days[day] > 0:
        run += 1
        longest_streak = max(longest_streak, run)
    else:
        run = 0

repos = user["repositories"]["nodes"]
stars = sum(repo["stargazerCount"] for repo in repos)
languages = {}
for repo in repos:
    for edge in repo["languages"]["edges"]:
        name = edge["node"]["name"]
        languages[name] = languages.get(name, 0) + edge["size"]
top_languages = sorted(languages.items(), key=lambda item: item[1], reverse=True)[:6]
language_total = sum(value for _, value in top_languages) or 1

BG = "#0D0B18"
PANEL = "#171329"
TEXT = "#E5E7EB"
MUTED = "#A7A1BC"
PURPLE = "#A78BFA"
VIOLET = "#8B5CF6"
INDIGO = "#6366F1"
ACCENTS = ["#A78BFA", "#8B5CF6", "#6366F1", "#C084FC", "#7C3AED", "#4F46E5"]

def esc(value):
    return html.escape(str(value), quote=True)

def card_start(width, height, title, subtitle=""):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        f'<title>{esc(title)}</title>',
        f'<rect width="{width}" height="{height}" rx="16" fill="{BG}" stroke="#30294A"/>',
        f'<text x="24" y="34" fill="{TEXT}" font-size="17" font-weight="700">{esc(title)}</text>',
        f'<text x="{width-24}" y="33" text-anchor="end" fill="{MUTED}" font-size="11">{esc(subtitle)}</text>',
    ]

# Main statistics card
contrib = user["contributionsCollection"]
stats = [
    ("CONTRIBUTIONS", f"{total_contributions:,}", "last 12 months"),
    ("PUBLIC REPOS", f'{user["repositories"]["totalCount"]:,}', "owned repositories"),
    ("STARS EARNED", f"{stars:,}", "across public repos"),
    ("FOLLOWERS", f'{user["followers"]["totalCount"]:,}', "GitHub community"),
]
svg = card_start(700, 190, "GitHub Overview", "live profile data")
for index, (label, value, detail) in enumerate(stats):
    x = 24 + index * 168
    svg.extend([
        f'<rect x="{x}" y="57" width="152" height="105" rx="11" fill="{PANEL}"/>',
        f'<text x="{x+13}" y="83" fill="{MUTED}" font-size="10" letter-spacing=".6">{label}</text>',
        f'<text x="{x+13}" y="119" fill="{PURPLE}" font-size="27" font-weight="700">{value}</text>',
        f'<text x="{x+13}" y="143" fill="{MUTED}" font-size="10">{detail}</text>',
    ])
svg.append(f'<text x="24" y="179" fill="{MUTED}" font-size="10">Commits {contrib["totalCommitContributions"]:,}  ·  PRs {contrib["totalPullRequestContributions"]:,}  ·  Issues {contrib["totalIssueContributions"]:,}</text>')
svg.append("</svg>")
os.makedirs(".github/assets", exist_ok=True)
with open(".github/assets/github-stats.svg", "w", encoding="utf-8") as file:
    file.write("\n".join(svg))

# Top languages card
svg = card_start(700, 220, "Most Used Languages", "by code bytes in public repositories")
if not top_languages:
    svg.append(f'<text x="24" y="100" fill="{MUTED}" font-size="14">No public repository language data yet.</text>')
else:
    y = 66
    for index, (name, size) in enumerate(top_languages):
        percent = size / language_total * 100
        bar_width = 430 * percent / 100
        svg.extend([
            f'<text x="24" y="{y+12}" fill="{TEXT}" font-size="12">{esc(name)}</text>',
            f'<rect x="160" y="{y}" width="430" height="13" rx="6.5" fill="#30294A"/>',
            f'<rect x="160" y="{y}" width="{bar_width:.1f}" height="13" rx="6.5" fill="{ACCENTS[index]}"/>',
            f'<text x="670" y="{y+12}" text-anchor="end" fill="{MUTED}" font-size="11">{percent:.1f}%</text>',
        ])
        y += 25
svg.append("</svg>")
with open(".github/assets/top-languages.svg", "w", encoding="utf-8") as file:
    file.write("\n".join(svg))

# Contribution streak card
svg = card_start(700, 190, "Contribution Streak", "based on daily contribution calendar")
streak_stats = [
    ("CURRENT STREAK", f"{current_streak} days"),
    ("LONGEST STREAK", f"{longest_streak} days"),
    ("LAST 12 MONTHS", f"{total_contributions:,} contributions"),
]
for index, (label, value) in enumerate(streak_stats):
    x = 24 + index * 220
    svg.extend([
        f'<rect x="{x}" y="57" width="202" height="88" rx="11" fill="{PANEL}"/>',
        f'<text x="{x+13}" y="83" fill="{MUTED}" font-size="10">{label}</text>',
        f'<text x="{x+13}" y="119" fill="{PURPLE}" font-size="24" font-weight="700">{esc(value)}</text>',
    ])
svg.append(f'<text x="24" y="173" fill="{MUTED}" font-size="10">Calendar window: {START.isoformat()} to {END.isoformat()} UTC</text>')
svg.append("</svg>")
with open(".github/assets/streak.svg", "w", encoding="utf-8") as file:
    file.write("\n".join(svg))

print(f"Generated analytics: {total_contributions} contributions, {len(repos)} public repos, {stars} stars, {len(top_languages)} languages, {current_streak}-day current streak.")

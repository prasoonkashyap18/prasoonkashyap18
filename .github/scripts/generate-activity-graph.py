#!/usr/bin/env python3
"""Generate a self-hosted 31-day GitHub contribution activity graph."""
import datetime as dt
import html
import json
import os
import urllib.request

USERNAME = "prasoonkashyap18"
TOKEN = os.environ["PROFILE_STATS_TOKEN"]
END = dt.datetime.now(dt.timezone.utc).date()
START = END - dt.timedelta(days=364)

query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
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
    }
  }
}
"""
payload = {
    "query": query,
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
        "User-Agent": "profile-activity-graph",
    },
)
with urllib.request.urlopen(request, timeout=30) as response:
    data = json.load(response)

if data.get("errors"):
    raise RuntimeError("GitHub GraphQL error: " + json.dumps(data["errors"]))
calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
counts = {}
for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        counts[dt.date.fromisoformat(day["date"])] = day["contributionCount"]

days = [END - dt.timedelta(days=30 - i) for i in range(31)]
values = [counts.get(day, 0) for day in days]
total = sum(values)
peak = max(values, default=0)

W, H = 1000, 330
left, right, top, bottom = 64, 28, 58, 58
plot_w, plot_h = W - left - right, H - top - bottom
max_y = max(peak, 1)
points = []
for i, value in enumerate(values):
    x = left + i * plot_w / (len(values) - 1)
    y = top + plot_h - (value / max_y) * (plot_h - 18)
    points.append((x, y))
line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
area = f"{left},{top + plot_h} " + line + f" {left + plot_w},{top + plot_h}"

grid = []
for tick in range(5):
    value = round(max_y * tick / 4)
    y = top + plot_h - (value / max_y) * (plot_h - 18)
    grid.append(
        f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" '
        'stroke="#34304b" stroke-width="1" stroke-dasharray="4 7"/>'
        f'<text x="{left - 14}" y="{y + 4:.1f}" text-anchor="end" '
        'fill="#aaa5c2" font-size="12">' + str(value) + '</text>'
    )

labels = []
for index in (0, 7, 14, 21, 30):
    x = left + index * plot_w / 30
    label = days[index].strftime("%b %d")
    labels.append(
        f'<text x="{x:.1f}" y="{H - 24}" text-anchor="middle" '
        f'fill="#aaa5c2" font-size="12">{html.escape(label)}</text>'
    )

circles = "".join(
    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.8" fill="#c4b5fd" '
    'stroke="#171329" stroke-width="2"/>'
    for x, y in points
)
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">GitHub contribution activity for {USERNAME}</title>
<desc id="desc">Daily GitHub contributions over the last 31 days. Total: {total}.</desc>
<defs>
  <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#8b5cf6" stop-opacity=".48"/>
    <stop offset="100%" stop-color="#8b5cf6" stop-opacity=".02"/>
  </linearGradient>
  <linearGradient id="line" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#6366f1"/>
    <stop offset="100%" stop-color="#c084fc"/>
  </linearGradient>
</defs>
<rect width="100%" height="100%" rx="18" fill="#0d0b18"/>
<text x="{left}" y="30" fill="#f5f3ff" font-size="18" font-weight="700">Contribution activity</text>
<text x="{W-right}" y="30" text-anchor="end" fill="#c4b5fd" font-size="13">{total} contributions · last 31 days</text>
{''.join(grid)}
<polygon points="{area}" fill="url(#area)"/>
<polyline points="{line}" fill="none" stroke="url(#line)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>
{circles}
{''.join(labels)}
<text x="{W-right}" y="{H-7}" text-anchor="end" fill="#77718f" font-size="10">Updated {END.isoformat()} UTC</text>
</svg>
'''
os.makedirs(".github/assets", exist_ok=True)
with open(".github/assets/activity-graph.svg", "w", encoding="utf-8") as output:
    output.write(svg)
print(f"Generated activity graph: {total} contributions in the last 31 days (peak {peak}/day).")

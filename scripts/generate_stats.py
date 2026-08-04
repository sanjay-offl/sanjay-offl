"""
generate_stats.py  —  sanjay-offl GitHub profile stats
Generates: stats.svg, streak.svg, langs.svg, year.svg
           hd-about.svg, hd-stack.svg, hd-projects.svg,
           hd-stats.svg, hd-about-this-page.svg

Requires only the Python standard library.
Run with:  GITHUB_TOKEN=<token> GH_LOGIN=sanjay-offl python3 scripts/generate_stats.py
"""

import json, os, urllib.request, urllib.parse, base64
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
TOKEN    = os.environ["GITHUB_TOKEN"]
LOGIN    = os.environ.get("GH_LOGIN", "sanjay-offl")
OUT_DIR  = "."          # repo root — where the README expects the files

FILL        = "#c9d1d9"   # main text / bar colour (GitHub dark text)
BG          = "transparent"
ACCENT      = "#58a6ff"   # blue highlight
DIM         = "#8b949e"   # secondary text

FONT_MONO   = "'JetBrains Mono','Liberation Mono','DejaVu Sans Mono',monospace"
FONT_SANS   = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"
FONT_SIZE   = 13
LINE_H      = FONT_SIZE * 1.6

# portrait ramp (for year.svg)
RAMP = ' .`:-=+*cs#%@'

# ─────────────────────────────────────────────────────────────────────────────
# GitHub GraphQL helper
# ─────────────────────────────────────────────────────────────────────────────
def gql(query: str, variables: dict = None):
    payload = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type":  "application/json",
        },
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["data"]

# ─────────────────────────────────────────────────────────────────────────────
# Fetch data
# ─────────────────────────────────────────────────────────────────────────────
now    = datetime.now(timezone.utc)
today  = now.replace(hour=23, minute=59, second=59, microsecond=0)
start  = (today - timedelta(days=364)).replace(hour=0, minute=0, second=0)

print(f"Fetching stats for {LOGIN} …")
print(f"  window: {start.date()} → {today.date()}")

data = gql("""
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
      commitContributionsByRepository(maxRepositories: 10) {
        repository { name }
        contributions { totalCount }
      }
    }
    repositories(first: 100, privacy: PUBLIC, ownerAffiliations: [OWNER]) {
      nodes {
        name
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges {
            size
            node { name color }
          }
        }
      }
    }
    createdAt
  }
}
""", {"login": LOGIN, "from": start.isoformat(), "to": today.isoformat()})

user  = data["user"]
cc    = user["contributionsCollection"]
cal   = cc["contributionCalendar"]
weeks = cal["weeks"]
repos = user["repositories"]["nodes"]

# ── flat list of (date, count) for the window ────────────────────────────────
all_days = []
for week in weeks:
    for day in week["contributionDays"]:
        all_days.append((day["date"], day["contributionCount"]))

all_days.sort()
total_contribs = cal["totalContributions"]

# ── weekly sparkline buckets ──────────────────────────────────────────────────
weekly = []
bucket = 0
for i, (d, c) in enumerate(all_days):
    bucket += c
    if (i + 1) % 7 == 0:
        weekly.append(bucket)
        bucket = 0
if bucket:
    weekly.append(bucket)

# ── streak calculation ────────────────────────────────────────────────────────
current_streak = longest_streak = cur = 0
streak_start   = streak_end = cur_start = None

for d, c in reversed(all_days):
    if c > 0:
        if cur == 0:
            cur_start = d
        cur += 1
        if cur > longest_streak:
            longest_streak = cur
            streak_start   = d
            streak_end     = cur_start
    else:
        if current_streak == 0 and cur > 0:
            current_streak = cur
        if cur > longest_streak:
            longest_streak = cur
            streak_start   = d
            streak_end     = cur_start
        cur = 0

if current_streak == 0:
    current_streak = cur

# ── language totals (bytes, public only) ─────────────────────────────────────
lang_bytes  = {}
lang_repos  = {}
for repo in repos:
    seen = set()
    for edge in repo["languages"]["edges"]:
        name  = edge["node"]["name"]
        color = edge["node"]["color"] or "#888"
        size  = edge["size"]
        lang_bytes[name] = lang_bytes.get(name, 0) + size
        if name not in seen:
            lang_repos[name] = lang_repos.get(name, 0) + 1
            seen.add(name)

top_langs = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:8]

print(f"  total contributions: {total_contribs}")
print(f"  current streak:      {current_streak}")
print(f"  longest streak:      {longest_streak}")
print(f"  top languages:       {[l for l,_ in top_langs]}")

# ─────────────────────────────────────────────────────────────────────────────
# SVG helpers
# ─────────────────────────────────────────────────────────────────────────────
def svg_open(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>\n')

def svg_close():
    return '</svg>'

def txt(x, y, content, size=FONT_SIZE, fill=FILL, anchor="start", family=FONT_MONO, weight="normal"):
    return (f'<text x="{x}" y="{y}" '
            f'font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{content}</text>\n')

def save(name, content):
    path = os.path.join(OUT_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  wrote {path}")

# ─────────────────────────────────────────────────────────────────────────────
# 1. stats.svg  — total contributions + weekly sparkline
# ─────────────────────────────────────────────────────────────────────────────
W, H = 620, 100
SPARK_X, SPARK_Y = 180, 15
SPARK_W, SPARK_H = 420, 65

spark_max = max(weekly) if weekly else 1
parts     = [svg_open(W, H)]
parts.append(txt(20, 38, f"{total_contribs:,}", size=32, fill=FILL, weight="600"))
parts.append(txt(20, 58, "contributions · last 365 days", size=11, fill=DIM))
parts.append(txt(20, 78, f"{cc['totalCommitContributions']:,} commits · "
                         f"{cc['totalPullRequestContributions']:,} PRs · "
                         f"{cc['totalIssueContributions']:,} issues",
                 size=11, fill=DIM))

# sparkline bars
bar_w  = max(1, SPARK_W // len(weekly) - 1)
spacing = SPARK_W / len(weekly)
for i, v in enumerate(weekly):
    bh = max(2, int(v / spark_max * SPARK_H))
    bx = SPARK_X + i * spacing
    by = SPARK_Y + SPARK_H - bh
    parts.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w}" height="{bh}" '
                 f'fill="{ACCENT}" opacity="0.85" rx="1"/>\n')

parts.append(svg_close())
save("stats.svg", "".join(parts))

# ─────────────────────────────────────────────────────────────────────────────
# 2. streak.svg — current streak + longest streak
# ─────────────────────────────────────────────────────────────────────────────
W, H = 620, 80
parts = [svg_open(W, H)]
# divider
parts.append(f'<line x1="310" y1="10" x2="310" y2="70" stroke="{DIM}" stroke-width="1" opacity="0.3"/>\n')
# left: current streak
parts.append(txt(155, 42, f"{current_streak}", size=36, fill=FILL, anchor="middle", weight="600"))
parts.append(txt(155, 62, "current streak", size=11, fill=DIM, anchor="middle"))
# right: longest streak
parts.append(txt(465, 42, f"{longest_streak}", size=36, fill=FILL, anchor="middle", weight="600"))
parts.append(txt(465, 62, "longest streak", size=11, fill=DIM, anchor="middle"))
if streak_start and streak_end:
    label = f"{streak_start} → {streak_end}"
    parts.append(txt(465, 74, label, size=9, fill=DIM, anchor="middle"))
parts.append(svg_close())
save("streak.svg", "".join(parts))

# ─────────────────────────────────────────────────────────────────────────────
# 3. langs.svg — top languages
# ─────────────────────────────────────────────────────────────────────────────
# Map language names to colors
LANG_COLORS = {
    "Python":     "#3572A5",
    "TypeScript": "#2b7489",
    "JavaScript": "#f1e05a",
    "HTML":       "#e34c26",
    "CSS":        "#563d7c",
    "Shell":      "#89e051",
    "Dockerfile": "#384d54",
    "MDX":        "#fcb32c",
}

W, H    = 620, 130
BAR_H   = 12
total_b = sum(v for _, v in top_langs) or 1
parts   = [svg_open(W, H)]
parts.append(txt(20, 22, "top languages · public repos", size=11, fill=DIM))

# percentage bar
bar_x, bar_y = 20, 32
bar_total_w  = 580
x = bar_x
for lang, byt in top_langs:
    frac = byt / total_b
    w    = max(2, int(frac * bar_total_w))
    col  = LANG_COLORS.get(lang, "#8b949e")
    parts.append(f'<rect x="{x}" y="{bar_y}" width="{w}" height="{BAR_H}" '
                 f'fill="{col}" rx="2"/>\n')
    x += w

# legend
lx, ly = 20, 62
for i, (lang, byt) in enumerate(top_langs):
    col  = LANG_COLORS.get(lang, "#8b949e")
    pct  = byt / total_b * 100
    col_w = 8
    # two columns layout
    if i >= 4:
        lx2 = 320
        ly2 = 62 + (i - 4) * 17
    else:
        lx2 = 20
        ly2 = 62 + i * 17
    parts.append(f'<rect x="{lx2}" y="{ly2 - 7}" width="{col_w}" height="{col_w}" '
                 f'fill="{col}" rx="1"/>\n')
    parts.append(txt(lx2 + col_w + 6, ly2, f"{lang}", size=11, fill=FILL))
    parts.append(txt(lx2 + col_w + 6 + 100, ly2, f"{pct:.1f}%", size=11, fill=DIM))

parts.append(svg_close())
save("langs.svg", "".join(parts))

# ─────────────────────────────────────────────────────────────────────────────
# 4. year.svg — one char per day using the portrait ramp
# ─────────────────────────────────────────────────────────────────────────────
RAMP_CHARS = ' .:-+#@'
day_max    = max((c for _, c in all_days), default=1)
W, H       = 620, 100
CELL       = 7
GAP        = 1
parts      = [svg_open(W, H)]
parts.append(txt(20, 16, "the year · one character per day", size=11, fill=DIM))

# map contributions to ramp
x0, y0 = 20, 24
col = 0
row = 0
for date_s, count in all_days:
    if count == 0:
        ch = '.'
    else:
        idx = max(1, int(count / day_max * (len(RAMP_CHARS) - 1)))
        ch  = RAMP_CHARS[idx]
    cx = x0 + col * (CELL + GAP)
    cy = y0 + row * (CELL + GAP)
    parts.append(
        f'<text x="{cx}" y="{cy + CELL}" '
        f'font-family="{FONT_MONO}" font-size="{CELL}" '
        f'fill="{ACCENT}">{ch}</text>\n'
    )
    row += 1
    if row >= 7:
        row = 0
        col += 1

parts.append(svg_close())
save("year.svg", "".join(parts))

# ─────────────────────────────────────────────────────────────────────────────
# 5. Section heading SVGs
# ─────────────────────────────────────────────────────────────────────────────
def make_heading(filename, label):
    W, H = 620, 36
    parts = [svg_open(W, H)]
    # label in mono
    parts.append(txt(0, 22, label, size=12, fill=DIM, family=FONT_MONO))
    # hairline rule
    label_w = len(label) * 7.4 + 4  # rough estimate
    parts.append(
        f'<line x1="{label_w:.0f}" y1="18" x2="620" y2="18" '
        f'stroke="{DIM}" stroke-width="0.5" opacity="0.4"/>\n'
    )
    parts.append(svg_close())
    save(filename, "".join(parts))

make_heading("hd-about.svg",          "about")
make_heading("hd-stack.svg",          "stack")
make_heading("hd-projects.svg",       "projects")
make_heading("hd-stats.svg",          "stats")
make_heading("hd-about-this-page.svg","about this page")

print("\nAll files generated.")

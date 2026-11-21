"""Render the profile stage: the fonneyx wordmark standing on a perspective floor
made from the last year of contributions.

The contribution calendar (53 weeks x 7 days) is laid flat on the ground in front
of the wordmark, in the same orientation as GitHub's own graph: oldest week on the
left, Sunday at the back. An empty day is a faint floor dot; a day with activity
rises as a pillar of 1-4 dots (GitHub's contribution level). A slow wave travels
through the weeks from old to new.

Standard library only. Data comes from GitHub's GraphQL API (GITHUB_TOKEN or
GH_TOKEN), or from a saved JSON response with --data for offline work.

Usage: python scripts/render.py [--login fonneyx] [--data response.json]
"""
import argparse
import json
import math
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

THEMES = {
    "dark": "#E6EDF3",
    "light": "#1F2328",
}

QUERY = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date weekday contributionLevel } }
      }
    }
  }
}"""

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch(login):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("Set GITHUB_TOKEN or GH_TOKEN, or pass --data.")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-stage-renderer"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.load(resp)
    if body.get("errors"):
        raise SystemExit(f"GraphQL error: {body['errors']}")
    return body


def calendar(body):
    cal = body["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["weekday"], LEVELS[d["contributionLevel"]]) for d in w["contributionDays"]]
             for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def render(ink, word, total, weeks):
    W, H, horizon, step = word["width"], word["height"], word["baseline"], word["step"]
    f = H - horizon                              # camera height 1: z=1 lands on the bottom edge
    cx = W / 2
    taken = {(x // step, y // step) for x, y, _ in word["dots"]}

    def free(x, y):
        return (int(x) // step, int(y) // step) not in taken

    def edge(x):                                 # soft vignette toward the sides
        return max(0.0, math.sin(math.pi * min(max(x, 0), W) / W)) ** 1.1

    # 1. Ambient floor behind the calendar, receding to the horizon.
    ambient, z = [], 4.5
    while z <= 9.0:
        y, r = horizon + f / z, 2.3 / z ** 0.75
        fade = max(0.0, 1 - (z - 4.5) / 4.8) ** 0.9
        reach, dx = (W / 2) * z / f, 0.25
        X = -math.floor(reach / dx) * dx
        while X <= reach:
            x = cx + f * X / z
            o = (0.05 + 0.16 * fade) * edge(x)
            if 0 <= x <= W and o > 0.03 and free(x, y):
                ambient.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill-opacity="{o:.2f}"/>')
            X += dx
        z += 0.25

    # 2. The calendar on the floor: weeks left -> right, Sunday at the back.
    n = len(weeks)
    z_back, z_front = 4.0, 1.5
    half_x = (W * 0.46) * z_front / f            # front row spans ~92% of the width
    dx = 2 * half_x / max(n - 1, 1)
    today = weeks[-1][-1][0]
    groups = []
    for wi, week in enumerate(weeks):
        X = -half_x + wi * dx
        dots = []
        for date, wd, level in week:
            z = z_back - (z_back - z_front) * wd / 6
            x, y = cx + f * X / z, horizon + f / z
            pitch = f * dx / z                   # on-screen column spacing at this depth
            r = 0.30 * pitch
            e = 0.45 + 0.55 * edge(x)
            if free(x, y):                       # every day keeps its floor dot
                o = 0.30 * e if level == 0 else 0.55 * e
                dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill-opacity="{o:.2f}"/>')
            gap, r_up = 0.8 * pitch, 0.36 * pitch
            for k in range(1, level + 1):        # active days rise: one dot per level
                py = y - k * gap
                top = k == level
                o = (0.6 + 0.4 * k / level) * e
                cls = ' class="now"' if top and date == today else ""
                if free(x, py):
                    dots.append(f'<circle{cls} cx="{x:.1f}" cy="{py:.1f}" r="{r_up:.2f}" fill-opacity="{o:.2f}"/>')
        if dots:
            delay = -6.0 * (1 - wi / n)
            groups.append(f'<g class="w" style="animation-delay:{delay:.2f}s">{"".join(dots)}</g>')

    letters = "".join(f'<circle cx="{x}" cy="{y}" r="{r}"/>' for x, y, r in word["dots"])
    label = f"fonneyx — {total} contributions in the last year"
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{label}">
<title>{label}</title>
<style>
.w{{animation:wave 6s linear infinite}}
@keyframes wave{{0%,100%{{opacity:.5}}6%{{opacity:1}}16%{{opacity:.5}}}}
.now{{animation:now 2.4s ease-in-out infinite}}
@keyframes now{{0%,100%{{opacity:1}}50%{{opacity:.25}}}}
@media (prefers-reduced-motion:reduce){{.w,.now{{animation:none;opacity:1}}}}
</style>
<g fill="{ink}">{"".join(ambient)}{"".join(groups)}{letters}</g>
</svg>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--login", default="fonneyx")
    ap.add_argument("--data", help="saved GraphQL response (skips the network)")
    args = ap.parse_args()

    body = json.loads(Path(args.data).read_text()) if args.data else fetch(args.login)
    total, weeks = calendar(body)
    word = json.loads((ROOT / "data" / "wordmark.json").read_text())
    for name, ink in THEMES.items():
        svg = render(ink, word, total, weeks)
        (ROOT / "assets" / f"fonneyx-{name}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg) / 1024:.0f} KB, {total} contributions")


if __name__ == "__main__":
    main()

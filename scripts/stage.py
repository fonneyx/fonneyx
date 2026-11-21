"""Render the fonneyx stage: a 3D particle swarm that assembles into the wordmark.

Every dot of the wordmark (data/wordmark.json) gets two positions in a 3D cloud.
The cloud is projected through a pinhole camera here in Python, because CSS 3D
perspective inside SVG is not rendered reliably by browsers. The SVG then only
animates 2D translate/scale/opacity per dot through CSS custom properties, which
keeps the file small. A static perspective floor sits under the word.

Standard library only.
Usage: python scripts/stage.py [--seed 7] [--freeze SECONDS]
  --freeze renders a paused frame at that point of the loop (for previews).
"""
import argparse
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = {"dark": "#E6EDF3", "light": "#1F2328"}

LOOP = 11.0          # seconds per cycle
STAGGER = 1.4        # left-to-right spread of the assembly, seconds
CAM = 900.0          # pinhole distance for the swarm


def project(X, Y, Z, cx, cy):
    p = CAM / (CAM + Z)
    return cx + X * p, cy + Y * p, p


def swarm_point(rng):
    """A point in a flattened, centre-weighted cloud around the word."""
    while True:
        X, Y, Z = rng.gauss(0, 330), rng.gauss(0, 120), rng.gauss(0, 360)
        if -560 < Z < 900:
            return X, Y, Z


def rotate_y(X, Z, deg):
    a = math.radians(deg)
    return X * math.cos(a) + Z * math.sin(a), -X * math.sin(a) + Z * math.cos(a)


def floor(word, ink_attr):
    W, H, horizon = word["width"], word["height"], word["baseline"]
    taken = {(x // 8, y // 8) for x, y, _ in word["dots"]}
    f = H - horizon
    rows, z = [], 1.0
    while z <= 9.0:
        y, r = horizon + f / z, 2.3 / z ** 0.75
        fade = max(0.0, 1 - (z - 1) / 8.5) ** 0.8
        reach = (W / 2) * z / f + 0.25
        X, pts = -math.floor(reach / 0.25) * 0.25, []
        while X <= reach:
            x = W / 2 + f * X / z
            edge = math.sin(math.pi * min(max(x, 0), W) / W) ** 1.2
            o = (0.08 + 0.42 * fade) * edge
            if 0 <= x <= W and o > 0.03 and (int(x) // 8, int(y) // 8) not in taken:
                pts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill-opacity="{o:.2f}"/>')
            X += 0.25
        if pts:
            delay = -5.0 * (1 - (9.0 - z) / 8.0)
            rows.append(f'<g class="f" style="animation-delay:{delay:.2f}s">{"".join(pts)}</g>')
        z += 0.25
    return "".join(rows)


def stage(word, ink, seed, freeze):
    W, H = word["width"], word["height"]
    cx, cy = W / 2, word["baseline"] - 40
    rng = random.Random(seed)
    xs = [d[0] for d in word["dots"]]
    x_min, x_max = min(xs), max(xs)

    dots = []
    for x, y, r in word["dots"]:
        X, Y, Z = swarm_point(rng)
        ax, ay, ap = project(X, Y, Z, cx, cy)
        bX, bZ = rotate_y(X, Z, 80)                  # the cloud has turned while the word was held
        bx, by, bp = project(bX, Y * 1.15, bZ, cx, cy)
        t = (x - x_min) / (x_max - x_min)
        d = -(LOOP - (t * STAGGER + rng.uniform(0, 0.35)))
        style = (f"--x:{ax - x:.0f}px;--y:{ay - y:.0f}px;--s:{0.45 * ap:.2f};--o:{min(0.85, 0.2 + 0.4 * ap):.2f};"
                 f"--u:{bx - x:.0f}px;--v:{by - y:.0f}px;--k:{0.45 * bp:.2f};--q:{min(0.85, 0.2 + 0.4 * bp):.2f};"
                 f"animation-delay:{d:.2f}s")
        dots.append(f'<circle class="p" cx="{x}" cy="{y}" r="{r}" style="{style}"/>')

    paused = ""
    if freeze is not None:
        # Shift every animation by the same amount, then pause: one frame of the loop.
        paused = f".p,.f{{animation-play-state:paused;margin:0}}"
        dots = [s.replace("animation-delay:", f"animation-delay:calc(-{freeze}s + ") .replace('s"/>', 's)"/>')
                for s in dots]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="fonneyx">
<title>fonneyx</title>
<style>
.p{{transform-box:fill-box;transform-origin:center;animation:swarm {LOOP}s infinite both}}
@keyframes swarm{{
0%{{transform:translate(var(--x),var(--y)) scale(var(--s));opacity:var(--o);animation-timing-function:cubic-bezier(.16,1,.3,1)}}
20%{{transform:none;opacity:1;animation-timing-function:linear}}
70%{{transform:none;opacity:1;animation-timing-function:cubic-bezier(.7,0,.84,0)}}
88%{{transform:translate(var(--u),var(--v)) scale(var(--k));opacity:var(--q);animation-timing-function:cubic-bezier(.45,0,.55,1)}}
100%{{transform:translate(var(--x),var(--y)) scale(var(--s));opacity:var(--o)}}
}}
.f{{animation:sweep 5s linear infinite}}
@keyframes sweep{{0%,100%{{opacity:.55}}5%{{opacity:1}}14%{{opacity:.55}}}}
@media (prefers-reduced-motion:reduce){{.p,.f{{animation:none}}}}
{paused}
</style>
<g fill="{ink}">{floor(word, ink)}{"".join(dots)}</g>
</svg>'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--freeze", type=float)
    ap.add_argument("--out", default=str(ROOT / "assets"))
    args = ap.parse_args()
    word = json.loads((ROOT / "data" / "wordmark.json").read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, ink in THEMES.items():
        svg = stage(word, ink, args.seed, args.freeze)
        (out / f"swarm-{name}.svg").write_text(svg, encoding="utf-8")
        print(f"{name}: {len(svg) / 1024:.0f} KB")


if __name__ == "__main__":
    main()

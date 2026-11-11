"""Dot-matrix hero for the fonneyx profile.

The wordmark is rasterised once with Pillow and resampled onto a dot grid, so the
SVG contains only circles: no fonts, identical on every OS. A ground plane of dots
recedes toward the horizon; a slow sweep passes over it like a depth sensor.

Usage: python -I gen_hero.py <out_dir>
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1200, 380
HORIZON = 214                # baseline of the wordmark = horizon of the ground plane
STEP = 8                     # dot grid pitch
R_MAX = 3.3                  # letter dot radius
WORD, MARK = "fonneyx", "."
FONT = "C:/Windows/Fonts/seguibl.ttf"
SS = 4                       # supersampling for coverage

THEMES = {
    "dark": dict(ink="#E6EDF3", accent="#FF453A"),
    "light": dict(ink="#1F2328", accent="#E5321F"),
}


def coverage_masks():
    """Return (word_mask, mark_mask) as L images at W x H with anti-aliased coverage."""
    font = ImageFont.truetype(FONT, 205 * SS)
    ascent = font.getmetrics()[0]
    big = (W * SS, H * SS)
    word_img, mark_img = Image.new("L", big, 0), Image.new("L", big, 0)
    dw, dm = ImageDraw.Draw(word_img), ImageDraw.Draw(mark_img)
    wb = dw.textbbox((0, 0), WORD, font=font)
    mb = dm.textbbox((0, 0), MARK, font=font)
    gap = 6 * SS
    total = (wb[2] - wb[0]) + gap + (mb[2] - mb[0])
    x0 = (big[0] - total) // 2 - wb[0]
    y0 = HORIZON * SS - ascent                          # letters stand on the plane
    dw.text((x0, y0), WORD, font=font, fill=255)
    dm.text((x0 + wb[2] + gap, y0), MARK, font=font, fill=255)
    return word_img.resize((W, H), Image.BOX), mark_img.resize((W, H), Image.BOX)


def cov(img, x, y):
    """Mean coverage in the STEP x STEP cell centred on (x, y)."""
    h = STEP // 2
    box = img.crop((x - h, y - h, x + h, y + h))
    px = list(box.get_flattened_data())
    return sum(px) / (255 * len(px))


def build(theme):
    word, mark = coverage_masks()
    letters = []
    for gx in range(STEP // 2, W, STEP):
        for gy in range(STEP // 2, H, STEP):
            cm, cw = cov(mark, gx, gy), cov(word, gx, gy)
            if cm > 0.12:
                letters.append(f'<circle cx="{gx}" cy="{gy}" r="{R_MAX*math.sqrt(cm):.2f}" fill="{theme["accent"]}"/>')
            elif cw > 0.12:
                letters.append(f'<circle cx="{gx}" cy="{gy}" r="{R_MAX*math.sqrt(cw):.2f}"/>')

    # Ground plane: points on a 3D grid projected through a pinhole camera.
    f = (H - HORIZON) * 1.0          # camera height 1, nearest row (Z=1) lands on the bottom edge
    rows, z, dz, dx = [], 1.0, 0.25, 0.25
    while z <= 9.0:
        y = HORIZON + f / z
        r = 2.3 / z ** 0.75
        depth_fade = max(0.0, 1 - (z - 1) / 8.5) ** 0.8
        pts, xi = [], 0.0
        reach = (W / 2) * z / f + dx
        X = -math.floor(reach / dx) * dx
        while X <= reach:
            x = W / 2 + f * X / z
            if 0 <= x <= W and cov(word, int(min(max(x, 4), W - 4)), int(min(y, H - 4))) < 0.05:
                edge = math.sin(math.pi * x / W) ** 1.2
                o = (0.08 + 0.42 * depth_fade) * edge
                if o > 0.03:
                    pts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill-opacity="{o:.2f}"/>')
            X += dx
        if pts:
            rows.append((z, pts))
        z += dz

    period = 5.0
    groups = []
    for z, pts in rows:
        delay = -period * (1 - (9.0 - z) / 8.0)      # wave travels from the horizon toward the viewer
        groups.append(f'<g class="s" style="animation-delay:{delay:.2f}s">{"".join(pts)}</g>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="fonneyx">
<style>
.s{{animation:sweep {period}s linear infinite}}
@keyframes sweep{{0%,100%{{opacity:.55}}5%{{opacity:1}}14%{{opacity:.55}}}}
@media (prefers-reduced-motion:reduce){{.s{{animation:none;opacity:1}}}}
</style>
<g fill="{theme["ink"]}">{"".join(groups)}{"".join(letters)}</g>
</svg>'''


for name, theme in THEMES.items():
    svg = build(theme)
    (OUT / f"hero-{name}.svg").write_text(svg, encoding="utf-8")
    print(name, f"{len(svg)/1024:.0f} KB")

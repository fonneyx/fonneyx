"""Bake the fonneyx wordmark into dots (run locally, once).

Rasterises the word with Pillow and resamples it onto the dot grid, then writes
data/wordmark.json. The daily renderer only reads that file, so CI needs no fonts
and no third-party packages.

Usage: python scripts/wordmark.py [path/to/font.ttf]
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = sys.argv[1] if len(sys.argv) > 1 else "C:/Windows/Fonts/seguibl.ttf"
WORD = "fonneyx"
W, H = 1200, 380
BASELINE = 214      # the floor's horizon in render.py
STEP = 8            # dot grid pitch
R_MAX = 3.3         # radius of a fully covered cell
SS = 4              # supersampling


def main():
    font = ImageFont.truetype(FONT, 205 * SS)
    ascent = font.getmetrics()[0]
    img = Image.new("L", (W * SS, H * SS), 0)
    draw = ImageDraw.Draw(img)
    bbox = draw.textbbox((0, 0), WORD, font=font)
    x0 = (W * SS - (bbox[2] - bbox[0])) // 2 - bbox[0]
    draw.text((x0, BASELINE * SS - ascent), WORD, font=font, fill=255)
    img = img.resize((W, H), Image.BOX)

    dots, h = [], STEP // 2
    for gx in range(h, W, STEP):
        for gy in range(h, H, STEP):
            px = img.crop((gx - h, gy - h, gx + h, gy + h)).get_flattened_data()
            cov = sum(px) / (255 * len(px))
            if cov > 0.12:
                dots.append([gx, gy, round(R_MAX * math.sqrt(cov), 2)])

    out = ROOT / "data" / "wordmark.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({"width": W, "height": H, "baseline": BASELINE,
                               "step": STEP, "dots": dots}, separators=(",", ":")))
    print(f"{len(dots)} dots -> {out}")


if __name__ == "__main__":
    main()

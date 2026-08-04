"""
make_portrait.py  —  sanjay-offl ASCII portrait generator
Converts a photo to an animated ASCII SVG using SMIL typing animation.

Usage:
    python3 scripts/make_portrait.py <photo.jpg>
    # outputs ascii.svg in the repo root

Dependencies:
    pip install pillow numpy opencv-python-headless
"""

import sys, os
import numpy as np
import cv2
from PIL import Image

# ── config ───────────────────────────────────────────────────────────────────
COLS      = 90
CHAR_W    = 7.74
FONT_SIZE = 12.9
LINE_H    = CHAR_W * 2
FILL      = "#c9d1d9"
RAMP      = ' .`:-=+*cs#%@'

# ── load image ───────────────────────────────────────────────────────────────
photo = sys.argv[1] if len(sys.argv) > 1 else "photo.jpg"
if not os.path.exists(photo):
    print(f"Usage: python3 scripts/make_portrait.py <photo>")
    sys.exit(1)

pil = Image.open(photo).convert("RGB")
img = np.array(pil)
h, w = img.shape[:2]
print(f"Loaded {photo} ({w}x{h})")

# ── auto-crop to subject ──────────────────────────────────────────────────────
white_mask = (img[:,:,0] > 238) & (img[:,:,1] > 238) & (img[:,:,2] > 238)
non_white  = ~white_mask
rw     = np.any(non_white, axis=1)
cw_ax  = np.any(non_white, axis=0)
r0 = int(np.argmax(rw));      r1 = int(len(rw)    - np.argmax(rw[::-1]))
c0 = int(np.argmax(cw_ax));   c1 = int(len(cw_ax) - np.argmax(cw_ax[::-1]))
pad = 15
img = img[max(0,r0-pad):min(h,r1+pad), max(0,c0-pad):min(w,c1+pad)]
h, w = img.shape[:2]
print(f"  cropped to {w}x{h}")

rows = int(COLS * (h / w) * 0.48)
print(f"  ASCII grid: {COLS}x{rows}")

# ── processing pipeline ───────────────────────────────────────────────────────
small_orig = cv2.resize(img, (COLS, rows), interpolation=cv2.INTER_AREA)
smooth     = cv2.bilateralFilter(small_orig, d=5, sigmaColor=50, sigmaSpace=50)
gray       = cv2.cvtColor(smooth, cv2.COLOR_RGB2GRAY)
clahe      = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
gray       = clahe.apply(gray)
gray       = ((gray / 255.0) ** 1.7 * 255).astype(np.uint8)

bg_mask = (small_orig[:,:,0] > 238) & (small_orig[:,:,1] > 238) & (small_orig[:,:,2] > 238)

n    = len(RAMP)
grid = []
for r in range(rows):
    row_chars = []
    for c in range(COLS):
        if bg_mask[r, c]:
            row_chars.append(' ')
        else:
            row_chars.append(RAMP[int(gray[r, c] / 255 * (n - 1))])
    grid.append(''.join(row_chars))

# ── SVG with SMIL typing animation ───────────────────────────────────────────
SVG_W = int(COLS * CHAR_W) + 20
SVG_H = int(rows * LINE_H) + 20

def xmlesc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

lines = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">',
    f'  <rect width="{SVG_W}" height="{SVG_H}" fill="transparent"/>',
    '  <defs>',
]
for i in range(rows):
    y = 10 + i * LINE_H
    lines.append(
        f'    <clipPath id="r{i}"><rect x="10" y="{y:.1f}" width="0" height="{LINE_H+2:.1f}">'
        f'<animate attributeName="width" from="0" to="{COLS*CHAR_W:.1f}"'
        f' begin="{i*0.09:.2f}s" dur="{COLS*0.005:.2f}s" fill="freeze"/>'
        f'</rect></clipPath>'
    )
lines.append('  </defs>')
for i, row in enumerate(grid):
    y = 10 + i * LINE_H + FONT_SIZE
    lines.append(
        f'  <text x="10" y="{y:.1f}" '
        f"font-family=\"'JetBrains Mono','Liberation Mono','DejaVu Sans Mono',monospace\" "
        f'font-size="{FONT_SIZE}" fill="{FILL}" xml:space="preserve" '
        f'clip-path="url(#r{i})">{xmlesc(row)}</text>'
    )
lines.append('</svg>')

out = "ascii.svg"
with open(out, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))
print(f"\nSaved -> {out}  ({os.path.getsize(out):,} bytes)")

#!/usr/bin/env python3
"""Generate a polished README banner for Mouse Jiggler."""
from PIL import Image, ImageDraw, ImageFont
import math, sys

W, H = 900, 420
OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "readme_banner.png"

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
# ── Font loading (cross-platform) ────────────────────────────────────────
def load_font(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

def load_font_regular(size):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()

title_font = load_font(46)
subtitle_font = load_font_regular(18)
tag_font = load_font_regular(13)
zzz_font = load_font_regular(18)



# ── Rich dark gradient background ─────────────────────────────────────────
for y in range(H):
    t = y / H
    r = int(18 + 10 * t)
    g = int(22 + 12 * t)
    b = int(32 + 14 * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b, 255))

# Fine dot grid for texture
for x in range(20, W, 20):
    for y in range(20, H, 20):
        draw.point((x, y), fill=(40, 44, 54, 100))

# ── Left: animated mouse movement visualization ──────────────────────────
cx, cy = 200, H // 2 - 10

# Outer glow rings
for i in range(5, 0, -1):
    alpha = 40 - i * 5
    rr = 115 + i * 15
    draw.ellipse(
        [(cx - rr, cy - rr), (cx + rr, cy + rr)],
        outline=(76, 175, 80, alpha), width=2
    )

# Green circle base
r = 105
draw.ellipse(
    [(cx - r, cy - r), (cx + r, cy + r)],
    fill=(56, 142, 60, 255)
)
# Inner highlight
draw.ellipse(
    [(cx - 75, cy - 70), (cx + 65, cy + 50)],
    fill=(76, 175, 80, 100)
)
# Bright rim
draw.ellipse(
    [(cx - r, cy - r), (cx + r, cy + r)],
    outline=(129, 212, 130, 180), width=3
)

# Large white mouse cursor
pointer = [
    (cx - 30, cy - 52), (cx - 36, cy + 30),
    (cx + 1,  cy + 6),  (cx + 34, cy + 48),
    (cx + 58, cy + 28), (cx + 14, cy - 8),
    (cx + 52, cy - 35),
]
draw.polygon(pointer, fill=(255, 255, 255, 255))
# Cursor shadow
draw.polygon(
    [(x + 2, y + 2) for x, y in pointer],
    fill=(0, 0, 0, 30)
)
draw.polygon(pointer, fill=(255, 255, 255, 255))

# Motion trails — dotted arcs
for arc_idx, (arc_r, count, alpha) in enumerate([
    (145, 5, 180), (180, 7, 120), (220, 7, 70)
]):
    for i in range(count):
        angle = math.radians(40 + i * (200 / max(count - 1, 1)))
        ax = int(cx + arc_r * math.cos(angle))
        ay = int(cy + arc_r * math.sin(angle))
        dr = 4 + arc_idx
        draw.ellipse(
            [(ax - dr, ay - dr), (ax + dr, ay + dr)],
            fill=(129, 212, 130, alpha)
        )

# Direction arrow at end of trail
arrow_angle = math.radians(240)
ax_end = int(cx + 235 * math.cos(arrow_angle))
ay_end = int(cy + 235 * math.sin(arrow_angle))
ax_start = int(cx + 200 * math.cos(arrow_angle))
ay_start = int(cy + 200 * math.sin(arrow_angle))
draw.line([(ax_start, ay_start), (ax_end, ay_end)], fill=(200, 230, 201, 200), width=2)
# Arrowhead
perp = arrow_angle + math.pi / 2
draw.polygon([
    (ax_end, ay_end),
    (int(ax_end - 10 * math.cos(arrow_angle) + 6 * math.cos(perp)),
     int(ay_end - 10 * math.sin(arrow_angle) + 6 * math.sin(perp))),
    (int(ax_end - 10 * math.cos(arrow_angle) - 6 * math.cos(perp)),
     int(ay_end - 10 * math.sin(arrow_angle) - 6 * math.sin(perp))),
], fill=(200, 230, 201, 200))

# ── Zzz fading away — screen waking up ───────────────────────────────────
for i, (zx, zy, sz, alpha) in enumerate([
    (cx + 40, cy - 90, 18, 200),
    (cx + 70, cy - 115, 14, 150),
    (cx + 95, cy - 130, 10, 80),
]):
    draw.text((zx, zy), "Z", fill=(180, 200, 210, alpha),
              font=zzz_font)

tx = 420

# Title with green accent
draw.text((tx, 85), "Mouse Jiggler", fill=(129, 212, 130, 255), font=title_font)

# Subtitle
lines = [
    ("Keeps your screen awake with", (210, 215, 220)),
    ("imperceptible mouse movement.", (210, 215, 220)),
]
y = 148
for text, color in lines:
    draw.text((tx, y), text, fill=color + (255,), font=subtitle_font)
    y += 26

# Feature bullets
features = [
    ("▸", "Runs quietly in your system tray or menu bar"),
    ("▸", "Randomized pattern — indistinguishable from real input"),
    ("▸", "No services, no registry, no admin rights"),
]
y = 210
for bullet, text in features:
    draw.text((tx, y), bullet, fill=(129, 212, 130, 255), font=subtitle_font)
    draw.text((tx + 24, y), text, fill=(170, 180, 190, 255), font=subtitle_font)
    y += 28

# Platform badges
platforms = [
    ("Windows", (0, 120, 212)),
    ("macOS", (80, 80, 85)),
    ("Linux", (220, 140, 0)),
]
py = 310
for label, color in platforms:
    tw = len(label) * 8 + 20
    # Badge background
    draw.rounded_rectangle(
        [(tx, py), (tx + tw, py + 28)],
        radius=6, fill=color + (200,)
    )
    # Badge border
    draw.rounded_rectangle(
        [(tx, py), (tx + tw, py + 28)],
        radius=6, outline=color + (255,), width=1
    )
    draw.text((tx + 10, py + 5), label, fill=(255, 255, 255, 255), font=tag_font)
    tx += tw + 12

# Bottom accent line
draw.rectangle([(0, H - 3), (W, H)], fill=(76, 175, 80, 255))

img.save(OUTPUT, "PNG")
print(f"Created {OUTPUT} ({W}x{H})")

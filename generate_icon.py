#!/usr/bin/env python3
"""Generate the Mouse Jiggler icon as a multi-resolution .ico file."""

from PIL import Image, ImageDraw, ImageFont

SIZES = [16, 32, 48, 256]
OUTPUT = "mouse_jiggler.ico"

def draw_icon(size: int) -> Image.Image:
    """Draw a polished mouse cursor icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = size  # shorthand

    # ── Cursor arrow body ────────────────────────────────────────
    # Main arrow shape — filled with a green gradient-like solid + darker border
    body = [
        (s * 0.12, s * 0.08),   # tip
        (s * 0.12, s * 0.72),   # left heel
        (s * 0.36, s * 0.56),   # inner corner
        (s * 0.54, s * 0.82),   # bottom-right point
        (s * 0.72, s * 0.72),   # right tip
        (s * 0.40, s * 0.44),   # inner top
        (s * 0.68, s * 0.30),   # top-right
    ]

    # Fill with green
    draw.polygon(body, fill="#4CAF50", outline="#2E7D32")

    # ── Inner highlight (lighter green stripe) ───────────────────
    highlight = [
        (s * 0.18, s * 0.20),
        (s * 0.18, s * 0.64),
        (s * 0.34, s * 0.50),
        (s * 0.48, s * 0.72),
        (s * 0.64, s * 0.64),
        (s * 0.38, s * 0.42),
        (s * 0.60, s * 0.32),
    ]
    draw.polygon(highlight, fill="#66BB6A")

    # ── White shine on top edge ──────────────────────────────────
    shine = [
        (s * 0.15, s * 0.12),
        (s * 0.15, s * 0.25),
        (s * 0.58, s * 0.25),
        (s * 0.60, s * 0.18),
    ]
    draw.polygon(shine, fill=(255, 255, 255, 100))

    # ── Small jiggle indicator dots ──────────────────────────────
    # Three small dots near the bottom-right suggesting movement
    dot_r = max(2, int(s * 0.04))
    for i, (dx, dy) in enumerate([(0.80, 0.85), (0.88, 0.82), (0.92, 0.88)]):
        x, y = int(s * dx), int(s * dy)
        alpha = 220 - i * 50
        draw.ellipse(
            [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
            fill=(129, 199, 132, alpha),
        )

    return img


def main():
    icons = []
    for size in SIZES:
        print(f"  Drawing {size}x{size}...")
        icons.append(draw_icon(size))

    # Save as multi-resolution .ico
    icons[0].save(
        OUTPUT,
        format="ICO",
        sizes=[(s, s) for s in SIZES],
        append_images=icons[1:],
    )
    print(f"\n✓ Saved {OUTPUT} with sizes {SIZES}")


if __name__ == "__main__":
    main()

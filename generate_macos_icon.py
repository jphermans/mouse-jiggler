#!/usr/bin/env python3
"""Generate AppIcon.icns for Mouse Jiggler macOS app."""
import struct, os, sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("pip3 install Pillow", file=sys.stderr)
    sys.exit(1)

OUTPUT = sys.argv[1] if len(sys.argv) > 1 else "AppIcon.icns"

# ── Generate icon image ───────────────────────────────────────────────────
def make_icon(size):
    """Create a mouse-cursor style icon at given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 512.0  # scale factor

    # Background circle
    r = int(200 * s)
    draw.ellipse(
        [(size//2 - r, size//2 - r), (size//2 + r, size//2 + r)],
        fill="#4CAF50"
    )

    # Mouse pointer shape (white)
    points = [
        (int(140*s), int(100*s)),
        (int(140*s), int(360*s)),
        (int(210*s), int(310*s)),
        (int(280*s), int(410*s)),
        (int(350*s), int(360*s)),
        (int(250*s), int(240*s)),
        (int(340*s), int(170*s)),
    ]
    draw.polygon(points, fill="white")

    # Motion dots
    for angle in [30, 150, 270]:
        import math
        rad = math.radians(angle)
        cx = int(size//2 + 220*s * math.cos(rad))
        cy = int(size//2 + 220*s * math.sin(rad))
        dot_r = int(30 * s)
        draw.ellipse(
            [(cx - dot_r, cy - dot_r), (cx + dot_r, cy + dot_r)],
            fill="white"
        )

    return img

# ── Write .icns file ──────────────────────────────────────────────────────
SIZES = [16, 32, 64, 128, 256, 512]

def write_icns(path):
    icon_data = []
    for sz in SIZES:
        img = make_icon(sz)
        raw = img.tobytes()

        # ARGB (PIL RGBA -> swap to ARGB for icns)
        argb = bytearray()
        for i in range(0, len(raw), 4):
            r, g, b, a = raw[i], raw[i+1], raw[i+2], raw[i+3]
            argb.append(a)
            argb.append(r)
            argb.append(g)
            argb.append(b)

        # Compress with PNG (run-length is simpler but PNG works)
        import io
        png_buf = io.BytesIO()
        img.save(png_buf, format="PNG")
        png_data = png_buf.getvalue()

        # icns entry: type(4) + size(4) + data
        if sz == 16:   etype = b"icp4"
        elif sz == 32:  etype = b"icp5"
        elif sz == 64:  etype = b"icp6"
        elif sz == 128: etype = b"ic07"
        elif sz == 256: etype = b"ic08"
        elif sz == 512: etype = b"ic09"
        else: continue

        entry = etype + struct.pack(">I", 8 + len(png_data)) + png_data
        icon_data.append(entry)

    # Header: 'icns' + total_size
    total = 8 + sum(len(e) for e in icon_data)
    header = b"icns" + struct.pack(">I", total)

    with open(path, "wb") as f:
        f.write(header)
        for entry in icon_data:
            f.write(entry)

    print(f"Created {path} ({total} bytes, {len(SIZES)} sizes)")

write_icns(OUTPUT)

#!/usr/bin/env python3
"""Generate the Mouse Jiggler icon as a proper multi-resolution .ico file.

Works around Pillow's lack of multi-frame ICO support by manually
constructing the ICO container format.
"""

import struct
import io
from PIL import Image, ImageDraw

SIZES = [16, 32, 48, 256]
OUTPUT = "mouse_jiggler.ico"


def draw_icon(size: int) -> Image.Image:
    """Draw a polished mouse cursor icon at the given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size
    body = [
        (s * 0.12, s * 0.08), (s * 0.12, s * 0.72),
        (s * 0.36, s * 0.56), (s * 0.54, s * 0.82),
        (s * 0.72, s * 0.72), (s * 0.40, s * 0.44),
        (s * 0.68, s * 0.30),
    ]
    draw.polygon(body, fill="#4CAF50", outline="#2E7D32")
    highlight = [
        (s * 0.18, s * 0.20), (s * 0.18, s * 0.64),
        (s * 0.34, s * 0.50), (s * 0.48, s * 0.72),
        (s * 0.64, s * 0.64), (s * 0.38, s * 0.42),
        (s * 0.60, s * 0.32),
    ]
    draw.polygon(highlight, fill="#66BB6A")
    shine = [
        (s * 0.15, s * 0.12), (s * 0.15, s * 0.25),
        (s * 0.58, s * 0.25), (s * 0.60, s * 0.18),
    ]
    draw.polygon(shine, fill=(255, 255, 255, 100))
    dot_r = max(2, int(s * 0.04))
    for i, (dx, dy) in enumerate([(0.80, 0.85), (0.88, 0.82), (0.92, 0.88)]):
        x, y = int(s * dx), int(s * dy)
        draw.ellipse(
            [x - dot_r, y - dot_r, x + dot_r, y + dot_r],
            fill=(129, 199, 132, 220 - i * 50),
        )
    return img


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def image_to_bmp_bytes(img: Image.Image) -> bytes:
    w, h = img.size
    pixels = img.convert("RGBA").tobytes()
    bmp_data = bytearray()
    for y in range(h - 1, -1, -1):
        row_start = y * w * 4
        for x in range(w):
            idx = row_start + x * 4
            r, g, b, a = pixels[idx:idx + 4]
            bmp_data.extend([b, g, r, a])
    xor_mask = bytes(bmp_data)
    and_row_bytes = (w + 7) // 8
    and_mask = bytearray(and_row_bytes * h)
    for y in range(h):
        for x in range(w):
            idx = ((h - 1 - y) * w + x) * 4
            if pixels[idx + 3] < 128:
                byte_idx = y * and_row_bytes + x // 8
                bit_idx = 7 - (x % 8)
                and_mask[byte_idx] |= (1 << bit_idx)
    bmp_header = struct.pack(
        "<IiiHHIIiiII",
        40, w, h * 2, 1, 32, 0,
        len(xor_mask) + len(and_mask), 0, 0, 0, 0,
    )
    return bmp_header + xor_mask + bytes(and_mask)


def build_ico(images: list[Image.Image]) -> bytes:
    count = len(images)
    header = struct.pack("<HHH", 0, 1, count)
    entries = []
    image_datas = []
    offset = 6 + count * 16
    for img in images:
        w, h = img.size
        entry_w = w if w < 256 else 0
        entry_h = h if h < 256 else 0
        data = image_to_png_bytes(img) if w >= 256 else image_to_bmp_bytes(img)
        image_datas.append(data)
        entry = struct.pack(
            "<BBBBHHII",
            entry_w, entry_h, 0, 0, 1, 32, len(data), offset,
        )
        entries.append(entry)
        offset += len(data)
    return header + b"".join(entries) + b"".join(image_datas)


def main():
    images = [draw_icon(s) for s in SIZES]
    ico_data = build_ico(images)
    with open(OUTPUT, "wb") as f:
        f.write(ico_data)
    print(f"Saved {OUTPUT} — {len(images)} frames, {len(ico_data)} bytes")


if __name__ == "__main__":
    main()

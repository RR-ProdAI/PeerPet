"""Dev-only: render every pixel-art frame to a PNG contact sheet.

Lets you review/iterate on `pet/pixel_sprites.py` art without a sixel terminal:

    python tools/preview_frames.py [out.png]

Writes one image with a row per animation (happy idle, sad idle, feed, play,
pet, HUD sample). Pure stdlib (zlib + struct), like everything else here; this
file ships in the repo but not in the wheel.
"""

from __future__ import annotations

import struct
import sys
import zlib

from peerpet.pet import pixel_sprites as px
from peerpet.pet.state import Mood

SCALE = 6
GAP = 8
BACKGROUND = (30, 30, 40)


def _png(width: int, height: int, rgb_rows: list[list[tuple[int, int, int]]]) -> bytes:
    raw = b"".join(b"\x00" + bytes(c for px_ in row for c in px_) for row in rgb_rows)

    def chunk(tag: bytes, payload: bytes) -> bytes:
        data = tag + payload
        return struct.pack(">I", len(payload)) + data + struct.pack(">I", zlib.crc32(data))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _sheet(rows_of_frames: list[list[list[str]]]) -> bytes:
    frame_w = max(len(f[0]) for row in rows_of_frames for f in row)
    cols = max(len(row) for row in rows_of_frames)
    cell_w = frame_w * SCALE + GAP
    heights = [max(len(f) for f in row) * SCALE + GAP for row in rows_of_frames]
    width, height = GAP + cols * cell_w, GAP + sum(heights)

    pixels = [[BACKGROUND] * width for _ in range(height)]
    y0 = GAP
    for row, row_h in zip(rows_of_frames, heights, strict=True):
        for col, frame in enumerate(row):
            x0 = GAP + col * cell_w
            for fy, line in enumerate(frame):
                for fx, key in enumerate(line):
                    if key == ".":
                        continue
                    color = px.PALETTE[key]
                    for sy in range(SCALE):
                        for sx in range(SCALE):
                            pixels[y0 + fy * SCALE + sy][x0 + fx * SCALE + sx] = color
        y0 += row_h
    return _png(width, height, pixels)


def main() -> int:
    out = sys.argv[1] if len(sys.argv) > 1 else "tools/preview.png"
    sheet = _sheet(
        [
            px.FRAMES[Mood.HAPPY],
            px.FRAMES[Mood.SAD],
            px.REACTIONS["feed"],
            px.REACTIONS["play"],
            px.REACTIONS["pet"],
            [px.hud(80, 60), px.hud(25, 10), px.hud(100, 100)],
        ]
    )
    with open(out, "wb") as f:
        f.write(sheet)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

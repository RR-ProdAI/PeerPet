"""Sixel image encoding — pixel graphics for terminals that support it.

Like `region.py`, this module only *builds* escape strings; callers decide
where to write them. It is the second (and last) place in the codebase allowed
to construct raw escape sequences — see AGENTS.md.

A sixel image is a DCS sequence: `ESC P 0;1;0 q <raster> <palette> <data> ESC \\`.
The pixel data packs vertical strips of 6 pixels into one byte per color per
column ("sixels", chars `?`..`~`); `$` rewinds to the line start to overlay the
next color, `-` advances to the next 6-pixel band. `P2=1` makes uncovered
pixels transparent, so the pet keeps its silhouette over the terminal
background.

Input format matches `pet/pixel_sprites.py`: a grid of single-character palette
keys (one string per pixel row) plus a palette mapping keys to RGB. This keeps
the encoder a pure, unit-testable function of strings.
"""

from __future__ import annotations

DCS = "\x1bP"
ST = "\x1b\\"
# Grid character that means "no pixel here" (transparent).
TRANSPARENT = "."


def _color_definitions(keys: list[str], palette: dict[str, tuple[int, int, int]]) -> str:
    """Sixel palette entries: `#<index>;2;<r>;<g>;<b>` with RGB scaled 0-100."""
    parts = []
    for index, key in enumerate(keys):
        r, g, b = palette[key]
        parts.append(f"#{index};2;{r * 100 // 255};{g * 100 // 255};{b * 100 // 255}")
    return "".join(parts)


def _run_length(data: list[int]) -> str:
    """RLE-compress one band line: sixel value list -> `!<n><char>` runs."""
    out: list[str] = []
    i = 0
    while i < len(data):
        j = i
        while j < len(data) and data[j] == data[i]:
            j += 1
        run, char = j - i, chr(data[i] + 63)
        # `!<n>x` costs at least 3 chars; only pays off for runs of 4+.
        out.append(f"!{run}{char}" if run > 3 else char * run)
        i = j
    return "".join(out)


def encode(
    grid: list[str],
    palette: dict[str, tuple[int, int, int]],
    scale: int = 1,
) -> str:
    """Encode a palette-keyed pixel grid as a complete sixel sequence.

    `scale` integer-zooms the grid (each logical pixel becomes a scale x scale
    block) so chunky pixel art stays chunky instead of tiny.
    """
    if scale > 1:
        grid = ["".join(ch * scale for ch in row) for row in grid for _ in range(scale)]

    height = len(grid)
    width = len(grid[0]) if grid else 0
    keys = sorted({ch for row in grid for ch in row if ch != TRANSPARENT})
    color_of = {key: index for index, key in enumerate(keys)}

    bands: list[str] = []
    for top in range(0, height, 6):
        rows = grid[top : top + 6]
        band_parts: list[str] = []
        for key, index in color_of.items():
            # Bit n of a sixel = pixel n rows below the band top.
            line = [
                sum(1 << n for n, row in enumerate(rows) if row[x] == key) for x in range(width)
            ]
            if any(line):
                band_parts.append(f"#{index}" + _run_length(line))
        bands.append("$".join(band_parts))

    raster = f'"1;1;{width};{height}'
    return f"{DCS}0;1;0q{raster}{_color_definitions(keys, palette)}{'-'.join(bands)}-{ST}"

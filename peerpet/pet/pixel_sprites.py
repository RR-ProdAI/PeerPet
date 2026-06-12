"""Pixel-art sprite frames per mood — the sixel (graphics) twin of `sprites.py`.

Same contract as the text art: ALL art lives here, one dict mood -> frames,
every frame of every mood/reaction is the SAME size (WIDTH x HEIGHT) so the pet
never jumps. A frame is a list of HEIGHT strings of WIDTH palette keys, one
character per pixel; `host/sixel.encode` turns a frame into pixels.

The creature is a Tamagotchi-style blob: a rounded body with big eyes, blush,
nub feet, and a soft bob. Frames are *composed*, not hand-drawn one by one: the
body is rasterized from a half-width profile (then shaded, highlighted and
outlined in code), and small hand-drawn stamps (eyes, mouths, hearts, snack,
ball) are placed on top. To restyle the pet, edit the profile, the palette, or
the stamps — every frame updates together.

Preview any change with `python tools/preview_frames.py` (writes PNGs) or
`peerpet demo` in a sixel terminal.
"""

from __future__ import annotations

from peerpet.pet.state import Mood

Frame = list[str]

WIDTH = 36
HEIGHT = 30

PALETTE: dict[str, tuple[int, int, int]] = {
    "K": (43, 36, 56),  # outline
    "B": (104, 211, 169),  # body
    "b": (66, 162, 128),  # body shade
    "H": (214, 247, 227),  # body highlight
    "W": (250, 250, 250),  # eye white
    "E": (43, 36, 56),  # pupil
    "P": (244, 145, 160),  # blush
    "M": (122, 62, 75),  # mouth
    "R": (235, 84, 110),  # hearts
    "Y": (249, 198, 86),  # snack / ball
    "O": (236, 124, 62),  # snack chips / ball stripe
    "D": (74, 70, 94),  # HUD empty-bar fill
}

_T = "."  # transparent, matches sixel.TRANSPARENT

# --- body ------------------------------------------------------------------
# The blob silhouette as half-widths per row (so it stays symmetric). Rows 0-7
# above the body are prop space (hearts float there); the feet sit below.
_CX = 18
_BODY_TOP = 8
_BODY_HALF = [4, 6, 8, 9, 10, 10, 11, 11, 11, 11, 11, 11, 10, 10, 9, 8, 7, 6]

# --- feature stamps ---------------------------------------------------------
# Small hand-drawn pieces placed onto the body. `.` = leave canvas untouched.
_EYES: dict[str, list[str]] = {
    # Big DS-style oval eye: tall dark pupil with a glint in its corner.
    "open": [
        ".KKKK.",
        "KWWWWK",
        "KWHEWK",
        "KWEEWK",
        "KWEEWK",
        "KWWWWK",
        ".KKKK.",
    ],
    "blink": [
        "......",
        "......",
        "......",
        "KKKKKK",
        "......",
        "......",
        "......",
    ],
    # Sad: heavy lid pressing down, pupil sunk low.
    "sad": [
        ".KKKK.",
        "KKKKKK",
        "KWWWWK",
        "KWHEWK",
        "KWEEWK",
        "KWWWWK",
        ".KKKK.",
    ],
    # Joy: closed happy arches (^ ^), used while being petted.
    "joy": [
        "......",
        "..KK..",
        ".KKKK.",
        "KK..KK",
        "......",
        "......",
        "......",
    ],
}

_MOUTHS: dict[str, list[str]] = {
    "smile": [
        "M.....M",
        "MM...MM",
        ".MMMMM.",
    ],
    "frown": [
        ".MMMMM.",
        "MM...MM",
        "M.....M",
    ],
    "open": [
        ".MMMMM.",
        "MMMMMMM",
        "MMMMMMM",
        ".MMMMM.",
    ],
    "chew": [
        ".......",
        "MMMMMMM",
        ".......",
    ],
}

_HEART = [
    ".RR.RR.",
    "RRRRRRR",
    ".RRRRR.",
    "..RRR..",
    "...R...",
]
_HEART_SMALL = [
    ".R.R.",
    "RRRRR",
    ".RRR.",
    "..R..",
]
_SNACK = [
    ".YYYY.",
    "YYOYYY",
    "YYYYOY",
    "YOYYYY",
    ".YYYY.",
]
_BALL = [
    ".OOOO.",
    "OYYYYO",
    "OYYYYO",
    "OOOOOO",
    "OYYYYO",
    ".OOOO.",
]
_FOOT = [
    "KBBBK",
    ".KKK.",
]


def _stamp(canvas: list[list[str]], x: int, y: int, art: list[str]) -> None:
    """Draw `art` onto the canvas at (x, y); `.` cells leave the canvas alone.
    Out-of-bounds pixels are clipped so props can hug the frame edges."""
    for dy, row in enumerate(art):
        for dx, ch in enumerate(row):
            if ch != _T and 0 <= y + dy < HEIGHT and 0 <= x + dx < WIDTH:
                canvas[y + dy][x + dx] = ch


def _body(canvas: list[list[str]], dy: int) -> None:
    """Rasterize the blob at vertical offset `dy` (the idle bob): fill, shade
    the lower-right, add a highlight, then trace the outline. Feet stay planted
    at the bottom so a bob reads as a squash, not a hop."""
    top = _BODY_TOP + dy
    inside = set()
    for r, hw in enumerate(_BODY_HALF):
        for x in range(_CX - hw, _CX + hw):
            inside.add((x, top + r))
    for x, y in inside:
        if (x - _CX) + (y - top) > 16:  # lower-right crescent
            canvas[y][x] = "b"
        else:
            canvas[y][x] = "B"
    for x, y in inside:
        neighbors = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
        if any(n not in inside for n in neighbors):
            canvas[y][x] = "K"
    # Sheen on the crown, stamped after the outline so it survives the pass.
    _stamp(canvas, _CX - 3, top + 1, [".HHH", "HH.."])
    _stamp(canvas, _CX - 9, _BODY_TOP + len(_BODY_HALF), _FOOT)
    _stamp(canvas, _CX + 4, _BODY_TOP + len(_BODY_HALF), _FOOT)


def _compose(
    eyes: str,
    mouth: str,
    dy: int = 0,
    blush: bool = True,
    props: list[tuple[int, int, list[str]]] | None = None,
) -> Frame:
    """Build one full frame: body at bob offset `dy`, a face, optional blush,
    and any extra prop stamps (hearts, snack, ball) at absolute positions."""
    canvas = [[_T] * WIDTH for _ in range(HEIGHT)]
    _body(canvas, dy)
    top = _BODY_TOP + dy
    _stamp(canvas, _CX - 9, top + 4, _EYES[eyes])
    _stamp(canvas, _CX + 3, top + 4, _EYES[eyes])
    _stamp(canvas, _CX - 3, top + 12, _MOUTHS[mouth])
    if blush:
        _stamp(canvas, _CX - 10, top + 11, ["PP"])
        _stamp(canvas, _CX + 8, top + 11, ["PP"])
    for x, y, art in props or []:
        _stamp(canvas, x, y, art)
    return ["".join(row) for row in canvas]


# --- idle loops --------------------------------------------------------------
# Mostly-still, like the text art: a slow 2-frame bob with one blink per cycle.
# At ~0.5s per step the pet breathes every couple seconds and blinks every ~4s.
_HAPPY_REST = _compose("open", "smile")
_HAPPY_BOB = _compose("open", "smile", dy=1)
_HAPPY_BLINK = _compose("blink", "smile")
_SAD_REST = _compose("sad", "frown", blush=False)
_SAD_BOB = _compose("sad", "frown", dy=1, blush=False)
_SAD_BLINK = _compose("blink", "frown", blush=False)

_HAPPY_IDLE = [_HAPPY_REST, _HAPPY_REST, _HAPPY_BOB, _HAPPY_BOB] * 2
_HAPPY_IDLE[6] = _HAPPY_BLINK
_SAD_IDLE = [_SAD_REST, _SAD_REST, _SAD_BOB, _SAD_BOB] * 2
_SAD_IDLE[6] = _SAD_BLINK

FRAMES: dict[Mood, list[Frame]] = {
    Mood.HAPPY: _HAPPY_IDLE,
    Mood.CONTENT: _HAPPY_IDLE,
    Mood.SAD: _SAD_IDLE,
    Mood.HUNGRY: _SAD_IDLE,
    Mood.SLEEPY: _SAD_IDLE,
}

# --- one-shot reactions -------------------------------------------------------
# Props live in the empty margins (rows 0-7 above the head, columns beside the
# body), so reaction frames stay the standard size.
_SNACK_AT_MOUTH = (1, _BODY_TOP + 12, _SNACK)
REACTIONS: dict[str, list[Frame]] = {
    # A snack floats in; the pet opens wide, chews, and beams.
    "feed": [
        _compose("open", "open", props=[_SNACK_AT_MOUTH]),
        _compose("open", "chew", dy=1, props=[_SNACK_AT_MOUTH]),
        _compose("blink", "chew"),
        _compose("joy", "smile", dy=1),
    ],
    # A ball bounces up the right margin; the pet bobs along.
    "play": [
        _compose("open", "open", props=[(30, 22, _BALL)]),
        _compose("open", "smile", dy=1, props=[(30, 12, _BALL)]),
        _compose("joy", "open", props=[(30, 2, _BALL)]),
        _compose("open", "smile", dy=1, props=[(30, 12, _BALL)]),
    ],
    # Hearts pop above the head while the eyes squeeze shut with joy.
    "pet": [
        _compose("joy", "smile", props=[(8, 2, _HEART_SMALL), (24, 3, _HEART_SMALL)]),
        _compose("joy", "open", dy=1, props=[(7, 1, _HEART), (23, 2, _HEART_SMALL)]),
        _compose("joy", "smile", props=[(8, 2, _HEART_SMALL), (22, 1, _HEART)]),
    ],
}


def frame_for(mood: Mood, tick: int) -> Frame:
    """Return the pixel frame for a mood at animation step `tick`."""
    frames = FRAMES.get(mood, FRAMES[Mood.HAPPY])
    return frames[tick % len(frames)]


def reaction_frames(command: str) -> list[Frame]:
    """Reaction sequence for a command, or [] for unknown commands (same
    contract as `sprites.reaction_frames`: empty list means stay idle)."""
    return REACTIONS.get(command, [])


# --- HUD ---------------------------------------------------------------------
# Stat bars drawn as pixels so the demo reads as a game, not a status line.
# Appended below a sprite frame by the renderer; same WIDTH, so the combined
# grid stays rectangular.
_HUD_ICONS = {
    "happiness": ("R", ["R.R", "RRR", ".R."]),
    "hunger": ("Y", ["YYY", "YOY", "YYY"]),
}
_BAR_X = 5  # bar starts after the 3px icon + 1px gap
_BAR_INNER = WIDTH - _BAR_X - 2  # interior pixels between the 1px borders


def hud(happiness: float, hunger: float) -> list[str]:
    """Render the two stat bars as a WIDTH-wide pixel strip (icon + bar each)."""
    rows: list[list[str]] = []
    for name, value in (("happiness", happiness), ("hunger", hunger)):
        fill_key, icon = _HUD_ICONS[name]
        filled = round(max(0.0, min(100.0, value)) / 100 * _BAR_INNER)
        inner = fill_key * filled + "D" * (_BAR_INNER - filled)
        bar = [
            ["K" * (_BAR_INNER + 2)],
            ["K" + inner + "K"],
            ["K" * (_BAR_INNER + 2)],
        ]
        for i in range(3):
            row = [_T] * WIDTH
            for dx, ch in enumerate(icon[i]):
                row[dx] = ch if ch != "." else _T
            for dx, ch in enumerate(bar[i][0]):
                row[_BAR_X + dx] = ch
            rows.append(row)
        rows.append([_T] * WIDTH)  # spacer between bars
    return ["".join(r) for r in rows[:-1]]  # drop the trailing spacer

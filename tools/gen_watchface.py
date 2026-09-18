#!/usr/bin/env python3
"""
Quinary (base-5) Watch Face generator.

One layout spec -> two outputs:
  * app/src/main/res/raw/watchface.xml   Wear OS Watch Face Format (WFF), v2
  * preview.html                          live browser preview, no build needed

Sibling of ../BinaryWatchFace/tools/gen_watchface.py, same one-spec-two-
outputs approach. Time is shown as the raw H/M/S values converted straight
to base-5 ("quinary") positional digits -- the base-5 analog of
BinaryWatchFace's raw-bit "Binary" mode (not its decimal "BCD" mode). Each
digit (0-4) is a group of 4 fixed-color sub-cells; the COUNT of lit
(colored, not background) sub-cells encodes the digit value, lighting up
in Cartesian-quadrant order as the digit counts up:
    digit 0: (none lit)              digit 1: TR
    digit 2: TR TL                   digit 3: TR TL BL
    digit 4: TR TL BL BR
Each sub-cell position keeps the same fixed color across every digit group
(never user-configurable -- unlike BinaryWatchFace's single pickable LED
color) so the eye learns the color/position -> digit-value pattern the same
way regardless of row. What DOES vary by row is the outer SHAPE (2026-09-17,
per Paul: "color and position with digits, shape with the type" -- so the
silhouette alone identifies which row you're looking at):
    H -- wide rectangles ("bar"), stretched edge-to-edge since it only ever
         needs 2 places and would otherwise look cramped/off-balance
         against M/S's 3
    M -- rounded rectangles ("rounded"), deliberately between H's sharp
         corners and S's full circle
    S -- one four-part circle ("pie"), 4 pie-slice quadrants that fuse into
         a seamless disc when fully lit
"Off" sub-cells are not drawn at all -- the background IS the neutral/off
state, per the design brief -- so there's no dim-LED placeholder to draw,
unlike BinaryWatchFace's always-on dim dot. A faint dashed outline in each
row's own shape marks every digit-group's footprint at all times, so the
eye can find all 8 groups even when most are unlit.

  H  (0-23) needs 2 places: floor(H/5)%5 (0-4), H%5 (0-4)
  M  (0-59) needs 3 places: floor(M/25)%5 (0-2), floor(M/5)%5 (0-4), M%5 (0-4)
  S  (0-59) needs 3 places: same as M

The per-sub-cell lit test mirrors BinaryWatchFace's complication-visibility
expressions (which already use comparison operators like `!=` inside a
named <Expression>, tested for truthiness via <Compare expression="...">)
rather than its per-bit `bit_expr` (which avoids comparison operators
entirely) -- here the comparison is `digit > k` for sub-cell index k (0..3):
      lit = (digit > k)
"""

import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "app" / "src" / "main" / "res" / "raw" / "watchface.xml"
PREVIEW = ROOT / "preview.html"
HEART_ICON = ROOT / "app" / "src" / "main" / "res" / "drawable" / "heart_icon.png"
PREVIEW_IMG = ROOT / "app" / "src" / "main" / "res" / "drawable" / "preview.png"

# ---- geometry -------------------------------------------------------------
CANVAS = 450
C = CANVAS / 2
RADIUS = CANVAS / 2

QUAD = 72               # M/S digit-group footprint (width == height)
WEDGE_R = QUAD / 2      # radius of the full circle S's pie-wedge groups
                         # form when all 4 quadrants are lit
SUB_GAP = 0             # gap between the 4 sub-cells within one digit group
                         # -- zero (2026-09-17) so H's rectangles and M's
                         # rounded corners tile into one seamless shape when
                         # fully lit, the same "4 quadrants of ONE shape"
                         # construction S's pie-wedge Arc already used;
                         # only the corner radius now varies row to row.
HOUR_RADIUS = 8         # H's corner radius -- a little rounding (2026-09-17
                         # follow-up: H started fully sharp, Paul asked for
                         # a touch of softening once M/S were in place)
MINUTE_RADIUS = 24      # M's corner radius -- more rounded than H, still
                         # short of S's full circle, "soft rectangles" per
                         # Paul's rectangle -> rounded box -> circle
                         # progression (bumped from 16, still not enough)
QUAD_PITCH = 88         # horizontal distance between M/S digit-group
                         # centers in a row
ROW_Y = {0: 162, 1: 249, 2: 336}        # H, M, S row centers -- picked to
                                         # clear the widget slots (bottom
                                         # edge 116) and the date slot (top
                                         # edge 382); verified below.

# M/S are right-aligned on their base-5 PLACE, not centered independently:
# every row's "ones" group (place 0) sits at RIGHT_EDGE_X, its "fives"
# group (place 1) one pitch to the left, and so on -- so the ones/fives/25s
# columns line up vertically across M/S, same idea as BinaryWatchFace's BCD
# columns sharing a baseline. M/S's combined span is 2*QUAD_PITCH+QUAD=248,
# symmetric about canvas center C (RIGHT_EDGE_X=C+QUAD_PITCH).
RIGHT_EDGE_X = 313

# H stretches to match that same 248px span instead of right-aligning
# (2026-09-17, per Paul: "the top two boxes [should be] the same width as
# three of the circles below") -- so H's left/right edges land EXACTLY on
# M/S's (101 and 349), not just the same total width.
HOUR_H = 72
HOUR_GAP = 24           # bumped from 8 (2026-09-17: wanted a touch more
                         # breathing room between the two boxes)
HOUR_TOTAL_W = 2 * QUAD_PITCH + QUAD          # = 248, matches M/S's span
HOUR_W = (HOUR_TOTAL_W - HOUR_GAP) // 2        # integer: PartDraw needs int

# widget slots (top corners + date, unchanged from BinaryWatchFace)
DATE_X, DATE_Y, DATE_W, DATE_H = 125, 382, 200, 36
WIDGET_W, WIDGET_H = 120, 68
WIDGET_Y = 48
WIDGET_MARGIN_X = 98

LABEL_GAP = 10          # gap between a row's leftmost group and its label
LABEL_W, LABEL_H = 36, 36

# All three rows now share the same left edge (101) as well as the same
# width, so one label position works for all of them -- back on the LEFT
# (2026-09-17: labels had briefly moved to the right when M/S were
# right-aligned; restored on the left, including H's, now that everything
# shares this edge).
ROW_LEFT_EDGE_X = RIGHT_EDGE_X + QUAD // 2 - HOUR_TOTAL_W      # = 101
LABEL_X = ROW_LEFT_EDGE_X - LABEL_GAP - LABEL_W // 2

# ---- color themes -----------------------------------------------------
# Position order is fixed: TR, TL, BL, BR -- matches the Cartesian-quadrant
# lighting order (digit 1 lights TR only, digit 4 lights all four). Palette
# is Okabe-Ito-derived, per Paul's brief (colorblind-safe).
THEMES = {
    "dark": dict(
        bg="#FF111111",
        label="#FF808080",
        outline="#99FFFFFF",           # dashed placeholder outline, ~60% white
                                        # (2026-09-17: bumped from ~25%, too subtle)
        blocks=["#FFFFFFFF", "#FF56B4E9", "#FFE69F00", "#FF009E73"],
    ),
    "light": dict(
        bg="#FFFFFFFF",
        label="#FF808080",
        outline="#99111111",           # dashed placeholder outline, ~60% black
        blocks=["#FF111111", "#FF0072B2", "#FFD55E00", "#FFCC79A7"],
    ),
}
POSITIONS = ["TR", "TL", "BL", "BR"]
POS_SIGN = {"TR": (+1, -1), "TL": (-1, -1), "BL": (-1, +1), "BR": (+1, +1)}
# Arc angles: WFF's Arc measures degrees clockwise from 12 o'clock, so each
# 90-degree quadrant maps directly onto compass-style TR/BR/BL/TL sweeps.
POS_ANGLES = {"TR": (0, 90), "BR": (90, 180), "BL": (180, 270), "TL": (270, 360)}


def places_needed(max_value: int) -> int:
    """How many base-5 digits are needed to represent 0..max_value."""
    n = 1
    while 5 ** n <= max_value:
        n += 1
    return n


def quad_digit_expr(value_expr: str, place: int) -> str:
    """WFF arithmetic yielding the base-5 digit (0-4) at `place` (0 = ones)."""
    return f"round(floor(({value_expr}) / {5 ** place}) % 5)"


# ---- layout: yields dicts {x, y, w, h, shape, radius, place, expr, label,
# label_x, label_y} ----
def hour_layout():
    """Two wide bars, 50/50, spanning the same total width as M/S's
    3-circle row (HOUR_TOTAL_W == 2*QUAD_PITCH+QUAD) and centered so their
    left/right edges land exactly on M/S's -- H only ever needs 2 base-5
    places (max value 23), so unlike M/S it stretches to match rather than
    right-aligning on place value. Label ("H") sits on the leftmost bar,
    at the shared LABEL_X -- same left-side convention as M/S."""
    cy = ROW_Y[0]
    total_w = 2 * HOUR_W + HOUR_GAP
    left_x = C - total_w / 2 + HOUR_W / 2
    right_x = C + total_w / 2 - HOUR_W / 2
    for col, cx in enumerate((left_x, right_x)):
        place = 1 - col                  # most-significant place on the left
        yield dict(x=cx, y=cy, w=HOUR_W, h=HOUR_H, shape="bar", radius=HOUR_RADIUS,
                   place=place, expr="[HOUR_0_23]",
                   label="H" if col == 0 else None, label_x=LABEL_X, label_y=cy)


def quad_layout():
    """M (rounded rectangles) and S (pie-wedge circles), right-aligned on
    base-5 place value -- every row's "ones" group (place 0) sits at
    RIGHT_EDGE_X, "fives" one pitch to the left, and so on. Label sits on
    the leftmost (most-significant-place) group, at the shared LABEL_X."""
    specs = [(1, "M", "[MINUTE]", 59, "rounded"), (2, "S", "[SECOND]", 59, "pie")]
    for row_i, label, expr, max_value, shape in specs:
        n = places_needed(max_value)
        cy = ROW_Y[row_i]
        radius = MINUTE_RADIUS if shape == "rounded" else 0
        for col in range(n):
            place = n - 1 - col          # most-significant place on the left
            cx = RIGHT_EDGE_X - place * QUAD_PITCH
            yield dict(x=cx, y=cy, w=QUAD, h=QUAD, shape=shape, radius=radius,
                       place=place, expr=expr,
                       label=label if col == 0 else None,
                       label_x=LABEL_X, label_y=cy)


def full_layout():
    return list(hour_layout()) + list(quad_layout())


def _check_fits_clip(boxes):
    """Every box's farthest corner must stay inside the circular clip --
    checked against the actual corner distance, not just the square canvas
    (same lesson as BinaryWatchFace's complication placement). `boxes` is
    an iterable of (cx, cy, half_w, half_h, name)."""
    for cx, cy, hw, hh, name in boxes:
        corner_x = cx + hw if cx >= C else cx - hw
        corner_y = cy + hh if cy >= C else cy - hh
        dist = math.hypot(corner_x - C, corner_y - C)
        if dist > RADIUS:
            raise AssertionError(f"{name} at ({cx},{cy}) clips the circle: {dist:.1f} > {RADIUS}")


def _layout_check_boxes(layout):
    for c in layout:
        yield (c["x"], c["y"], c["w"] / 2, c["h"] / 2, f'{c["shape"]}@({c["x"]},{c["y"]})')
        if c["label"]:
            yield (c["label_x"], c["label_y"], LABEL_W / 2, LABEL_H / 2, f'label {c["label"]}')


# ======================================================================
# WFF  (res/raw/watchface.xml)
# ======================================================================
def wff_quad_outlines(layout, palette):
    """A dashed, always-visible outline at each digit-group's full
    footprint, IN THAT ROW'S OWN SHAPE (rectangle/rounded/circle) --
    scaffolding so the eye can find all 8 groups at a glance, even when
    most sub-cells are unlit and there's nothing else marking their
    bounds. Static (not gated by a Condition) and drawn before the lit
    sub-cells so those layer cleanly on top."""
    out = []
    for c in layout:
        x, y = round(c["x"] - c["w"] / 2), round(c["y"] - c["h"] / 2)
        stroke = (f'<Stroke color="{palette["outline"]}" thickness="1.5" '
                  f'dashIntervals="3 5" cap="ROUND"/>')
        if c["shape"] == "pie":
            shape_el = f'<Ellipse x="0" y="0" width="{c["w"]}" height="{c["h"]}">{stroke}</Ellipse>'
        elif c["radius"] > 0:
            shape_el = (f'<RoundRectangle x="0" y="0" width="{c["w"]}" height="{c["h"]}" '
                        f'cornerRadiusX="{c["radius"]}" cornerRadiusY="{c["radius"]}">{stroke}</RoundRectangle>')
        else:
            shape_el = f'<Rectangle x="0" y="0" width="{c["w"]}" height="{c["h"]}">{stroke}</Rectangle>'
        out.append(
            f'      <PartDraw x="{x}" y="{y}" width="{c["w"]}" height="{c["h"]}">\n'
            f'        {shape_el}\n'
            f'      </PartDraw>')
    return "\n".join(out)


def wff_quads(layout, palette):
    """Each digit group is 4 sub-cells in Cartesian-quadrant order (TR, TL,
    BL, BR), rendered in that row's own shape:
      - "pie": a circle split into 4 pie-slice quadrants. WFF's <Arc> only
        draws a STROKE (no Fill), so each wedge is a thick WeightedStroke
        traced along a circle of radius WEDGE_R/2 with thickness=WEDGE_R --
        the stroke then spans from the center (0) out to the full radius,
        filling the wedge solid. cap="BUTT" keeps the radial edges flat so
        adjacent wedges meet with no rounded overlap at the seams.
      - "bar"/"rounded": 4 sub-rectangles in a 2x2 grid within the group's
        w x h box (same TR/TL/BL/BR offsets as BinaryWatchFace's original
        block layout, generalized to non-square cells -- H's bars are much
        wider than tall). Corner rounding is driven purely by `radius`, not
        the shape name: H uses a small HOUR_RADIUS, M a larger
        MINUTE_RADIUS, so both bar and rounded groups share the same
        rendering path. Radius > 0 rounds ONLY each sub-cell's own true
        OUTER corner (the one on the digit group's exterior), staying
        sharp on the other 3 (which face the group's own center) -- so a
        fully-lit group fuses into one seamless rounded rectangle exactly
        matching its dashed placeholder outline, the same way S's pie
        wedges fuse into one circle, rather than 4 separate pills with
        visible rounding at every inner seam. Per-corner rounding isn't a
        WFF primitive (RoundRectangle only takes one uniform radius for
        all 4 corners), so each cell draws a fully-rounded RoundRectangle
        THEN squares off the 3 unwanted corners with same-color
        radius x radius overlays -- entirely within the cell's own bounds,
        no reliance on any clipping behavior at the PartDraw edge."""
    out = []
    for c in layout:
        digit_expr = quad_digit_expr(c["expr"], c["place"])
        w, h = c["w"], c["h"]
        if c["shape"] == "pie":
            r = w / 2
            bx, by = round(c["x"] - w / 2), round(c["y"] - h / 2)
            for k, pos in enumerate(POSITIONS):
                start, end = POS_ANGLES[pos]
                name = f"q{c['place']}_{round(c['x'])}_{round(c['y'])}_{k}"
                out.append(
                    f'      <Condition>\n'
                    f'        <Expressions>\n'
                    f'          <Expression name="{name}">'
                    f'<![CDATA[(({digit_expr}) > {k})]]></Expression>\n'
                    f'        </Expressions>\n'
                    f'        <Compare expression="{name}">\n'
                    f'          <PartDraw x="{bx}" y="{by}" width="{w}" height="{h}">\n'
                    f'            <Arc centerX="{w / 2}" centerY="{h / 2}" '
                    f'width="{r}" height="{r}" '
                    f'startAngle="{start}" endAngle="{end}" direction="CLOCKWISE">\n'
                    f'              <WeightedStroke colors="{palette["blocks"][k]}" '
                    f'thickness="{r}" cap="BUTT"/>\n'
                    f'            </Arc>\n'
                    f'          </PartDraw>\n'
                    f'        </Compare>\n'
                    f'      </Condition>')
            continue

        # PartDraw's width/height must be integers (unlike the shape
        # elements nested inside it, which accept floats) -- round once
        # here so both stay consistent.
        cell_w, cell_h = round((w - SUB_GAP) / 2), round((h - SUB_GAP) / 2)
        for k, pos in enumerate(POSITIONS):
            sx, sy = POS_SIGN[pos]
            off_x = sx * (cell_w / 2 + SUB_GAP / 2)
            off_y = sy * (cell_h / 2 + SUB_GAP / 2)
            bx = round(c["x"] + off_x - cell_w / 2)
            by = round(c["y"] + off_y - cell_h / 2)
            name = f"q{c['place']}_{round(c['x'])}_{round(c['y'])}_{k}"
            color = palette["blocks"][k]
            if c["radius"] > 0:
                r = c["radius"]
                corner_xy = {
                    "TL": (0, 0),
                    "TR": (cell_w - r, 0),
                    "BL": (0, cell_h - r),
                    "BR": (cell_w - r, cell_h - r),
                }
                squares = "".join(
                    f'<Rectangle x="{cx}" y="{cy}" width="{r}" height="{r}"><Fill color="{color}"/></Rectangle>'
                    for corner, (cx, cy) in corner_xy.items() if corner != pos)
                shape_el = (
                    f'<RoundRectangle x="0" y="0" width="{cell_w}" height="{cell_h}" '
                    f'cornerRadiusX="{r}" cornerRadiusY="{r}"><Fill color="{color}"/></RoundRectangle>'
                    f'{squares}')
            else:
                shape_el = (f'<Rectangle x="0" y="0" width="{cell_w}" height="{cell_h}">'
                            f'<Fill color="{color}"/></Rectangle>')
            out.append(
                f'      <Condition>\n'
                f'        <Expressions>\n'
                f'          <Expression name="{name}">'
                f'<![CDATA[(({digit_expr}) > {k})]]></Expression>\n'
                f'        </Expressions>\n'
                f'        <Compare expression="{name}">\n'
                f'          <PartDraw x="{bx}" y="{by}" width="{cell_w}" height="{cell_h}">\n'
                f'            {shape_el}\n'
                f'          </PartDraw>\n'
                f'        </Compare>\n'
                f'      </Condition>')
    return "\n".join(out)


def wff_labels(layout, palette):
    out = []
    for c in layout:
        if not c["label"]:
            continue
        x, y = round(c["label_x"] - LABEL_W / 2), round(c["label_y"] - LABEL_H / 2)
        out.append(
            f'        <PartText x="{x}" y="{y}" width="{LABEL_W}" height="{LABEL_H}">\n'
            f'          <Text align="CENTER">\n'
            f'            <Font family="SYNC_TO_DEVICE" size="26" '
            f'weight="NORMAL" color="{palette["label"]}">{c["label"].upper()}</Font>\n'
            f'          </Text>\n'
            f'        </PartText>')
    return "\n".join(out)


def _rgb(argb: str):
    """#AARRGGBB -> (r, g, b), dropping alpha (PIL draws fully opaque)."""
    return tuple(int(argb[i:i + 2], 16) for i in (3, 5, 7))


PREVIEW_TIME = (23, 49, 3)   # H, M, S -- "a great time (very full)" per Paul


def build_preview_image():
    """Static gallery/picker thumbnail, at PREVIEW_TIME -- replaces the
    placeholder image copied from BinaryWatchFace at scaffolding time,
    which was literally its binary/BCD LED clock, not this face at all.
    Simplified rendering (uniform per-cell corner rounding, no
    seamless-fusion overlay trick, no dashed placeholder rings) since this
    is a representative icon, not the live interactive face."""
    from PIL import Image, ImageDraw
    palette = THEMES["dark"]
    img = Image.new("RGB", (CANVAS, CANVAS), _rgb(palette["bg"]))
    d = ImageDraw.Draw(img)
    h, m, s = PREVIEW_TIME
    values = {"[HOUR_0_23]": h, "[MINUTE]": m, "[SECOND]": s}
    for c in full_layout():
        digit = (values[c["expr"]] // 5 ** c["place"]) % 5
        if c["shape"] == "pie":
            r = c["w"] / 2
            box = [c["x"] - r, c["y"] - r, c["x"] + r, c["y"] + r]
            for k, pos in enumerate(POSITIONS):
                if digit <= k:
                    continue
                start, end = POS_ANGLES[pos]
                # PIL angles are 0=3 o'clock, clockwise; WFF's are 0=12
                # o'clock, clockwise -- shift by -90 to convert, then
                # normalize into [0,360) since pieslice doesn't handle
                # negative angles correctly (confirmed by test render:
                # raw negative start angles produced garbled slices).
                pil_start = (start - 90) % 360
                pil_end = (end - 90) % 360
                if pil_end <= pil_start:
                    pil_end += 360
                d.pieslice(box, pil_start, pil_end, fill=_rgb(palette["blocks"][k]))
        else:
            cell_w, cell_h = c["w"] / 2, c["h"] / 2
            # PIL's rounded_rectangle radius must be <= half the shorter
            # side or it degenerates toward an ellipse (confirmed by test
            # render: MINUTE_RADIUS=24 on a 36px cell drew circles, not
            # rounded squares) -- clamp for this simplified thumbnail only,
            # the real per-corner WFF technique has no such limit.
            radius = min(c["radius"], int(min(cell_w, cell_h) // 2))
            for k, pos in enumerate(POSITIONS):
                if digit <= k:
                    continue
                sx, sy = POS_SIGN[pos]
                cx, cy = c["x"] + sx * cell_w / 2, c["y"] + sy * cell_h / 2
                box = [cx - cell_w / 2, cy - cell_h / 2, cx + cell_w / 2, cy + cell_h / 2]
                if radius > 0:
                    d.rounded_rectangle(box, radius=radius, fill=_rgb(palette["blocks"][k]))
                else:
                    d.rectangle(box, fill=_rgb(palette["blocks"][k]))
        if c["label"]:
            tx, ty = c["label_x"], c["label_y"]
            d.text((tx, ty), c["label"], fill=_rgb(palette["label"]), anchor="mm")
    img.save(PREVIEW_IMG)


def build_heart_icon():
    """Rasterize a heart to app/src/main/res/drawable/heart_icon.png -- same
    parametric curve as BinaryWatchFace's (WFF's Image loader only handles
    raster drawables, not VectorDrawable XML). Solid white on transparent;
    tinted to the theme's block-1 color at render time via tintColor."""
    from PIL import Image, ImageDraw
    SS, SIZE = 4, 128
    S = SIZE * SS
    pts = []
    for i in range(240):
        t = 2 * math.pi * i / 240
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((x, y))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = maxx - minx, maxy - miny
    pad = 0.06
    scale = (1 - 2 * pad) * S / max(w, h)
    ox, oy = (S - w * scale) / 2, (S - h * scale) / 2

    def to_px(x, y):
        return (x - minx) * scale + ox, S - ((y - miny) * scale + oy)

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(img).polygon([to_px(x, y) for x, y in pts], fill=(255, 255, 255, 255))
    img.resize((SIZE, SIZE), Image.LANCZOS).save(HEART_ICON)


# Complications must sit as DIRECT children of <Scene> -- confirmed by the
# validator (a ComplicationSlot nested inside a Group is rejected) and
# already documented from BinaryWatchFace's own history. That means they
# can't live inside the per-theme Group/BooleanConfiguration switch the way
# the quad grid does.
#
# They ALSO don't theme-tint at all (2026-09-13->17 history: an earlier
# version tried picking the tint via a per-branch `[CONFIGURATION.theme] ==
# "FALSE"/"TRUE"` Expression comparison. Complication *data* loaded fine the
# whole time -- confirmed live in logcat, e.g. Fitbit heart-rate ticking
# 79/80/81/82bpm -- but nothing ever rendered on-device. BinaryWatchFace's
# own gotcha log only ever proved `== "TRUE"` works for a Boolean
# UserConfiguration read from an Expression; `== "FALSE"` (or reading
# [CONFIGURATION.theme] at all from OUTSIDE the structural BooleanOption
# branch it's declared for) was never actually verified anywhere, and is
# the prime suspect for the Condition silently never firing true.
# Rather than re-relitigate that, complications use ONE fixed tint instead
# -- palette["label"] is already the identical `#FF808080` in both themes,
# so there's no actual need for per-theme tinting here at all.
COMPLICATION_TINT = THEMES["dark"]["label"]


def wff_complication_date() -> str:
    return (
        f'    <ComplicationSlot x="{DATE_X}" y="{DATE_Y}" width="{DATE_W}" height="{DATE_H}" '
        f'slotId="3" displayName="slot_date" supportedTypes="SHORT_TEXT EMPTY">\n'
        f'      <DefaultProviderPolicy defaultSystemProvider="DAY_AND_DATE" defaultSystemProviderType="SHORT_TEXT"/>\n'
        f'      <BoundingRoundBox x="0" y="0" width="{DATE_W}" height="{DATE_H}" cornerRadius="8"/>\n'
        f'      <Complication type="SHORT_TEXT">\n'
        f'        <Condition>\n'
        f'          <Expressions>\n'
        f'            <Expression name="date_on"><![CDATA[[COMPLICATION.TEXT] != null]]></Expression>\n'
        f'          </Expressions>\n'
        f'          <Compare expression="date_on">\n'
        f'            <PartText x="0" y="0" width="{DATE_W}" height="{DATE_H}">\n'
        f'              <Text align="CENTER">\n'
        f'                <Font family="SYNC_TO_DEVICE" size="30" weight="NORMAL" color="{COMPLICATION_TINT}">\n'
        f'                  <Template>%s<Parameter expression="[COMPLICATION.TEXT]"/></Template>\n'
        f'                </Font>\n'
        f'              </Text>\n'
        f'            </PartText>\n'
        f'          </Compare>\n'
        f'        </Condition>\n'
        f'      </Complication>\n'
        f'    </ComplicationSlot>')


def wff_complication_heart(x: int) -> str:
    icon = 36
    text_w = WIDGET_W - icon
    return (
        f'    <ComplicationSlot x="{x}" y="{WIDGET_Y}" width="{WIDGET_W}" height="{WIDGET_H}" '
        f'slotId="1" displayName="slot_heart" supportedTypes="SHORT_TEXT EMPTY">\n'
        f'      <DefaultProviderPolicy defaultSystemProvider="HEART_RATE" defaultSystemProviderType="SHORT_TEXT"/>\n'
        f'      <BoundingRoundBox x="0" y="0" width="{WIDGET_W}" height="{WIDGET_H}" cornerRadius="12"/>\n'
        f'      <Complication type="SHORT_TEXT">\n'
        f'        <Condition>\n'
        f'          <Expressions>\n'
        f'            <Expression name="heart_on">'
        f'<![CDATA[[COMPLICATION.TEXT] != null]]></Expression>\n'
        f'          </Expressions>\n'
        f'          <Compare expression="heart_on">\n'
        f'            <PartImage x="0" y="{(WIDGET_H - icon) // 2}" width="{icon}" height="{icon}" '
        f'tintColor="{COMPLICATION_TINT}">\n'
        f'              <Image resource="heart_icon"/>\n'
        f'            </PartImage>\n'
        f'            <PartText x="{icon}" y="0" width="{text_w}" height="{WIDGET_H}">\n'
        f'              <Text align="CENTER" ellipsis="TRUE">\n'
        f'                <Font family="SYNC_TO_DEVICE" size="30" weight="NORMAL" color="{COMPLICATION_TINT}">\n'
        f'                  <Template>%s<Parameter expression="[COMPLICATION.TEXT]"/></Template>\n'
        f'                </Font>\n'
        f'              </Text>\n'
        f'            </PartText>\n'
        f'          </Compare>\n'
        f'        </Condition>\n'
        f'      </Complication>\n'
        f'    </ComplicationSlot>')


def wff_complication_weather(x: int) -> str:
    icon = 36
    text_w = WIDGET_W - icon
    icon_y = (WIDGET_H - icon) // 2
    return (
        f'    <ComplicationSlot x="{x}" y="{WIDGET_Y}" width="{WIDGET_W}" height="{WIDGET_H}" '
        f'slotId="2" displayName="slot_weather" supportedTypes="SHORT_TEXT EMPTY">\n'
        f'      <BoundingRoundBox x="0" y="0" width="{WIDGET_W}" height="{WIDGET_H}" cornerRadius="12"/>\n'
        f'      <Complication type="SHORT_TEXT">\n'
        f'        <Condition>\n'
        f'          <Expressions>\n'
        f'            <Expression name="weather_icon_text"><![CDATA['
        f'[COMPLICATION.TEXT] != null && [COMPLICATION.MONOCHROMATIC_IMAGE] != null]]></Expression>\n'
        f'            <Expression name="weather_text"><![CDATA['
        f'[COMPLICATION.TEXT] != null && [COMPLICATION.MONOCHROMATIC_IMAGE] == null]]></Expression>\n'
        f'          </Expressions>\n'
        f'          <Compare expression="weather_icon_text">\n'
        f'            <PartText x="0" y="0" width="{text_w}" height="{WIDGET_H}">\n'
        f'              <Text align="CENTER" ellipsis="TRUE">\n'
        f'                <Font family="SYNC_TO_DEVICE" size="30" weight="NORMAL" color="{COMPLICATION_TINT}">\n'
        f'                  <Template>%s<Parameter expression="[COMPLICATION.TEXT]"/></Template>\n'
        f'                </Font>\n'
        f'              </Text>\n'
        f'            </PartText>\n'
        f'            <PartImage x="{text_w}" y="{icon_y}" width="{icon}" height="{icon}" tintColor="{COMPLICATION_TINT}">\n'
        f'              <Image resource="[COMPLICATION.MONOCHROMATIC_IMAGE]"/>\n'
        f'            </PartImage>\n'
        f'          </Compare>\n'
        f'          <Compare expression="weather_text">\n'
        f'            <PartText x="0" y="0" width="{WIDGET_W}" height="{WIDGET_H}">\n'
        f'              <Text align="CENTER" ellipsis="TRUE">\n'
        f'                <Font family="SYNC_TO_DEVICE" size="30" weight="NORMAL" color="{COMPLICATION_TINT}">\n'
        f'                  <Template>%s<Parameter expression="[COMPLICATION.TEXT]"/></Template>\n'
        f'                </Font>\n'
        f'              </Text>\n'
        f'            </PartText>\n'
        f'          </Compare>\n'
        f'        </Condition>\n'
        f'      </Complication>\n'
        f'    </ComplicationSlot>')


# NOTE: a 4th "EXTRA" complication slot briefly lived here (2026-09-17,
# in the space right-aligning the hour row freed up on its left) but was
# removed the same session once H switched to full-width bars -- that space
# no longer exists. See project_quinarywatchface memory for where a future
# 4th slot might go instead; nothing currently occupies slotId 4.


def theme_group(name: str, palette: dict, layout, labels: bool) -> str:
    """Background + quads + labels for one theme. Complications are NOT
    included here -- a ComplicationSlot is only valid as a direct child of
    <Scene> (confirmed by the offline validator: nesting one inside a Group
    is rejected), so they're generated once at Scene level instead, with a
    single fixed tint (COMPLICATION_TINT) rather than a per-theme one."""
    outlines = wff_quad_outlines(layout, palette)
    cells = wff_quads(layout, palette)
    body = f"""    <Group name="{name}" x="0" y="0" width="{CANVAS}" height="{CANVAS}">
      <PartDraw x="0" y="0" width="{CANVAS}" height="{CANVAS}">
        <Rectangle x="0" y="0" width="{CANVAS}" height="{CANVAS}"><Fill color="{palette['bg']}"/></Rectangle>
      </PartDraw>
{outlines}
{cells}"""
    if labels:
        body += f"""
      <BooleanConfiguration id="labels">
        <BooleanOption id="TRUE">
          <Group name="{name}_labels" x="0" y="0" width="{CANVAS}" height="{CANVAS}">
{wff_labels(layout, palette)}
          </Group>
        </BooleanOption>
      </BooleanConfiguration>"""
    body += "\n    </Group>"
    return body


def build_wff() -> str:
    layout = full_layout()
    _check_fits_clip(_layout_check_boxes(layout))
    preview_time = "%02d:%02d:%02d" % PREVIEW_TIME
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- GENERATED by tools/gen_watchface.py - do not hand-edit. -->
<WatchFace width="{CANVAS}" height="{CANVAS}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="DIGITAL"/>
  <Metadata key="PREVIEW_TIME" value="{preview_time}"/>

  <UserConfigurations>
    <BooleanConfiguration id="theme" displayName="cfg_theme" defaultValue="FALSE"/>
    <BooleanConfiguration id="labels" displayName="cfg_labels" defaultValue="TRUE"/>
  </UserConfigurations>

  <Scene>
    <!-- complications: independent of theme, and must be a direct child of
         Scene (can't nest inside the theme Group/BooleanConfiguration
         below), so each picks its own tint via an inner theme check. -->
{wff_complication_date()}
{wff_complication_heart(WIDGET_MARGIN_X)}
{wff_complication_weather(CANVAS - WIDGET_MARGIN_X - WIDGET_W)}

    <!-- theme (dark/light) is a UserConfiguration selection, not a per-frame
         value, so it's a BooleanConfiguration/BooleanOption structural
         switch, same reasoning as BinaryWatchFace's BCD/binary toggle. -->
    <BooleanConfiguration id="theme">
      <BooleanOption id="FALSE">
{theme_group("theme_dark", THEMES["dark"], layout, labels=True)}
      </BooleanOption>
      <BooleanOption id="TRUE">
{theme_group("theme_light", THEMES["light"], layout, labels=True)}
      </BooleanOption>
    </BooleanConfiguration>
  </Scene>
</WatchFace>
"""


# ======================================================================
# preview.html  (browser, live clock, no build)
# ======================================================================
_HTML_TMPL = r"""<!doctype html>
<meta charset="utf-8">
<title>Quinary Watch Face - preview</title>
<style>
  body { background:#111; color:#ccc; font:14px system-ui; text-align:center; margin:0; padding:24px; }
  svg  { border-radius:50%; box-shadow:0 0 40px #0008; }
  label { margin:0 10px; }
  .wrap { display:inline-block; }
</style>
<div class="wrap">
  <h2>Quinary Watch Face</h2>
  <svg id="face" width="360" height="360" viewBox="0 0 __CANVAS__ __CANVAS__"></svg>
  <div style="margin-top:14px">
    <label><input type="checkbox" id="theme"> light theme</label>
    <label><input type="checkbox" id="labels" checked> labels</label>
  </div>
  <p id="readout" style="color:#666"></p>
</div>
<script>
const SUB_GAP = __SUB_GAP__, LABEL_W = __LABEL_W__, LABEL_H = __LABEL_H__;
const POS_SIGN = {TR:[1,-1], TL:[-1,-1], BL:[-1,1], BR:[1,1]};
const POS_ANGLES = {TR:[0,90], BR:[90,180], BL:[180,270], TL:[270,360]};
const POSITIONS = ["TR","TL","BL","BR"];
const THEMES = __THEMES_JS__;
const LAYOUT = __LAYOUT_JS__;
const svg = document.getElementById("face");

function value(src, now) {
  const H = now.getHours(), M = now.getMinutes(), S = now.getSeconds();
  src = src.replaceAll("[HOUR_0_23]", H).replaceAll("[MINUTE]", M).replaceAll("[SECOND]", S);
  src = src.replace(/floor\(([^()]+)\)/g, (_, e) => "Math.floor(" + e + ")");
  return Function('"use strict";return (' + src + ')')();
}
function quinaryDigit(src, place, now) {
  return Math.round(Math.floor(value(src, now) / (5 ** place)) % 5);
}
function polar(cx, cy, r, deg) {
  const rad = deg * Math.PI / 180;
  return [cx + r * Math.sin(rad), cy - r * Math.cos(rad)];
}
function wedgePath(cx, cy, r, a0, a1) {
  // pie-slice from center out to the arc, matching the on-device thick-
  // stroke-arc trick: one 90-degree wedge, always a minor arc.
  const [x0, y0] = polar(cx, cy, r, a0);
  const [x1, y1] = polar(cx, cy, r, a1);
  return `M ${cx} ${cy} L ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1} Z`;
}
function cssRGBA(argb) {
  // WFF colors are #AARRGGBB; CSS/SVG hex is RRGGBBAA (alpha last), so a
  // raw AARRGGBB string as a CSS color is wrong for anything with real
  // alpha (like the faint outline) -- convert properly instead.
  const a = parseInt(argb.slice(1, 3), 16) / 255;
  const r = parseInt(argb.slice(3, 5), 16), g = parseInt(argb.slice(5, 7), 16), b = parseInt(argb.slice(7, 9), 16);
  return `rgba(${r},${g},${b},${a})`;
}
function outlineShape(c, colorCss) {
  const stroke = `fill="none" stroke="${colorCss}" stroke-width="1.5" stroke-dasharray="3 5" stroke-linecap="round"`;
  if (c.shape === "pie") return `<circle cx="${c.x}" cy="${c.y}" r="${c.w / 2}" ${stroke}/>`;
  const x = c.x - c.w / 2, y = c.y - c.h / 2;
  if (c.radius > 0) return `<rect x="${x}" y="${y}" width="${c.w}" height="${c.h}" rx="${c.radius}" ry="${c.radius}" ${stroke}/>`;
  return `<rect x="${x}" y="${y}" width="${c.w}" height="${c.h}" ${stroke}/>`;
}

function draw() {
  const now = new Date();
  const light = document.getElementById("theme").checked;
  const showLabels = document.getElementById("labels").checked;
  const palette = THEMES[light ? "light" : "dark"];
  let s = `<rect x="0" y="0" width="__CANVAS__" height="__CANVAS__" fill="${cssRGBA(palette.bg)}"/>`;
  for (const c of LAYOUT) {
    s += outlineShape(c, cssRGBA(palette.outline));
    const digit = quinaryDigit(c.src, c.place, now);
    if (c.shape === "pie") {
      const r = c.w / 2;
      POSITIONS.forEach((pos, k) => {
        if (digit <= k) return;
        const [a0, a1] = POS_ANGLES[pos];
        s += `<path d="${wedgePath(c.x, c.y, r, a0, a1)}" fill="${cssRGBA(palette.blocks[k])}"/>`;
      });
    } else {
      const cellW = (c.w - SUB_GAP) / 2, cellH = (c.h - SUB_GAP) / 2;
      const rx = c.radius;
      POSITIONS.forEach((pos, k) => {
        if (digit <= k) return;
        const [sx, sy] = POS_SIGN[pos];
        const offX = sx * (cellW / 2 + SUB_GAP / 2), offY = sy * (cellH / 2 + SUB_GAP / 2);
        const bx = c.x + offX - cellW / 2, by = c.y + offY - cellH / 2;
        s += `<rect x="${bx}" y="${by}" width="${cellW}" height="${cellH}" rx="${rx}" ry="${rx}" fill="${cssRGBA(palette.blocks[k])}"/>`;
      });
    }
    if (showLabels && c.label) {
      s += `<text x="${c.label_x}" y="${c.label_y + 8}" fill="${cssRGBA(palette.label)}" font-size="26" text-anchor="middle" font-family="system-ui">${c.label.toUpperCase()}</text>`;
    }
  }
  svg.innerHTML = s;
  document.getElementById("readout").textContent = now.toTimeString().slice(0, 8);
}
setInterval(draw, 250); draw();
</script>
"""


def build_html() -> str:
    def js_layout(layout):
        rows = []
        for c in layout:
            lab = f'"{c["label"]}"' if c["label"] else "null"
            lx = "null" if c["label_x"] is None else f'{c["label_x"]:.1f}'
            ly = "null" if c["label_y"] is None else f'{c["label_y"]:.1f}'
            rows.append(
                '{x:%.1f,y:%.1f,w:%.1f,h:%.1f,shape:"%s",radius:%d,place:%d,src:%s,label:%s,label_x:%s,label_y:%s}' % (
                    c["x"], c["y"], c["w"], c["h"], c["shape"], c["radius"], c["place"],
                    repr(c["expr"]).replace("'", '"'), lab, lx, ly))
        return "[" + ",".join(rows) + "]"

    def js_theme(palette):
        blocks = ",".join(f'"{b}"' for b in palette["blocks"])
        return (f'{{bg:"{palette["bg"]}",label:"{palette["label"]}",'
                f'outline:"{palette["outline"]}",blocks:[{blocks}]}}')

    repl = {
        "__CANVAS__": str(CANVAS),
        "__SUB_GAP__": str(SUB_GAP),
        "__LABEL_W__": str(LABEL_W),
        "__LABEL_H__": str(LABEL_H),
        "__THEMES_JS__": "{dark:%s,light:%s}" % (js_theme(THEMES["dark"]), js_theme(THEMES["light"])),
        "__LAYOUT_JS__": js_layout(full_layout()),
    }
    out = _HTML_TMPL
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def main():
    RAW.parent.mkdir(parents=True, exist_ok=True)
    HEART_ICON.parent.mkdir(parents=True, exist_ok=True)
    build_heart_icon()
    build_preview_image()
    RAW.write_text(build_wff(), encoding="utf-8")
    PREVIEW.write_text(build_html(), encoding="utf-8")
    n_groups = len(full_layout())
    print(f"wrote {HEART_ICON.relative_to(ROOT)}")
    print(f"wrote {PREVIEW_IMG.relative_to(ROOT)}")
    print(f"wrote {RAW.relative_to(ROOT)}   ({n_groups} digit groups, {n_groups * 4} sub-cells)")
    print(f"wrote {PREVIEW.relative_to(ROOT)}   (open in a browser)")


if __name__ == "__main__":
    main()

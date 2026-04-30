"""SVG/PNG rendering of tournament brackets.

Bracket line structure (horizontal / left_to_right):

  x      conn_x  conn_x+arm               next_round_x
  |         |       |                          |
  ┌─────────┐       |                          |
  │ Team A  ├───────┤                          |
  └─────────┘       │ ← vertical connector     |
                    ├─────────────────────────→ result line
  ┌─────────┐       │
  │ Team B  ├───────┘
  └─────────┘

  conn_x     = pos.x + box_width        (right edge of name box)
  conn_x+arm = pos.x + box_width + arm_length  (connector bar)
  next_round_x = pos.x + box_width + connector_length
"""

import os
import svgwrite
from svgwrite import Drawing

from .models import Match, BracketData, BYE
from .layout import MatchPos, CanvasInfo, col_width
from .style import StyleOptions

_WB_LABELS = [
    "Round 1", "Round 2", "Quarterfinal", "Semifinal", "Final",
]
_WB_LABELS_DBL = [
    "WB Round 1", "WB Round 2", "WB QF", "WB SF", "WB Final",
]
_LB_LABELS = [
    "LB Round 1", "LB Round 2", "LB Round 3", "LB Round 4",
    "LB Round 5", "LB Round 6", "LB Final",
]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def render(bracket, positions, canvas, style, direction, output_path):
    is_v = direction in ("top_to_bottom", "top_to_bottom_2col")
    dwg = _build_svg(bracket, positions, canvas, style, is_v)
    if output_path.endswith(".png"):
        tmp = output_path + "._tmp.svg"
        dwg.saveas(tmp)
        _to_png(tmp, output_path)
        os.remove(tmp)
    else:
        dwg.saveas(output_path)


def render_svg(bracket, positions, canvas, style, direction, output_path):
    is_v = direction in ("top_to_bottom", "top_to_bottom_2col")
    _build_svg(bracket, positions, canvas, style, is_v).saveas(output_path)


def render_png(bracket, positions, canvas, style, direction, output_path):
    is_v = direction in ("top_to_bottom", "top_to_bottom_2col")
    tmp = output_path + "._tmp.svg"
    _build_svg(bracket, positions, canvas, style, is_v).saveas(tmp)
    _to_png(tmp, output_path)
    os.remove(tmp)


def _to_png(svg_path, png_path):
    try:
        import cairosvg
        cairosvg.svg2png(url=svg_path, write_to=png_path)
    except ImportError as e:
        raise ImportError(
            "cairosvg is required for PNG output.  pip install cairosvg"
        ) from e


# ---------------------------------------------------------------------------
# SVG assembly
# ---------------------------------------------------------------------------

def _build_svg(bracket, positions, canvas, style, is_vertical):
    dwg = svgwrite.Drawing(size=(f"{canvas.width}px", f"{canvas.height}px"))
    dwg.viewbox(0, 0, canvas.width, canvas.height)
    dwg.add(dwg.rect(insert=(0, 0), size=(canvas.width, canvas.height),
                     fill=style.bg_color))

    wb_labels = _pick_labels(_WB_LABELS_DBL if bracket.format == "double" else _WB_LABELS,
                             len(bracket.winners_rounds))
    lb_labels = _pick_labels(_LB_LABELS, len(bracket.losers_rounds))

    # Winners bracket
    for r_idx, rnd in enumerate(bracket.winners_rounds):
        if style.show_round_labels and rnd:
            _round_label(dwg, positions[id(rnd[0])], wb_labels[r_idx], style, is_vertical)
        is_last = r_idx == len(bracket.winners_rounds) - 1 and bracket.format == "single"
        for m in rnd:
            _draw_match(dwg, m, positions[id(m)], style, is_vertical, is_last)

    # Losers bracket + Grand Final
    if bracket.format == "double":
        for r_idx, rnd in enumerate(bracket.losers_rounds):
            if style.show_round_labels and rnd:
                _round_label(dwg, positions[id(rnd[0])], lb_labels[r_idx], style, is_vertical)
            is_last = r_idx == len(bracket.losers_rounds) - 1
            for m in rnd:
                _draw_match(dwg, m, positions[id(m)], style, is_vertical, is_last)

        if bracket.grand_final:
            _draw_match(dwg, bracket.grand_final,
                        positions[id(bracket.grand_final)], style, is_vertical, is_final=True)

    return dwg


def _pick_labels(source, n):
    labels = list(source)
    while len(labels) < n:
        labels.insert(0, f"Round {len(labels) + 1}")
    return labels[-n:]


def _round_label(dwg, pos, text, style, is_vertical):
    if is_vertical:
        svg_x = pos.result_y          # LTR result_y → SVG x (horizontal centre)
        svg_y = pos.x - style.padding_top / 2  # above the round
    else:
        svg_x = pos.x + style.box_width / 2
        svg_y = style.padding_top / 2
    dwg.add(dwg.text(text, insert=(svg_x, svg_y),
                     text_anchor="middle", dominant_baseline="middle",
                     font_family=style.font_family,
                     font_size=f"{style.round_label_size}px",
                     fill=style.round_label_color))


# ---------------------------------------------------------------------------
# Per-match dispatch
# ---------------------------------------------------------------------------

def _draw_match(dwg, match, pos, style, is_vertical, is_final=False):
    if is_vertical:
        _match_v(dwg, match, pos, style, is_final)
    else:
        _match_h(dwg, match, pos, style, is_final)


# ---------------------------------------------------------------------------
# Horizontal (left_to_right) match
# ---------------------------------------------------------------------------

def _match_h(dwg, match, pos, style, is_final):
    bw = style.box_width
    arm = style.arm_length
    conn_len = style.connector_length

    # arm_x: where the vertical connector bar sits (right of box + arm gap)
    arm_x = pos.conn_x + arm          # = pos.x + bw + arm
    result_end_x = pos.conn_x + conn_len  # = pos.x + bw + conn_len  (next round left)

    t1_win = (style.highlight_winner
              and match.winner is not None
              and match.winner == match.team1)
    t2_win = (style.highlight_winner
              and match.winner is not None
              and match.winner == match.team2)
    t1_bye = match.team1 == BYE
    t2_bye = match.team2 == BYE

    # ── name boxes ────────────────────────────────────────────────────────
    _name_box_h(dwg, pos.x, pos.y1, bw, match.display_team1,
                style, highlight=t1_win, is_bye=t1_bye)
    _name_box_h(dwg, pos.x, pos.y2, bw, match.display_team2,
                style, highlight=t2_win, is_bye=t2_bye)

    # ── bracket lines ─────────────────────────────────────────────────────
    t1_color = style.winner_color if t1_win else (style.bye_line_color if t1_bye else style.line_color)
    t2_color = style.winner_color if t2_win else (style.bye_line_color if t2_bye else style.line_color)
    vc_color = style.bye_line_color if match.is_bye else style.line_color
    lw = style.line_width

    # arms: box-right-edge → arm_x
    _line(dwg, pos.conn_x, pos.y1, arm_x, pos.y1, t1_color, lw)
    _line(dwg, pos.conn_x, pos.y2, arm_x, pos.y2, t2_color, lw,
          dashed=t2_bye)

    # vertical connector bar
    _line(dwg, arm_x, pos.y1, arm_x, pos.y2, vc_color, lw,
          dashed=match.is_bye)

    # result line → next round
    if not is_final:
        rc = style.winner_color if (t1_win or t2_win) else style.line_color
        _line(dwg, arm_x, pos.result_y, result_end_x, pos.result_y, rc, lw)


def _name_box_h(dwg, x, y, bw, name, style, highlight, is_bye):
    """Draw team name box + text.  No horizontal line through the box."""
    bg_h = style.name_bg_height
    bg_y = y - bg_h / 2

    if style.circle_names and not is_bye:
        # Ellipse sized to fit the name
        cx = x + style.text_padding + len(name) * 4 + style.circle_radius
        cy = y
        rx = len(name) * 4 + style.circle_radius
        ry = style.circle_radius
        fill = style.winner_color if highlight else style.circle_color
        dwg.add(dwg.ellipse(center=(cx, cy), r=(rx, ry),
                             fill=fill, stroke="none"))
        dwg.add(dwg.text(name, insert=(cx, cy),
                         text_anchor="middle", dominant_baseline="middle",
                         font_family=style.font_family,
                         font_size=f"{style.font_size}px",
                         fill=style.circle_text_color))
    else:
        # Background rect
        if not is_bye:
            bg_fill = style.winner_color if highlight else style.name_bg_color
            dwg.add(dwg.rect(insert=(x, bg_y), size=(bw, bg_h),
                             fill=bg_fill, rx=3, ry=3))

        # Name text
        text_fill = (style.winner_text_color if highlight
                     else (style.bye_line_color if is_bye else style.text_color))
        dwg.add(dwg.text(name,
                         insert=(x + style.text_padding, y),
                         text_anchor="start", dominant_baseline="middle",
                         font_family=style.font_family,
                         font_size=f"{style.font_size}px",
                         fill=text_fill))


# ---------------------------------------------------------------------------
# Vertical (top_to_bottom) match
# ---------------------------------------------------------------------------
# In TTB mode the axes are swapped: LTR-x ↔ SVG-y, LTR-y ↔ SVG-x.
#
#   LTR pos.x        → SVG round-start-y
#   LTR pos.conn_x   → SVG round-bottom-y (bottom of name column)
#   LTR pos.y1/y2    → SVG team column centre-x
#   LTR pos.result_y → SVG result column centre-x

def _match_v(dwg, match, pos, style, is_final):
    arm = style.arm_length
    conn_len = style.connector_length

    # In TTB: "below the box" = higher SVG y value
    arm_y = pos.conn_x + arm            # SVG-y of horizontal connector bar
    result_end_y = pos.conn_x + conn_len  # SVG-y where result line ends (next round top)

    t1_win = (style.highlight_winner
              and match.winner is not None
              and match.winner == match.team1)
    t2_win = (style.highlight_winner
              and match.winner is not None
              and match.winner == match.team2)
    t1_bye = match.team1 == BYE
    t2_bye = match.team2 == BYE

    # ── name columns ──────────────────────────────────────────────────────
    _name_col_v(dwg, pos.y1, pos.x, pos.conn_x, match.display_team1,
                style, highlight=t1_win, is_bye=t1_bye)
    _name_col_v(dwg, pos.y2, pos.x, pos.conn_x, match.display_team2,
                style, highlight=t2_win, is_bye=t2_bye)

    # ── bracket lines ─────────────────────────────────────────────────────
    t1_color = style.winner_color if t1_win else (style.bye_line_color if t1_bye else style.line_color)
    t2_color = style.winner_color if t2_win else (style.bye_line_color if t2_bye else style.line_color)
    vc_color = style.bye_line_color if match.is_bye else style.line_color
    lw = style.line_width

    # arms: column bottom → arm_y (vertical arms going down)
    _line(dwg, pos.y1, pos.conn_x, pos.y1, arm_y, t1_color, lw)
    _line(dwg, pos.y2, pos.conn_x, pos.y2, arm_y, t2_color, lw, dashed=t2_bye)

    # horizontal connector bar at arm_y
    _line(dwg, pos.y1, arm_y, pos.y2, arm_y, vc_color, lw, dashed=match.is_bye)

    # result line → next round (downward)
    if not is_final:
        rc = style.winner_color if (t1_win or t2_win) else style.line_color
        _line(dwg, pos.result_y, arm_y, pos.result_y, result_end_y, rc, lw)


def _name_col_v(dwg, svg_x, svg_y_top, svg_y_bot, name, style, highlight, is_bye):
    """Draw a vertical team name column for TTB layout."""
    bg_w = style.name_bg_height   # column pixel width (reuse same setting)
    bg_x = svg_x - bg_w / 2
    col_h = svg_y_bot - svg_y_top

    if not is_bye:
        bg_fill = style.winner_color if highlight else style.name_bg_color
        dwg.add(dwg.rect(insert=(bg_x, svg_y_top), size=(bg_w, col_h),
                         fill=bg_fill, rx=3, ry=3))

    text_fill = (style.winner_text_color if highlight
                 else (style.bye_line_color if is_bye else style.text_color))
    mid_y = svg_y_top + col_h / 2
    dwg.add(dwg.text(name, insert=(svg_x, mid_y),
                     text_anchor="middle", dominant_baseline="middle",
                     font_family=style.font_family,
                     font_size=f"{style.font_size}px",
                     fill=text_fill,
                     transform=f"rotate(-90, {svg_x}, {mid_y})"))


# ---------------------------------------------------------------------------
# SVG line helper
# ---------------------------------------------------------------------------

def _line(dwg, x1, y1, x2, y2, color, width, dashed=False):
    kwargs = dict(stroke=color, stroke_width=width)
    if dashed:
        kwargs["stroke_dasharray"] = "5,3"
    dwg.add(dwg.line(start=(x1, y1), end=(x2, y2), **kwargs))

"""
Coordinate computation for tournament bracket layouts.

MatchPos stores positions in "logical LTR space":
  x        -- left edge of the name area for this match
  y1       -- y-centre of team1's row
  y2       -- y-centre of team2's row
  conn_x   -- x where the vertical bracket connector is drawn (= x + box_width)
  result_y -- y where the horizontal result line runs (midpoint of y1/y2)
  mirrored -- True for right-side halves in face_to_face layout (renderer が RTL で描画)

For top_to_bottom variants the renderer swaps (x↔y) when drawing.
For 2-col variants a vertical gap is inserted between the two halves.
For face_to_face layout the right half gets mirrored=True and is rendered RTL.
"""

from dataclasses import dataclass
from .models import BracketData
from .style import StyleOptions


@dataclass
class MatchPos:
    x: float
    y1: float
    y2: float
    conn_x: float
    result_y: float
    mirrored: bool = False


@dataclass
class CanvasInfo:
    width: float
    height: float
    lb_y_offset: float = 0.0  # y where the losers bracket starts (double elim)


def col_width(style: StyleOptions) -> float:
    return style.box_width + style.connector_length


def _eff_box_width(style: StyleOptions, r_idx: int) -> float:
    """line_style=True かつ r_idx>0 のとき line_style_box_width を返す。"""
    if style.line_style and r_idx > 0 and style.line_style_box_width is not None:
        return style.line_style_box_width
    return style.box_width


def _eff_col_width(style: StyleOptions, r_idx: int) -> float:
    return _eff_box_width(style, r_idx) + style.connector_length


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def compute_positions(
    bracket: BracketData,
    style: StyleOptions,
    direction: str,
) -> tuple[dict[int, MatchPos], CanvasInfo]:
    """Return (positions_by_match_id, CanvasInfo)."""
    if direction == "face_to_face":
        return _layout_face_to_face(bracket, style)

    two_col = direction in ("left_to_right_2col", "top_to_bottom_2col")
    pos, canvas = _layout(bracket, style, two_col=two_col)

    # right_to_left: mirror all x coordinates within the LTR canvas width
    if direction == "right_to_left":
        W = canvas.width
        pos = {k: MatchPos(
            x=W - v.conn_x,
            y1=v.y1, y2=v.y2,
            conn_x=W - v.x,
            result_y=v.result_y,
            mirrored=v.mirrored,
        ) for k, v in pos.items()}

    # bottom_to_top: mirror the LTR "x" axis (which TTB renderer maps to SVG-y).
    # Use canvas.width (= LTR x-range) as the flip boundary, not canvas.height.
    if direction == "bottom_to_top":
        W = canvas.width
        pos = {k: MatchPos(
            x=W - v.conn_x,
            y1=v.y1, y2=v.y2,
            conn_x=W - v.x,
            result_y=v.result_y,
            mirrored=v.mirrored,
        ) for k, v in pos.items()}

    if direction in ("top_to_bottom", "top_to_bottom_2col", "bottom_to_top"):
        # Swap canvas dimensions; renderer will swap x↔y when drawing.
        canvas = CanvasInfo(
            width=canvas.height,
            height=canvas.width,
            lb_y_offset=canvas.lb_y_offset,
        )

    return pos, canvas


# ---------------------------------------------------------------------------
# Core layout: single-col and 2-col differ only in the half-gap
# ---------------------------------------------------------------------------

def _layout(
    bracket: BracketData,
    style: StyleOptions,
    two_col: bool,
) -> tuple[dict[int, MatchPos], CanvasInfo]:
    h = style.slot_height
    px, py = style.padding_left, style.padding_top
    half_slots = bracket.total_slots // 2

    # In 2-col mode a visible gap is inserted between the two bracket halves.
    half_gap = style.wb_lb_gap if two_col else 0.0

    positions: dict[int, MatchPos] = {}

    # --- Winners bracket ---
    _place_wb(bracket.winners_rounds, positions,
              x0=px, y0=py, style=style,
              half_slots=half_slots, half_gap=half_gap)

    wb_height = bracket.total_slots * h + half_gap  # gap inserted once

    lb_y0 = 0.0
    lb_height = 0.0

    # --- Losers bracket + Grand Final (double elim only) ---
    if bracket.format == "double" and bracket.losers_rounds:
        lb_y0 = py + wb_height + style.wb_lb_gap
        _place_lb(bracket.losers_rounds, positions,
                  x0=px, y0=lb_y0, style=style)
        lb_slots = bracket.total_slots // 2
        lb_height = lb_slots * h
        lb_col_count = len(bracket.losers_rounds)

        if bracket.grand_final:
            gf_col = max(len(bracket.winners_rounds), lb_col_count)
            gf_x = px + sum(_eff_col_width(style, r) for r in range(gf_col))
            wb_fin = positions[id(bracket.winners_rounds[-1][0])]
            lb_fin = positions[id(bracket.losers_rounds[-1][0])]
            gf_y1 = wb_fin.result_y
            gf_y2 = lb_fin.result_y
            positions[id(bracket.grand_final)] = MatchPos(
                x=gf_x, y1=gf_y1, y2=gf_y2,
                conn_x=gf_x + _eff_box_width(style, gf_col),
                result_y=(gf_y1 + gf_y2) / 2,
            )

    # --- Canvas dimensions ---
    wb_col_count = len(bracket.winners_rounds)
    if bracket.format == "double":
        n_cols = max(wb_col_count,
                     len(bracket.losers_rounds) if bracket.losers_rounds else 0) + 1
    else:
        n_cols = wb_col_count
    total_w = px + sum(_eff_col_width(style, r) for r in range(n_cols)) + style.box_width
    total_h = (py + wb_height
               + (style.wb_lb_gap + lb_height if bracket.format == "double" else 0)
               + py)

    return positions, CanvasInfo(width=total_w, height=total_h, lb_y_offset=lb_y0)


# ---------------------------------------------------------------------------
# Slot-index → y coordinate (respects the 2-col half-gap)
# ---------------------------------------------------------------------------

def _slot_y(
    slot_idx: int,
    y0: float,
    slot_h: float,
    half_slots: int,
    half_gap: float,
) -> float:
    """Centre-y of the given slot index, inserting half_gap after the upper half."""
    base = y0 + slot_idx * slot_h + slot_h / 2
    if slot_idx >= half_slots:
        base += half_gap
    return base


def _match_ys(
    m_idx: int,
    y0: float,
    style: StyleOptions,
    half_slots: int,
    half_gap: float,
) -> tuple[float, float]:
    """Return (y1, y2) for a round-0 match at position m_idx."""
    slot1 = m_idx * 2
    slot2 = m_idx * 2 + 1
    y1 = _slot_y(slot1, y0, style.slot_height, half_slots, half_gap)
    y2 = _slot_y(slot2, y0, style.slot_height, half_slots, half_gap)
    return y1, y2


# ---------------------------------------------------------------------------
# Winners bracket placement
# ---------------------------------------------------------------------------

def _place_wb(
    rounds: list,
    out: dict,
    x0: float,
    y0: float,
    style: StyleOptions,
    half_slots: int,
    half_gap: float,
) -> None:
    cum_x = x0
    for r_idx, round_matches in enumerate(rounds):
        x = cum_x
        bw = _eff_box_width(style, r_idx)
        for m_idx, match in enumerate(round_matches):
            if r_idx == 0:
                y1, y2 = _match_ys(m_idx, y0, style, half_slots, half_gap)
            else:
                prev = rounds[r_idx - 1]
                p1 = out[id(prev[m_idx * 2])]
                p2 = out[id(prev[m_idx * 2 + 1])]
                y1, y2 = p1.result_y, p2.result_y

            out[id(match)] = MatchPos(
                x=x, y1=y1, y2=y2,
                conn_x=x + bw,
                result_y=(y1 + y2) / 2,
            )
        cum_x += _eff_col_width(style, r_idx)


# ---------------------------------------------------------------------------
# Losers bracket placement
# ---------------------------------------------------------------------------

def _place_lb(
    lb_rounds: list,
    out: dict,
    x0: float,
    y0: float,
    style: StyleOptions,
) -> None:
    h = style.slot_height

    if not lb_rounds:
        return

    # Round 0: pair up evenly
    bw0 = _eff_box_width(style, 0)
    for m_idx, match in enumerate(lb_rounds[0]):
        y1 = y0 + m_idx * 2 * h + h / 2
        y2 = y0 + (m_idx * 2 + 1) * h + h / 2
        out[id(match)] = MatchPos(
            x=x0, y1=y1, y2=y2,
            conn_x=x0 + bw0,
            result_y=(y1 + y2) / 2,
        )

    cum_x = x0 + _eff_col_width(style, 0)
    for r_idx in range(1, len(lb_rounds)):
        x = cum_x
        bw = _eff_box_width(style, r_idx)
        prev = lb_rounds[r_idx - 1]
        curr = lb_rounds[r_idx]

        for m_idx, match in enumerate(curr):
            if len(curr) == len(prev):
                # Intake: each curr match corresponds 1:1 with prev match
                p = out[id(prev[m_idx])]
                y1 = p.result_y
                y2 = y1 + h   # WB-loser entry slot
            else:
                # Reduction: pair consecutive prev matches
                p1 = out[id(prev[m_idx * 2])]
                p2 = out[id(prev[m_idx * 2 + 1])]
                y1, y2 = p1.result_y, p2.result_y

            out[id(match)] = MatchPos(
                x=x, y1=y1, y2=y2,
                conn_x=x + bw,
                result_y=(y1 + y2) / 2,
            )
        cum_x += _eff_col_width(style, r_idx)


# ---------------------------------------------------------------------------
# face_to_face layout: left half LTR, right half RTL, final in center
# ---------------------------------------------------------------------------

def _layout_face_to_face(
    bracket: BracketData,
    style: StyleOptions,
) -> tuple[dict[int, MatchPos], CanvasInfo]:
    """左半分LTR・右半分RTL・中央にファイナルを配置する対面レイアウト。"""
    rounds = bracket.winners_rounds
    n = len(rounds)      # 総ラウンド数
    half = n - 1         # 片側のラウンド数（ファイナルを除く）

    h = style.slot_height
    px, py = style.padding_left, style.padding_top
    half_slots = bracket.total_slots // 2

    positions: dict[int, MatchPos] = {}

    # --- 左側x位置を累積計算 ---
    left_xs: list[float] = []
    cum = px
    for r in range(half):
        left_xs.append(cum)
        cum += _eff_col_width(style, r)
    final_x = cum  # 左側全列幅の合計がファイナルのx

    # --- 右側x位置を中央から外側へ計算 ---
    # 右innermost(r_idx=half-1)の結果線がfinal.conn_xに繋がる
    final_bw = style.box_width  # ファイナルは常にフルwidth（橋渡し線の長さを保つ）
    right_xs: list[float] = [0.0] * half  # right_xs[r_idx]
    if half > 0:
        right_xs[half - 1] = final_x + final_bw + style.connector_length
        for k in range(half - 2, -1, -1):
            right_xs[k] = right_xs[k + 1] + _eff_col_width(style, k + 1)

    # --- 左側 (LTR) ---
    for r_idx in range(half):
        x = left_xs[r_idx]
        bw = _eff_box_width(style, r_idx)
        left_matches = rounds[r_idx][: len(rounds[r_idx]) // 2]
        for m_idx, match in enumerate(left_matches):
            if r_idx == 0:
                y1 = py + m_idx * 2 * h + h / 2
                y2 = py + (m_idx * 2 + 1) * h + h / 2
            else:
                prev_left = rounds[r_idx - 1][: len(rounds[r_idx - 1]) // 2]
                p1 = positions[id(prev_left[m_idx * 2])]
                p2 = positions[id(prev_left[m_idx * 2 + 1])]
                y1, y2 = p1.result_y, p2.result_y
            positions[id(match)] = MatchPos(
                x=x, y1=y1, y2=y2,
                conn_x=x + bw,
                result_y=(y1 + y2) / 2,
                mirrored=False,
            )

    # --- 右側 (RTL): r_idx=0が最外列（最大x）、r_idx=half-1が中央寄り ---
    for r_idx in range(half):
        x = right_xs[r_idx]
        bw = _eff_box_width(style, r_idx)
        right_matches = rounds[r_idx][len(rounds[r_idx]) // 2 :]
        for m_idx, match in enumerate(right_matches):
            if r_idx == 0:
                base = m_idx * 2
                y1 = py + base * h + h / 2
                y2 = py + (base + 1) * h + h / 2
            else:
                prev_right = rounds[r_idx - 1][len(rounds[r_idx - 1]) // 2 :]
                p1 = positions[id(prev_right[m_idx * 2])]
                p2 = positions[id(prev_right[m_idx * 2 + 1])]
                y1, y2 = p1.result_y, p2.result_y
            positions[id(match)] = MatchPos(
                x=x, y1=y1, y2=y2,
                conn_x=x + bw,
                result_y=(y1 + y2) / 2,
                mirrored=True,
            )

    # --- 中央ファイナル ---
    final_match = rounds[n - 1][0]
    left_feeder = positions[id(rounds[half - 1][0])]
    center_y = left_feeder.result_y
    y1 = center_y - h / 2
    y2 = center_y + h / 2
    positions[id(final_match)] = MatchPos(
        x=final_x, y1=y1, y2=y2,
        conn_x=final_x + final_bw,
        result_y=center_y,
        mirrored=False,
    )

    outermost_right_x = right_xs[0] if half > 0 else final_x
    total_w = outermost_right_x + style.box_width + px
    total_h = py + half_slots * h + py
    return positions, CanvasInfo(width=total_w, height=total_h)

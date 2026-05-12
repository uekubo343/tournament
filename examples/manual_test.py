"""手動テスト用スクリプト。各種オプションを自由に試してください。"""

from tournament_maker import TournamentBracket

OUT = "manual_out"
import os
os.makedirs(OUT, exist_ok=True)

# ===========================================================================
# ここを編集して試してください
# ===========================================================================

# --- チーム設定 ---
TEAMS = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "1", "2", "3", "4", "5", "6", "7", "8",]
# TEAMS = ["チームA", "チームB", "チームC", "チームD"]   # 日本語チーム名
SEEDS = None
# SEEDS = ["Alpha", "Beta"]   # 不戦勝チーム（チーム数が2の累乗でない場合）

FORMAT = "single"
# FORMAT = "double"   # ダブルエリミネーション

# --- レイアウト ---
DIRECTION = "left_to_right"
# DIRECTION = "left_to_right_2col"
# DIRECTION = "right_to_left"
# DIRECTION = "top_to_bottom"
# DIRECTION = "top_to_bottom_2col"
# DIRECTION = "bottom_to_top"
# DIRECTION = "face_to_face"

# --- スタイル設定 ---
STYLE = dict(
    highlight_winner   = False,   # 勝者ボックスをハイライト
    winner_color       = "#2ecc71",  # 勝者ハイライト色
    winner_text_color  = "#ffffff",

    show_round_labels  = True,    # "Semifinal" などのラベル表示
    round_label_color  = "#888888",
    round_label_size   = 11.0,

    font_family        = "sans-serif",  # 日本語: "Noto Sans JP" など
    font_size          = 13.0,

    bg_color           = "#ffffff",
    line_color         = "#333333",
    line_width         = 1.5,

    name_bg_color      = "#f5f5f5",   # ボックス背景色（全体のデフォルト）
    box_width          = 160.0,
    slot_height        = 40.0,
    connector_length   = 60.0,

    circle_names       = False,   # チーム名を楕円で表示
    circle_color       = "#4a90d9",

    line_style         = True,   # Trueにするとボックスなし・勝者の線に色をつけるスタイル

    # line_style=True のとき、2回戦以降の列で使うボックス幅
    #   None  → デフォルト（box_widthと同じ、変化なし）
    #   0.0   → 最小（arm_lengthのみ）
    #   60.0  → 中間的な長さ
    line_style_box_width = 10,
)

# --- ラウンドラベル（カスタムテキスト） ---
# Noneのままだとデフォルト英語ラベル。リストを渡すと末尾から順に対応する。
ROUND_LABELS_WINNERS = None
# ROUND_LABELS_WINNERS = ["Round 1", "Round 2", "準々決勝", "準決勝", "決勝"]
ROUND_LABELS_LOSERS = None
# ROUND_LABELS_LOSERS = ["LB1回戦", "LB2回戦", "LB3回戦", "LB4回戦", "LB決勝"]

# --- チームごとのボックス色 ---
# TEAM_COLORS = {}
TEAM_COLORS = {
    "Alpha":   "#ff0000",   # 赤
    "Beta":    "#4ecdc4",   # 青緑
    "Gamma":   "#f7dc6f",   # 黄
    "Delta":   "#a29bfe",   # 紫
}

# ===========================================================================
# 以下は変更不要
# ===========================================================================

name = f"{FORMAT}_{DIRECTION}"
path = f"{OUT}/{name}.svg"

bracket = (
    TournamentBracket(teams=TEAMS, seeds=SEEDS, format=FORMAT)
    .set_style(**STYLE)
    .set_round_labels(winners=ROUND_LABELS_WINNERS, losers=ROUND_LABELS_LOSERS)
    .set_team_colors(TEAM_COLORS)
    .set_layout(DIRECTION)
    .render(path)
)

print(f"出力: {path}")
print(f"  チーム数 : {len(TEAMS)}")
print(f"  フォーマット: {FORMAT}")
print(f"  レイアウト: {DIRECTION}")

from dataclasses import dataclass, field


@dataclass
class StyleOptions:
    # チームごとのボックス背景色 {チーム名: 色コード}
    team_colors: dict = field(default_factory=dict)
    # Layout dimensions
    slot_height: float = 40.0
    box_width: float = 160.0
    connector_length: float = 60.0
    padding_top: float = 20.0
    padding_left: float = 20.0
    wb_lb_gap: float = 60.0  # gap between winners and losers bracket

    # Lines
    line_color: str = "#333333"
    line_width: float = 1.5
    bye_line_color: str = "#cccccc"

    # Text
    font_family: str = "sans-serif"
    font_size: float = 13.0
    text_color: str = "#222222"
    text_padding: float = 8.0

    # Team name area background
    name_bg_color: str = "#f5f5f5"
    name_bg_height: float = 28.0  # height of name background rect

    # Bracket arm: horizontal gap between box right-edge and vertical connector
    arm_length: float = 20.0

    # Winner highlight
    highlight_winner: bool = False
    winner_color: str = "#2ecc71"
    winner_text_color: str = "#ffffff"

    # Circle names
    circle_names: bool = False
    circle_color: str = "#4a90d9"
    circle_text_color: str = "#ffffff"
    circle_radius: float = 14.0

    # Round labels
    show_round_labels: bool = True
    round_label_color: str = "#888888"
    round_label_size: float = 11.0
    custom_wb_labels: list = field(default_factory=list)  # 空リストのときはデフォルト英語ラベルを使用
    custom_lb_labels: list = field(default_factory=list)

    # Canvas background
    bg_color: str = "#ffffff"

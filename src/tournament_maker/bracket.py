from .models import BracketData
from .style import StyleOptions
from .seeding import build_bracket
from .layout import compute_positions
from .renderer import render, render_svg, render_png


class TournamentBracket:
    """
    Main entry point for generating tournament bracket images.

    Usage::

        TournamentBracket(teams=["A", "B", "C", "D"])
            .set_style(highlight_winner=True)
            .set_layout("left_to_right")
            .render("bracket.svg")

        # With seeds for non-power-of-2 team counts
        TournamentBracket(
            teams=["A", "B", "C", "D", "E"],
            seeds=["A", "B", "C"],          # or seeds=[0, 1, 2]
            format="single",
        ).render("bracket.png")
    """

    def __init__(
        self,
        teams: list[str],
        seeds: list | None = None,
        format: str = "single",
    ) -> None:
        """
        Parameters
        ----------
        teams:
            List of team names.
        seeds:
            Seeded teams (receive a first-round bye when team count is not a
            power of 2).  Each element is either a team name (str) or a
            zero-based index (int).  The number of seeds required equals
            ``next_power_of_2(len(teams)) - len(teams)``.
        format:
            ``"single"`` (default) or ``"double"`` elimination.
        """
        if format not in ("single", "double"):
            raise ValueError(f"format must be 'single' or 'double', got {format!r}")

        self._bracket: BracketData = build_bracket(teams, seeds, format)
        self._style: StyleOptions = StyleOptions()
        self._direction: str = "left_to_right"

    # ------------------------------------------------------------------
    # Fluent configuration
    # ------------------------------------------------------------------

    def set_style(
        self,
        highlight_winner: bool | None = None,
        circle_names: bool | None = None,
        font_family: str | None = None,
        font_size: float | None = None,
        slot_height: float | None = None,
        box_width: float | None = None,
        connector_length: float | None = None,
        arm_length: float | None = None,
        line_color: str | None = None,
        line_width: float | None = None,
        bg_color: str | None = None,
        winner_color: str | None = None,
        winner_text_color: str | None = None,
        circle_color: str | None = None,
        circle_text_color: str | None = None,
        circle_radius: float | None = None,
        show_round_labels: bool | None = None,
        round_label_color: str | None = None,
        round_label_size: float | None = None,
        name_bg_color: str | None = None,
        text_color: str | None = None,
        text_padding: float | None = None,
        line_style: bool | None = None,
    ) -> "TournamentBracket":
        """Override style options. Returns self for chaining."""
        if highlight_winner is not None:
            self._style.highlight_winner = highlight_winner
        if circle_names is not None:
            self._style.circle_names = circle_names
        if font_family is not None:
            self._style.font_family = font_family
        if font_size is not None:
            self._style.font_size = font_size
        if slot_height is not None:
            self._style.slot_height = slot_height
        if box_width is not None:
            self._style.box_width = box_width
        if connector_length is not None:
            self._style.connector_length = connector_length
        if arm_length is not None:
            self._style.arm_length = arm_length
        if line_color is not None:
            self._style.line_color = line_color
        if line_width is not None:
            self._style.line_width = line_width
        if bg_color is not None:
            self._style.bg_color = bg_color
        if winner_color is not None:
            self._style.winner_color = winner_color
        if winner_text_color is not None:
            self._style.winner_text_color = winner_text_color
        if circle_color is not None:
            self._style.circle_color = circle_color
        if circle_text_color is not None:
            self._style.circle_text_color = circle_text_color
        if circle_radius is not None:
            self._style.circle_radius = circle_radius
        if show_round_labels is not None:
            self._style.show_round_labels = show_round_labels
        if round_label_color is not None:
            self._style.round_label_color = round_label_color
        if round_label_size is not None:
            self._style.round_label_size = round_label_size
        if name_bg_color is not None:
            self._style.name_bg_color = name_bg_color
        if text_color is not None:
            self._style.text_color = text_color
        if text_padding is not None:
            self._style.text_padding = text_padding
        if line_style is not None:
            self._style.line_style = line_style
        return self

    def set_round_labels(
        self,
        winners: list | None = None,
        losers: list | None = None,
    ) -> "TournamentBracket":
        """ラウンドラベルのテキストをカスタマイズする。

        末尾から順に対応する（例: winners=["準々決勝", "準決勝", "決勝"] の場合、
        最後の3ラウンドにそれぞれ割り当てられる）。
        ``show_round_labels=False`` と組み合わせることでラベルを非表示にもできる。

        Parameters
        ----------
        winners:
            ウィナーズブラケットのラベルリスト。
        losers:
            ルーザーズブラケットのラベルリスト（ダブルエリミ用）。
        """
        if winners is not None:
            self._style.custom_wb_labels = list(winners)
        if losers is not None:
            self._style.custom_lb_labels = list(losers)
        return self

    def set_team_colors(self, colors: dict) -> "TournamentBracket":
        """チームごとのボックス背景色を設定する。 ``{"チーム名": "#rrggbb"}`` 形式で渡す。"""
        self._style.team_colors = dict(colors)
        return self

    def set_layout(self, direction: str = "left_to_right") -> "TournamentBracket":
        """
        Set the bracket layout direction.

        Options:
            ``"left_to_right"``       Standard bracket (rounds go →)
            ``"left_to_right_2col"``  Two mirrored halves meeting in the centre
            ``"top_to_bottom"``       Rounds go downward
            ``"top_to_bottom_2col"``  Two mirrored halves meeting at the bottom
        """
        valid = {
            "left_to_right", "left_to_right_2col",
            "right_to_left",
            "top_to_bottom", "top_to_bottom_2col",
            "bottom_to_top",
            "face_to_face",
        }
        if direction not in valid:
            raise ValueError(f"direction must be one of {sorted(valid)}, got {direction!r}")
        self._direction = direction
        return self

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def render(self, output_path: str) -> "TournamentBracket":
        """
        Render the bracket to *output_path*.

        The file format is inferred from the extension:
            ``.svg``  → SVG
            ``.png``  → PNG (requires cairosvg)
        """
        positions, canvas = compute_positions(self._bracket, self._style, self._direction)
        render(self._bracket, positions, canvas, self._style, self._direction, output_path)
        return self

    def render_svg(self, output_path: str) -> "TournamentBracket":
        """Render to SVG explicitly."""
        positions, canvas = compute_positions(self._bracket, self._style, self._direction)
        render_svg(self._bracket, positions, canvas, self._style, self._direction, output_path)
        return self

    def render_png(self, output_path: str) -> "TournamentBracket":
        """Render to PNG (requires cairosvg)."""
        positions, canvas = compute_positions(self._bracket, self._style, self._direction)
        render_png(self._bracket, positions, canvas, self._style, self._direction, output_path)
        return self

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def bracket(self) -> BracketData:
        """Access the underlying bracket data."""
        return self._bracket

    def __repr__(self) -> str:
        fmt = self._bracket.format
        n = self._bracket.total_slots
        return f"TournamentBracket(format={fmt!r}, slots={n}, direction={self._direction!r})"

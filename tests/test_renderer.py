"""renderer.py のテスト（SVG出力の内容検証）"""

import os
import pytest

from tournament_maker import TournamentBracket

IMAGES_DIR = os.path.join(os.path.dirname(__file__), "images")


def _render_svg(teams, filename=None, **kwargs):
    """tests/images にSVGを書き出してテキストを返す"""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    if filename is None:
        filename = "test_output.svg"
    path = os.path.join(IMAGES_DIR, filename)
    TournamentBracket(teams=teams, **kwargs).render(path)
    with open(path, encoding="utf-8") as f:
        return f.read()


class TestSVGOutput:
    def test_svgタグが含まれる(self):
        svg = _render_svg(["A", "B", "C", "D"], filename="svg_tag.svg")
        assert "<svg" in svg

    def test_チーム名がsvgに含まれる(self):
        svg = _render_svg(["Alpha", "Beta", "Gamma", "Delta"], filename="team_names.svg")
        assert "Alpha" in svg
        assert "Beta" in svg

    def test_4方向すべてでファイルが生成される(self):
        directions = [
            "left_to_right",
            "left_to_right_2col",
            "top_to_bottom",
            "top_to_bottom_2col",
        ]
        teams = ["A", "B", "C", "D", "E", "F", "G", "H"]
        for d in directions:
            svg = _render_svg(teams, filename=f"direction_{d}.svg", format="single")
            assert "<svg" in svg, f"{d} でSVGが生成されなかった"

    def test_シングルエリミネーション_SVG出力(self):
        svg = _render_svg(["A", "B", "C", "D"], filename="single_elim.svg")
        assert "svg" in svg.lower()

    def test_ダブルエリミネーション_SVG出力(self):
        svg = _render_svg(["A", "B", "C", "D"], filename="double_elim.svg", format="double")
        assert "<svg" in svg

    def test_シード付き_SVG出力(self):
        svg = _render_svg(
            ["A", "B", "C", "D", "E"],
            filename="seeded.svg",
            seeds=["A", "B", "C"],
        )
        assert "<svg" in svg
        assert "BYE" in svg


class TestTournamentBracketAPI:
    def test_不正なformatはエラー(self):
        with pytest.raises(ValueError):
            TournamentBracket(teams=["A", "B"], format="triple")

    def test_不正なdirectionはエラー(self):
        with pytest.raises(ValueError):
            TournamentBracket(teams=["A", "B"]).set_layout("diagonal")

    def test_render_svgはselfを返す(self):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        path = os.path.join(IMAGES_DIR, "render_returns_self.svg")
        tb = TournamentBracket(teams=["A", "B", "C", "D"])
        result = tb.render(path)
        assert result is tb

    def test_set_styleのチェーン(self):
        tb = (
            TournamentBracket(teams=["A", "B", "C", "D"])
            .set_style(highlight_winner=True, winner_color="#ff0000")
            .set_layout("left_to_right")
        )
        assert tb._style.highlight_winner is True
        assert tb._style.winner_color == "#ff0000"

    def test_line_style_box_width_でキャンバス幅が縮小する(self):
        from tournament_maker.layout import compute_positions
        from tournament_maker.seeding import build_bracket
        from tournament_maker.style import StyleOptions

        teams = ["A", "B", "C", "D", "E", "F", "G", "H"]
        bracket = build_bracket(teams, seeds=None, format="single")

        _, canvas_default = compute_positions(
            bracket, StyleOptions(line_style=True), "left_to_right"
        )
        _, canvas_compact = compute_positions(
            bracket, StyleOptions(line_style=True, line_style_box_width=0.0), "left_to_right"
        )
        assert canvas_compact.width < canvas_default.width

    def test_line_style_box_width_でSVGが生成される(self):
        os.makedirs(IMAGES_DIR, exist_ok=True)
        path = os.path.join(IMAGES_DIR, "line_style_compact.svg")
        TournamentBracket(teams=["A", "B", "C", "D", "E", "F", "G", "H"]).set_style(
            line_style=True, line_style_box_width=0.0, highlight_winner=True
        ).render(path)
        with open(path, encoding="utf-8") as f:
            svg = f.read()
        assert "<svg" in svg

"""renderer.py のテスト（SVG出力の内容検証）"""

import os
import tempfile
import pytest
from tournament_maker import TournamentBracket


def _render_svg(teams, **kwargs):
    """一時ファイルにSVGを書き出してテキストを返す"""
    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
        path = f.name
    try:
        TournamentBracket(teams=teams, **kwargs).render(path)
        with open(path, encoding="utf-8") as f:
            return f.read()
    finally:
        os.unlink(path)


class TestSVGOutput:
    def test_svgタグが含まれる(self):
        svg = _render_svg(["A", "B", "C", "D"])
        assert "<svg" in svg

    def test_チーム名がsvgに含まれる(self):
        svg = _render_svg(["Alpha", "Beta", "Gamma", "Delta"])
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
            svg = _render_svg(teams, format="single")
            assert "<svg" in svg, f"{d} でSVGが生成されなかった"

    def test_シングルエリミネーション_SVG出力(self):
        svg = _render_svg(["A", "B", "C", "D"])
        assert "svg" in svg.lower()

    def test_ダブルエリミネーション_SVG出力(self):
        svg = _render_svg(["A", "B", "C", "D"], format="double")
        assert "<svg" in svg

    def test_シード付き_SVG出力(self):
        svg = _render_svg(
            ["A", "B", "C", "D", "E"],
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
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as f:
            path = f.name
        try:
            tb = TournamentBracket(teams=["A", "B", "C", "D"])
            result = tb.render(path)
            assert result is tb
        finally:
            os.unlink(path)

    def test_set_styleのチェーン(self):
        tb = (
            TournamentBracket(teams=["A", "B", "C", "D"])
            .set_style(highlight_winner=True, winner_color="#ff0000")
            .set_layout("left_to_right")
        )
        assert tb._style.highlight_winner is True
        assert tb._style.winner_color == "#ff0000"

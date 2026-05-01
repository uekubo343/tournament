"""layout.py のテスト"""

import pytest
from tournament_maker.seeding import build_bracket
from tournament_maker.layout import compute_positions
from tournament_maker.style import StyleOptions


def _bracket(n=4, format="single"):
    return build_bracket([str(i) for i in range(n)], seeds=None, format=format)


class TestComputePositions:
    def test_全マッチに座標が割り当てられる(self):
        b = _bracket(4)
        style = StyleOptions()
        pos, canvas = compute_positions(b, style, "left_to_right")
        all_matches = [m for r in b.winners_rounds for m in r]
        for m in all_matches:
            assert id(m) in pos

    def test_キャンバスサイズが正(self):
        b = _bracket(8)
        style = StyleOptions()
        pos, canvas = compute_positions(b, style, "left_to_right")
        assert canvas.width > 0
        assert canvas.height > 0

    def test_top_to_bottomはwidthとheightが入れ替わる(self):
        b = _bracket(4)
        style = StyleOptions()
        pos_ltr, canvas_ltr = compute_positions(b, style, "left_to_right")
        pos_ttb, canvas_ttb = compute_positions(b, style, "top_to_bottom")
        assert abs(canvas_ltr.width - canvas_ttb.height) < 1
        assert abs(canvas_ltr.height - canvas_ttb.width) < 1

    @pytest.mark.parametrize("direction", [
        "left_to_right",
        "left_to_right_2col",
        "top_to_bottom",
        "top_to_bottom_2col",
    ])
    def test_全レイアウト方向でエラーなし(self, direction):
        b = _bracket(8)
        style = StyleOptions()
        pos, canvas = compute_positions(b, style, direction)
        assert len(pos) > 0

    def test_ダブルエリミネーションでgrand_finalに座標がある(self):
        b = _bracket(4, format="double")
        style = StyleOptions()
        pos, canvas = compute_positions(b, style, "left_to_right")
        assert id(b.grand_final) in pos

    def test_result_yはy1とy2の中点(self):
        b = _bracket(4)
        style = StyleOptions()
        pos, canvas = compute_positions(b, style, "left_to_right")
        for p in pos.values():
            assert abs(p.result_y - (p.y1 + p.y2) / 2) < 0.01

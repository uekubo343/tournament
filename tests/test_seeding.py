"""seeding.py のテスト"""

import pytest
from tournament_maker.seeding import build_bracket
from tournament_maker.models import BYE


# ---------------------------------------------------------------------------
# build_bracket - シングルエリミネーション
# ---------------------------------------------------------------------------

class TestSingleElimination:
    def test_2チーム(self):
        b = build_bracket(["A", "B"], seeds=None, format="single")
        assert b.format == "single"
        assert b.total_slots == 2
        assert len(b.winners_rounds) == 1
        assert len(b.winners_rounds[0]) == 1
        m = b.winners_rounds[0][0]
        assert {m.team1, m.team2} == {"A", "B"}

    def test_4チーム(self):
        b = build_bracket(["A", "B", "C", "D"], seeds=None, format="single")
        assert b.total_slots == 4
        assert len(b.winners_rounds) == 2
        assert len(b.winners_rounds[0]) == 2  # 1回戦2試合
        assert len(b.winners_rounds[1]) == 1  # 決勝1試合

    def test_8チーム(self):
        b = build_bracket(list("ABCDEFGH"), seeds=None, format="single")
        assert b.total_slots == 8
        assert len(b.winners_rounds) == 3

    def test_2チーム未満はエラー(self):
        with pytest.raises(ValueError):
            build_bracket(["A"], seeds=None, format="single")

    def test_不正なformatはエラー(self):
        with pytest.raises(ValueError):
            build_bracket(["A", "B"], seeds=None, format="triple")


class TestSeeding:
    def test_5チーム_シード名前指定(self):
        teams = ["A", "B", "C", "D", "E"]
        b = build_bracket(teams, seeds=["A", "B", "C"], format="single")
        assert b.total_slots == 8
        # 1回戦にBYEが3つ含まれる
        round0 = b.winners_rounds[0]
        bye_count = sum(1 for m in round0 if m.is_bye)
        assert bye_count == 3

    def test_5チーム_シードインデックス指定(self):
        teams = ["A", "B", "C", "D", "E"]
        b = build_bracket(teams, seeds=[0, 1, 2], format="single")
        assert b.total_slots == 8

    def test_シード数不足はエラー(self):
        teams = ["A", "B", "C", "D", "E"]  # 3シード必要
        with pytest.raises(ValueError):
            build_bracket(teams, seeds=["A"], format="single")

    def test_シードなしで非2冪はエラー(self):
        with pytest.raises(ValueError):
            build_bracket(["A", "B", "C"], seeds=None, format="single")

    def test_シード範囲外インデックスはエラー(self):
        with pytest.raises(IndexError):
            build_bracket(["A", "B", "C", "D", "E"], seeds=[99, 0, 1], format="single")

    def test_存在しないシード名はエラー(self):
        with pytest.raises(ValueError):
            build_bracket(["A", "B", "C", "D", "E"], seeds=["Z", "A", "B"], format="single")

    def test_BYEの試合は自動的にwinnerが設定される(self):
        teams = ["A", "B", "C"]
        b = build_bracket(teams, seeds=["A"], format="single")
        round0 = b.winners_rounds[0]
        bye_matches = [m for m in round0 if m.is_bye]
        for m in bye_matches:
            assert m.winner is not None
            assert m.winner != BYE


# ---------------------------------------------------------------------------
# build_bracket - ダブルエリミネーション
# ---------------------------------------------------------------------------

class TestDoubleElimination:
    def test_4チームダブル(self):
        b = build_bracket(["A", "B", "C", "D"], seeds=None, format="double")
        assert b.format == "double"
        assert b.grand_final is not None
        assert b.grand_final.bracket == "grand_final"
        assert len(b.losers_rounds) > 0

    def test_8チームダブル(self):
        b = build_bracket(list("ABCDEFGH"), seeds=None, format="double")
        assert b.grand_final is not None
        # ウィナーズブラケットは3ラウンド
        assert len(b.winners_rounds) == 3

    def test_ダブルのlosersbracketはwinnersより多いラウンド(self):
        b = build_bracket(list("ABCDEFGH"), seeds=None, format="double")
        assert len(b.losers_rounds) > len(b.winners_rounds)

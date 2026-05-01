# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリで作業する際のガイダンスを提供します。

## 言語

ユーザーへの出力（説明、ログ、コメントなど）はすべて**日本語**で行うこと。

## コマンド

```bash
# 仮想環境を作成してパッケージをインストール
uv venv
uv pip install -e ".[dev]"

# 仮想環境を有効化
source .venv/bin/activate

# 全テスト実行
pytest

# 単一テストファイルの実行
pytest tests/test_seeding.py

# サンプルスクリプトの実行
python examples/basic_example.py
```

## アーキテクチャ

`TournamentBracket`（bracket.py）がフルエントAPIのエントリポイント。`.render()` を呼ぶと以下の3段パイプラインが実行される。

1. **`seeding.build_bracket()`** — チーム名とシード情報から `BracketData` を構築する。チーム数が2の累乗でない場合、不戦勝数（`next_power_of_2(n) - n`）と同数のシードが必要。シードチームは `BYE` センチネルとペアになり、通常対戦と均等にインターリーブされる。ダブルエリミネーションでは `_build_losers_bracket()` がWB敗者受け入れラウンドとLB内部削減ラウンドを交互に構築し、最後にグランドファイナルの `Match` を追加する。

2. **`layout.compute_positions()`** — 全 `Match` オブジェクトにピクセル座標を割り当て、`id(match)` をキーとする辞書で返す。座標は「論理LTR空間」（`MatchPos.x`, `y1`, `y2`, `conn_x`, `result_y`）で計算される。top-to-bottom レイアウトではここでキャンバスの幅と高さを入れ替え、レンダラーが `pos.y1/y2` をSVGのx座標、`pos.x/conn_x` をSVGのy座標として読む。2列レイアウトは上下ハーフの間に `half_gap` を挿入する。

3. **`renderer._build_svg()`** — ラウンドを順番にイテレートし、各マッチに対して `_match_h`（水平）または `_match_v`（垂直）を呼び出す。名前ボックスとブラケット線を `svgwrite` のプリミティブで描画する。BYEマッチは破線とグレーで表示。PNG出力はSVGを一時ファイルに書き出してから `cairosvg.svg2png` を呼び出す。

### 重要な不変条件

`positions` 辞書のキーはラウンド・マッチのインデックスではなく `id(match)`（Pythonオブジェクトの同一性）。bracket・layout・renderer の各段で同じ `Match` オブジェクトを使い回す必要があるため、途中で再生成してはいけない。

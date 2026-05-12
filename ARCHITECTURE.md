# tournament_maker アーキテクチャ解説

## 全体パイプライン

`.render()` を呼ぶと3段パイプラインが実行される。

```mermaid
flowchart LR
    User["TournamentBracket\n(bracket.py)"]
    S["① seeding\nbuild_bracket()"]
    L["② layout\ncompute_positions()"]
    R["③ renderer\n_build_svg()"]
    Out["SVG / PNG"]

    User -->|teams, seeds, format| S
    S -->|BracketData| L
    L -->|positions dict\nCanvasInfo| R
    R --> Out
```

各段の責務を一言で：

| 段 | ファイル | 入力 | 出力 | 責務 |
|----|----------|------|------|------|
| ① | `seeding.py` | チームリスト・シード・形式 | `BracketData` | **誰が誰と戦うか**を決める |
| ② | `layout.py` | `BracketData` + `StyleOptions` | `dict[int, MatchPos]` + `CanvasInfo` | **どこに描くか**を決める（ピクセル座標） |
| ③ | `renderer.py` | 上記すべて | SVG要素 | **実際に描く** |

---

## ① seeding.py — マッチツリーの構築

### データモデル

```mermaid
classDiagram
    class BracketData {
        winners_rounds: list[list[Match]]
        losers_rounds: list[list[Match]]
        grand_final: Match | None
        total_slots: int
        format: "single" | "double"
    }
    class Match {
        round_index: int
        match_index: int
        team1: str | None
        team2: str | None
        winner: str | None
        bracket: "winners"|"losers"|"grand_final"
    }
    BracketData "1" --> "many" Match
```

### スロット配置（チーム数が2の累乗でない場合）

8チームのトーナメントに5チームが参加する例：

```
チーム数 5 → 次の2の累乗 = 8 → 不戦勝（BYE）が必要な数 = 3
シード3名が必要
```

```mermaid
flowchart TD
    A[5チーム + seeds=3名] --> B["_next_power_of_2(5) = 8<br/>byes_needed = 3"]
    B --> C["_arrange_slots()<br/>シード vs BYE のペアと<br/>通常対戦ペアをインターリーブ"]
    C --> D["8スロット確定<br/>例: [A,BYE, C,D, B,BYE, E,BYE]"]
    D --> E["_slots_to_rounds()<br/>ラウンドツリーを再帰的に生成"]
```

**インターリーブ（Bresenham式）** — BYEペアと通常ペアを均等に分散する：

```
bye_pairs  = [(A,BYE), (B,BYE), (C,BYE)]   ← シード3名
real_pairs = [(D,E)]                         ← 残り2名のペア

インターリーブ後: [(A,BYE), (D,E), (B,BYE), (C,BYE)]
```

### ラウンドツリーの構造

シングルエリミネーション8チームの例：

```mermaid
graph LR
    subgraph R0["Round 0（1回戦）"]
        M00["M0: A vs B"]
        M01["M1: C vs D"]
        M02["M2: E vs F"]
        M03["M3: G vs H"]
    end
    subgraph R1["Round 1（準決勝）"]
        M10["M0: winner(M00) vs winner(M01)"]
        M11["M1: winner(M02) vs winner(M03)"]
    end
    subgraph R2["Round 2（決勝）"]
        M20["M0: winner(M10) vs winner(M11)"]
    end
    M00 --> M10
    M01 --> M10
    M02 --> M11
    M03 --> M11
    M10 --> M20
    M11 --> M20
```

### ダブルエリミネーションの構造

WBの各ラウンドで敗者をLBに送り込む。LBは「intake（WB敗者受け入れ）」と「intra-LB（内部削減）」が交互に並ぶ。

```mermaid
graph TD
    subgraph WB["Winners Bracket"]
        WR0["WB R0 (4試合)"]
        WR1["WB R1 (2試合)"]
        WR2["WB Final (1試合)"]
        WR0 --> WR1 --> WR2
    end
    subgraph LB["Losers Bracket"]
        LR0["LB R0: WB R0の敗者同士"]
        LR1["LB R1 (intake): LB生存者 vs WB R1敗者"]
        LR2["LB R2 (intra): LB内部で削減"]
        LR3["LB Final: WB Final敗者を受け入れ"]
        LR0 --> LR1 --> LR2 --> LR3
    end
    GF["Grand Final"]
    WR0 -.敗者.-> LR0
    WR1 -.敗者.-> LR1
    WR2 -.敗者.-> LR3
    WR2 --> GF
    LR3 --> GF
```

---

## ② layout.py — ピクセル座標の計算

### MatchPos — 1試合の座標

すべての座標は「**論理LTR空間**」で計算される。top_to_bottomのようなレイアウトでは、レンダラー側がx↔yを入れ替えて読む（layout.pyは常にLTR前提で計算する）。

```
       pos.x   pos.conn_x
         │          │
 ────────┼──────────┼──── pos.y1 （team1の中心y）
         │[name box]│
         │          │─── pos.result_y = (y1+y2)/2
         │[name box]│
 ────────┼──────────┼──── pos.y2 （team2の中心y）
         │          │
         ←─box_width─→
```

```python
@dataclass
class MatchPos:
    x: float        # name boxの左端x
    y1: float       # team1の中心y
    y2: float       # team2の中心y
    conn_x: float   # x + box_width（アームの起点）
    result_y: float # (y1+y2)/2（次ラウンドへの入力y）
    mirrored: bool  # True = RTL描画（face_to_face右側）
```

### col_width — 列幅の定義

```
←──────── col_width ──────────→
←── box_width ──→←connector_len→
┌─────────────────┐             :
│   name box      ├──arm──┤     :  ← 垂直コネクタ
└─────────────────┘        :   :
                            └─result line→
```

`col_width = box_width + connector_length`

`arm_length` は `connector_length` の内側に含まれる（box右端からarmの先端まで）。

### 座標の決まり方（シングルエリミネーション LTR）

```mermaid
flowchart TD
    A["スロット数 M から<br/>half_slots = M/2 を計算"] --> B

    B["ラウンド0のy座標を計算\n<br/>match[i].y1 = py + i*2*h + h/2\nmatch[i].y2 = py + (i*2+1)*h + h/2"]
    B --> C

    C["ラウンド1以降:\n前ラウンドの result_y を引き継ぐ\n<br/>y1 = prev[i*2].result_y\ny2 = prev[i*2+1].result_y"]
    C --> D

    D["x座標:\nx = px + round_index * col_width"]
    D --> E["キャンバスサイズを計算"]
```

具体例（8チーム、デフォルトスタイル）：

```
box_width=160, connector_length=60, arm_length=20
col_width = 220, padding_left=20, slot_height=40

Round 0, Match 0 (A vs B):
  x=20, conn_x=180
  y1 = 20 + 0*40 + 20 = 40
  y2 = 20 + 1*40 + 20 = 80
  result_y = 60

Round 0, Match 1 (C vs D):
  x=20
  y1=120, y2=160, result_y=140

Round 1, Match 0 (SF):
  x = 20 + 1*220 = 240
  y1 = 60  ← R0.M0.result_y
  y2 = 140 ← R0.M1.result_y
  result_y = 100

Round 2, Final:
  x = 20 + 2*220 = 480
  y1 = 100 ← R1.M0.result_y
  ...
```

### positions辞書のキーは id(match)

```python
positions: dict[int, MatchPos]
# キーは id(match)（Pythonオブジェクトのメモリアドレス）
# インデックスではない！
```

**なぜ id(match) を使うか：** seeding → layout → renderer の3段で同じ `Match` オブジェクトを使い回すため。ラウンドインデックスだとダブルエリミネーションのWB/LBで重複する。

---

## レイアウト方向ごとの変換

### direction 一覧

```mermaid
graph TD
    D["compute_positions(direction)"]
    D --> F2F["face_to_face\n→ _layout_face_to_face()"]
    D --> NORM["その他\n→ _layout() 共通処理"]
    NORM --> RTL["right_to_left\nx座標を左右反転"]
    NORM --> BTT["bottom_to_top\nx座標を反転（LTR空間）"]
    NORM --> TTB["top_to_bottom(_2col)\nキャンバスW↔Hを入れ替え"]
    NORM --> LTR["left_to_right(_2col)\nそのまま"]
```

### top_to_bottom の座標変換

TTBではlayout.pyは「LTR空間」で計算したまま、キャンバスのW↔Hを入れ替えてレンダラーに渡す。レンダラーが `pos.x` をSVGのy軸、`pos.y1/y2` をSVGのx軸として読む。

```
LTR空間（layout.py出力）   TTBレンダラーの読み替え
  pos.x     → SVG y（ラウンドの深さ方向）
  pos.conn_x → SVG y（ボックス下端）
  pos.y1    → SVG x（チーム1の列）
  pos.y2    → SVG x（チーム2の列）
```

### face_to_face の特殊処理

```mermaid
flowchart LR
    subgraph Left["左半分（LTR）"]
        LQ["QF matches\nrounds[r][:n//2]"]
        LSF["SF match"]
        LQ --> LSF
    end
    subgraph Center["中央（Final）"]
        FIN["Final\nx = px + half*cw\ny1 = center_y - h/2\ny2 = center_y + h/2"]
    end
    subgraph Right["右半分（RTL）\nmirrored=True"]
        RSF["SF match"]
        RQ["QF matches\nrounds[r][n//2:]"]
        RSF --> RQ
    end
    LSF -->|"result_y → final.y 中心"| FIN
    RSF -->|"同じ y 位置"| FIN
```

右半分が左半分と**同じ y スロット**を使うことで、両SFの `result_y` が揃い、水平線1本で繋がる。

---

## ③ renderer.py — SVG要素の生成

### 1試合の描画（LTR水平）

```
pos.x    conn_x  arm_x           result_end_x
  │         │      │                    │
  ┌─────────┐      │                    │
  │ team1   ├──────┤                    │
  └─────────┘      │ ← 垂直コネクタバー  │
                   ├────────────────────→ result line
  ┌─────────┐      │
  │ team2   ├──────┘
  └─────────┘

arm_x        = conn_x + arm_length
result_end_x = conn_x + connector_length  (= 次ラウンドの x)
```

### _match_h の描画ロジック

```mermaid
flowchart TD
    A["_match_h()"] --> NB["name box を2つ描画\n_name_box_h() × 2"]
    NB --> FC{face_final?}
    FC -->|Yes| FF["水平橋渡し線\n(pos.x → pos.conn_x, y=result_y)"]
    FC -->|No| NC{no_connector?}
    NC -->|Yes| END["何も描かない"]
    NC -->|No| ARMS["アーム線 × 2\n垂直コネクタ × 1"]
    ARMS --> FINAL{is_final?}
    FINAL -->|No| RL["result line を描く"]
    FINAL -->|Yes| END
```

### name box の3モード

```mermaid
flowchart TD
    NB["_name_box_h()"] --> CM{circle_names?}
    CM -->|Yes| CIRC["楕円（ellipse）を描画\nチーム名を中央に"]
    CM -->|No| UL{use_line?\n（line_style かつ round>0）}
    UL -->|Yes| SKIP["何も描かない（ボックスなし）"]
    UL -->|No| RECT["矩形（rect）＋テキスト\n通常スクエア"]
```

### is_rtl（RTL）の処理

`mirrored=True`（face_to_face右半分）か `direction=right_to_left` のとき `eff_rtl=True` になる。

```python
# LTR
arm_x        = pos.conn_x + arm_length      # 右に出る
result_end_x = pos.conn_x + connector_length

# RTL（is_rtl=True）
arm_x        = pos.x - arm_length           # 左に出る
result_end_x = pos.x - connector_length
```

---

## スタイルオプション一覧

```mermaid
graph LR
    SO["StyleOptions"]
    SO --> DIM["寸法\nslot_height, box_width\nconnector_length, arm_length\npadding_top, padding_left"]
    SO --> LINE["線スタイル\nline_color, line_width\nbye_line_color"]
    SO --> TEXT["テキスト\nfont_family, font_size\ntext_color, text_padding"]
    SO --> BOX["ボックス\nname_bg_color, name_bg_height"]
    SO --> WIN["勝者ハイライト\nhighlight_winner\nwinner_color, winner_text_color"]
    SO --> CIRC["丸名前モード\ncircle_names, circle_color\ncircle_text_color, circle_radius"]
    SO --> LBL["ラウンドラベル\nshow_round_labels\nround_label_color, round_label_size\ncustom_wb_labels, custom_lb_labels"]
    SO --> MISC["その他\nbg_color\nteam_colors（チームごと色）\nline_style"]
```

---

## 拡張ガイド

### 新しいレイアウト方向を追加する

1. `bracket.py` の `valid` セットに名前を追加
2. `layout.py` の `compute_positions()` に分岐を追加
3. 既存の `_layout()` を流用するか、`_layout_face_to_face()` のように専用関数を書く

```python
# layout.py
def compute_positions(bracket, style, direction):
    if direction == "my_new_layout":
        return _layout_my_new(bracket, style)   # ← 追加
    if direction == "face_to_face":
        ...
```

必要な出力は `dict[int, MatchPos]` と `CanvasInfo` の2つだけ。

### 新しいボックス描画スタイルを追加する

`renderer.py` の `_name_box_h()` または `_name_box_v()` を拡張する。

```python
def _name_box_h(dwg, x, y, bw, name, style, highlight, is_bye, is_rtl, use_line):
    if style.circle_names:
        ...           # 既存: 楕円
    elif use_line:
        pass          # 既存: 何も描かない
    elif style.MY_NEW_STYLE:   # ← 追加
        ...           # 新スタイル
    else:
        ...           # 既存: 矩形
```

`StyleOptions` に対応するフィールドを追加するだけで有効になる。

### 新しい試合接続スタイルを追加する

`_match_h()` の分岐に追加する。

```python
if face_final:
    ...
elif my_new_connector:    # ← 追加
    ...
elif not no_connector:
    ...  # 通常アーム
```

### ダブルエリミネーションのLBラウンド数

8チームの場合、LBは6ラウンドになる：

```
LB R0 (intake R0のペア) → LB R1 (WB R1敗者) → LB R2 (intra)
→ LB R3 (WB Final敗者) → LB Final
```

`_build_losers_bracket()` は `wb_rounds` の長さから自動的にラウンド数を計算する。新しいフォーマット（例: triple elimination）を追加するなら `seeding.py` に同様の関数を追加し、`BracketData` のフィールドを拡張する。

---

## 不変条件

1. **`id(match)` はパイプライン全体で一意のキー** — seeding で生成した `Match` オブジェクトをそのまま layout → renderer に渡す。途中で `Match` を再生成すると `id()` が変わってクラッシュする。

2. **`round_index` はラウンド内でのみ有効** — WBとLBで重複するため、ラウンドをまたぐ参照には `id(match)` を使う。

3. **LTR空間で計算** — `layout.py` は常にLTR座標を出力する。TTB/BTTへの変換はキャンバスW↔Hの入れ替えとレンダラー側の軸読み替えで実現する。layout.py自体は方向を意識しない。

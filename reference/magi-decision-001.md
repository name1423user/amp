# MAGI Decision Record — amp v0.1 の次の一手

## Problem Definition
- 対象: amp v0.1(構造化JSON→英文の監査ログ生成ツール)完成後、次にどう進めるか
- 選択肢: A すぐPyPI公開 / B MAGIに組み込みdogfoodingしてから公開 / C 公開せず自分用に留める / D(現状維持) 未判断のまま保留
- 不可逆性: 低〜中(公開は名前を消費するが実害は小さい) / 影響範囲: 主に開発者本人
- 成功条件: 実運用で有用性が確認される / 失敗条件: 破壊的変更を要する欠陥の露呈、または放置
- Quality: valid

## Fact Reconciliation
| 事実 | A(実用性) | B(品質) | C(検証) | 状態 |
|---|---|---|---|---|
| golden test 28/28 通過 | 一致(verified) | 一致(verified) | 一致(verified) | 合意成立 |
| PyPI に "amp" が既存(無関係な数式パーサ、Python2.7)。同名では新規公開不可 | 一致(verified, 直接HTTP確認) | 一致(verified, 直接HTTP確認) | 言及なし | 合意成立(呼び出し側でも再検証済み) |
| MAGIへの組み込みコードは未着手(リポジトリに存在しない) | 言及なし | 示唆のみ | 一致(verified, find実行) | 合意成立 |
| 判断書「判断7」は既に「まずMAGIで使う。外部利用者を探さない」と規定済み | 言及なし | 一致(verified) | 一致(verified) | 合意成立 |
| カタログ側JSONに `version` フィールドの検証コードがない(バージョンゲート非対称) | 言及なし | 指摘(verified, grep) | 言及なし | B単独指摘。技術的負債候補として記録 |

未解決の食い違いなし。

## Round 2/3 + Stop判定
3体は独立起動(他エージェントの出力を見せていない)にもかかわらず、根拠は異なりながら同じ方向(**B→検証→その後Aへ**)に収束した。新たな反論・新情報は出ていないため:

**STOP**(新情報なく結論が安定)

## Veto Check
veto: true を出したエージェントなし。該当なし。

## Convergence Analysis
- agreement: 3/3(方向性一致。ただし到達根拠は独立)
- evidence_diversity: **high** — A/Bは独立にPyPI名衝突を実地確認(HTTPで直接検証)、Cは独立にファイルシステム検索でMAGI未着手を確認。同じ未検証の仮定を繰り返しているのではなく、それぞれ異なる一次情報から同じ結論に到達している
- shared_assumptions: 「急ぐ外部要因がない」「yankにより公開の実害は限定的」は問題定義からの前提(user_provided、未検証)。「MAGI組み込みコストは小さい」は3体共通の予測(agent_claimed)
- veto: なし

## Robustness Assessment
判定材料: agreement=3/3, evidence_diversity=high, veto=なし, shared_assumptionsは限定的で決定を単独で覆すほど致命的ではない

**robustness: high**
理由: 「外部公開前に自分のユースケースで検証する」という結論は、(1)開発者自身が判断書 判断7で事前に規定していた計画と一致する、(2)「今すぐ公開」の前提(=名前がそのまま使え低コスト)自体が事実によって崩れている、(3)3本の独立した価値軸(実用性・品質・検証)がそれぞれ異なる一次情報から同じ方向に達している。これを覆すには「外部からの具体的な需要」「明確な期限」のような、現時点で存在しないと確認されている条件が新たに発生する必要がある。

---

## Final Decision

### Decision
**decision: conditional** — B(MAGIに組み込みdogfoodingしてから公開)を採用し、実運用で最低1件以上 Decision Record を英文化できることを確認したうえで、速やかに A(PyPI公開)へ進む。ただしA実行時は **PyPI名 "amp" が既存パッケージと衝突するため改名が必須**(例: `amp-protocol`)。D(保留)は明確に不採用、Cは次善(公開自体を見送るなら)。

### Robustness
high(上記参照)

### Evidence Quality
evidence_diversity: high
未検証(agent_claimed)の前提に依存している箇所: MAGI組み込みの実装コストが小さいという予測、実運用実績が「数回」で十分という基準

### Agreement(参考情報)
3/3(方向性)

### 決定を支配した論点
1. PyPI名 "amp" が既に別パッケージに使われている(即時公開の前提が崩れる)
2. 判断書 判断7がすでに「まずMAGIで検証」と自ら規定していたのに、実装が完了した今もまだ着手されていない
3. 独立実装が存在しない段階でのプロトコルの実用性は、外部公開ではなく実運用でしか検証できない(判断書の根本前提と同一)

### 結論を覆す条件(decision-changing assumptions)
- 具体的な外部利用者・期限が発生した場合(現状は存在しないと確認済み)
- MAGI組み込みで判断1〜8のいずれかと矛盾する構造上の欠陥が見つかった場合 → 判断7の但し書きどおり「プロトコル設計が間違っている証拠」として扱い、公開ではなく設計修正が先になる

### 各エージェントの最終見解
- 実用性(Utility): conditional(veto無)— B→速やかにA。Dは失敗条件に直結するため最悪
- 品質・保守性(Quality): conditional(veto無)— 検証前公開は技術的負債(カタログversion未検証等)を抱えたまま外部依存を生む
- 検証(Validation): conditional(veto無)— 判断書自身の一貫性(検証してから進む原則)からBが必然

### 少数意見
- 主張: Utility軸はB後のA移行を「速やかに」行うべきと強めに主張し、Quality/Validation軸より公開への時間的猶予に厳しい
- 見落とされている可能性: 「検証」に要する期間の見積もりが3体とも未検証(agent_claimed)であり、Bが長期化した場合にUtility軸の「機会損失」評価が変わりうる
- 現実化する条件: MAGI組み込みが数週間以上停滞した場合、Utility軸は条件を再評価すべき

### 事実認識の食い違い(未解決分)
なし

### Next Action
1. amp を実際に MAGI のDecision Record出力に対して稼働させる(本セッションで実施 → 下記参照)
2. カタログ側JSONの `version` フィールド検証を追加する(品質軸の指摘、公開前の技術的負債)
3. 実運用で判明した過不足を `reference/open-issues-remaining.md` に反映する
4. 上記が済んだ段階でPyPI公開に進む。公開時はパッケージ名を改名する("amp" は使用不可)

---

## Decision Record

```
MAGI Decision Record
ID: magi-decision-001
Date: 2026-09-13
Problem: amp v0.1 完成後、公開/dogfooding/留保のどれを選ぶか
Options: A) 即PyPI公開 / B) MAGI組み込みdogfoodingしてから公開 / C) 自分用に留める / D) 保留
Agents: A=実用性(Utility) / B=品質・保守性(Quality) / C=検証(Validation)
Key Facts: golden test 28/28通過(verified) / PyPI "amp" 既存で名前衝突(verified) / MAGI組み込み未着手(verified) / 判断書 判断7が既にB相当を規定(verified)
Key Assumptions: MAGI組み込みコストは小さい(agent_claimed) / 急ぐ外部要因なし(user_provided)
Decision: conditional — Bを先に実施し、検証後にA(改名要)へ
Robustness: high
Evidence Diversity: high
Agreement: 3/3(方向性)
Decision-changing Assumptions: 外部利用者・期限の発生 / MAGI組み込みで判断1〜8と矛盾する構造欠陥の発覚
Minority Opinion: Utility軸はA移行までの猶予により厳しい
Next Action: MAGIへの実組み込み(本記録の下部で実施) → カタログversion検証追加 → open-issues更新 → 改名のうえPyPI公開

Expected Outcomes: 4週間以内にMAGIのDecision Recordを1件以上amp経由で英文化し、少なくとも1つの設計判断(refs列挙10件閾値・attitude非実装の要否)について「そもそも要らない」または「やはり必要」の判定が付く

Review Date: 2026-10-11(4週間後)
Actual Outcomes: (Review Date到来後に追記)
Review結果: (Review Date到来後に追記)
```

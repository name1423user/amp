# MAGI Decision Record — v0.3後、今すぐ公開してよいか

## 対象
magi-decision-001(dogfoodingしてから公開)を受けてv0.2→v0.3(全7act・R-4・attitude・aspect・props/measurements・4件のバグ修正・改名・LICENSE/CI/README)を実施した。今すぐPyPI公開してよいか。

## Round 1 独立評価(3体並列起動)
- 実用性(Utility): **recommend** — 完璧な検証待ちはC(見送り)と同じ機会損失。公開してから直せばよい
- 品質(Quality): **conditional**(veto無) — 未実装コーナーは全て例外で拒否する設計であり致命的欠陥の根拠はないが、前回決定が自ら設定した4週間のReview Dateをまだ使い切っていない
- 検証(Validation): **conditional**(veto無) — **実データでのdogfoodingは今も`act: inform`の2件のみ**。request/query/commit/reject/failure/close の6act、aspect、props/measurementsは**実運用0回**(golden testという合成データのみ)。同一開発者が同一日の84分間で行った自己言及的な1件のdogfoodingは、「独立性・多様性・時間経過を欠いた最弱形の検証」

## Fact Reconciliation(合意成立分)
- golden test 96/96通過(3体ともverified)
- PyPI "amp-protocol" 現時点で未登録=空き(B, Cが独立に直接確認)
- 全作業が2026-09-13の84分間に集中(B, Cが独立にgit log/mtimeで確認)
- **6/7 actおよびv0.3の新機能(aspect/props/measurements)が実データで一度も使われていない**(Cがgrepで定量確認。A, Bも「dogfoodingは1件のみ」と言及しており事実自体には争いがない)

## Convergence / Robustness
agreement: 方向性は割れた(A=今すぐ推奨、B/C=条件付き)。ただし**根拠になった事実は3体で一致**しており、割れているのは「この事実をどう評価するか」という価値判断の部分のみ。evidence_diversity: high(B, Cが独立にPyPI/GitHub/grep/git logを直接確認)。

robustness: medium — 「未実装コーナーは例外で拒否する設計だから致命的欠陥は考えにくい」という部分は頑健(3体とも支持)。しかし「6actが実運用ゼロ」という具体的な穴が埋まっていない限り、A(即公開)への確信度は上げきれない。

## Decision
**conditional**: 4週間フルに待つ必要はないが(B/Cの懸念のうち「期間」そのものは本質ではない)、**未使用の6act・aspect・props/measurementsを実際に一度動かしてから**Aに進む。判断書の一貫した原則(検証してから広げる)をそのまま適用する。

## Next Action
本Decision Record自身を材料に、request/query/commit/aspect/props/measurementsを実際に使って英文化する(下記で実施)。そこで何か壊れれば設計判断、何も壊れなければ公開して良い、という一段階の検証を追加する。

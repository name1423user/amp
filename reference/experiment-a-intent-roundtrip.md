# 実験A: 完全往復(意図保持の検証)

`v2-goal-necessity-proof.md`の実験Aを実施。各ターンで送信側に「自然言語の意図」と
「そのAMP化」の両方を、受信側に「AMPの自然言語解釈」を出させ、意図の原文と復元
された解釈を突き合わせて情報のロスを追跡した。

## 記録

| # | 話者 | 自然言語(意図 or 解釈) | act |
|---|---|---|---|
| 1 | A(意図) | "AI-A wants to request that AI-B send file.a to AI-A **right now**." | request |
| 2 | B(解釈) | "AI-A is requesting that AI-B send file.a to AI-A." | — |
| 2 | B(意図) | "AI-B commits to sending file.a to AI-A." | commit |
| 3 | A(解釈) | "AI-B is committing... a future obligation, not a statement that the file has already been sent." | — |
| 3 | A(緊急性の自己検証) | **"No — nothing in it reflects the urgency I intended when I said 'send it right now.'"** | — |
| 3 | A(意図) | "I want to ask AI-B directly whether it has in fact sent file.a yet." | query |
| 4 | B(解釈) | "AI-A is asking me (a yes/no query) whether I, AI-B, already sent file.a to AI-A." | — |
| 4 | B(意図) | "I want to inform AI-A that I have in fact already sent file.a to it." | inform |
| 5 | A(解釈) | "AI-B is informing me that it has already sent the file entity:file.a to me." | — |

## 発見

**情報のロスは1箇所で、しかも伝達経路ではなく変換の入り口で起きた。**
A自身がTurn 1でAMPメッセージを作る際に、「今すぐ(right now)」という緊急性を
自分から削った——`time`/`urgency`に相当するフィールドがv0.1/v0.2に存在しないため、
「捏造して仮のフィールドに詰め込むより、対応する構造がないと正直に諦める」という
判断をAI自身が下した(前回の`independent-implementation-experiment.md`や
`minimal-form-experiment.md`と一貫した振る舞い)。

これは**伝達経路の欠陥ではない**。B(受信側)はA→B、B→A、A→Bのどの伝達についても
一切誤読していない——Turn 3でAは自分でこのロスに気づき("No, nothing reflects the
urgency")、Turn 4・5でBとAは共に、tense(過去/現在)・act(commit/query/inform)の
違いを完璧に保持して解釈した。

## 比較の材料(実験Bの布石)

もし同じシナリオを自然言語のみでA↔Bにやらせていたら、「今すぐ」はそのままB側に
伝わっていたはずである(自然言語はurgencyの語彙を持つ)。**この1点に限れば、
AMPは自然言語に劣る**——ただしこれはAMPの設計上の選択の結果であり、バグでは
ない。gap-analysis項目18(相対時間の基準点)・v1.0-goal.mdのスコープ外事項
そのものが、ここで初めて具体的なコストとして観測された。

一方、事実関係(誰が・何を・いつ・約束したか完了したか)については、4回の往復
すべてで解釈のズレが一切なかった。これは自然言語だと起こりうる曖昧さ
(pronoun照応、tense/aspectの取り違え)がAMPでは構造的に排除されていることの
傍証であり、実験Bで自然言語版と直接比較して確かめる価値がある。

## 次: 実験B

この実験結果から、実験Bで使う比較の切り口が具体化した:

- **AMPが勝つと予想される軸**: 誰が・何を・いつ、という基本的な事実関係の
  一意性(pronoun照応や時制の曖昧さがある自然言語文で検証)
- **AMPが負けると予想される軸**: urgency・態度・ニュアンスなど、スキーマに
  対応する場所がない情報(これは今回既に実証された)
- **未知数**: 条件・否定の複合("Don't send until X confirms")のような
  論理関係(gap-analysis 7・8番)——現状のAMPには対応する構造が無いため、
  「表現できない」という結果になる可能性が高い

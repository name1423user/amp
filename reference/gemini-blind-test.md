# 未学習AIでの読解テスト(Gemini)

「AMPを知らないAIにいきなり渡しても意味が伝わるのでは」という気づきを検証した記録。
Claude系ではなく別ベンダー(Gemini, Web UI, ログインなし, モデル: Flash-Lite)に、
**AMPという名前も仕様書も一切見せず**、生のJSONメッセージだけを渡して英語で説明させた。
公正を期すため、各テストは新規チャット(文脈の持ち越しなし)で実施した。

## テスト1: `request`(attitudeなし)

入力:
```json
{"protocol": "amp/0.1", "id": "msg-001", "conversation": "conv-v1-roundtrip-1", "sender": "entity:agent.a", "receiver": ["entity:agent.b"], "timestamp": "2026-09-13T10:00:00Z", "act": "request", "content": {"predicate": {"lemma": "send", "tense": "present", "polarity": "affirmative"}, "roles": {"agent": {"refs": ["entity:agent.b"]}, "patient": {"refs": ["entity:file.a"]}, "recipient": {"refs": ["entity:agent.a"]}}}}
```

Geminiの回答:
> Agent A requests Agent B to send file A to Agent A within conversation conv-v1-roundtrip-1.

正解(`amp render`): "AI-A requests AI-B to send file.a to AI-A."

**ほぼ完全一致。** 注目点: `request`の主語はJSON上`envelope.sender`から取り、
要求される行為者は`content.roles.agent`という**入れ子構造**(spec §9.3)になっているが、
Geminiはこれを仕様なしで正しく解いている。差分は会話IDまで文に含めた点のみ
(誤りではなく、amp renderより情報量が多いだけ)。

## テスト2: `inform` + `attitude`(閾値変換を要する部分)

入力:
```json
{"protocol": "amp/0.1", "id": "magi2-validation-r1", "conversation": "magi-v2-decision", "sender": "entity:agent.validation", "receiver": ["entity:agent.utility", "entity:agent.quality"], "timestamp": "2026-09-13T11:00:00Z", "act": "inform", "content": {"predicate": {"lemma": "recommend", "tense": "present"}, "roles": {"agent": {"refs": ["entity:agent.validation"]}, "patient": {"refs": ["entity:option.b"]}}}, "attitude": {"confidence": 0.85, "evidence": "inferred"}}
```

Geminiの回答:
> With an 85% confidence level based on inferred evidence, the validation agent informed
> the utility and quality agents on September 13, 2026, that it recommends option B.

正解(`amp render`): "Apparently, Validation almost certainly recommends Option B
(seek a second independent implementation)."

**意味は伝わったが、AMP独自の変換規則は再現されなかった**:
- `confidence: 0.85` → 正解は仕様(spec §9.2の閾値表)に従い`"almost certainly"`という
  副詞に変換する。Geminiは数値をそのまま`"85% confidence level"`として出力した
- `evidence: "inferred"` → 正解は`"Apparently,"`という文頭副詞。Geminiは
  `"based on inferred evidence"`とそのまま説明した

## 結論

2つのテストを重ねると、きれいな切り分けが見える。

**伝わったもの**: act(誰が誰に何をどうしてほしいか)、role構造(envelopeとcontentに
分散した主語の対応関係)、属性値の**意味内容**(85%の確信度、推論的根拠であること)。
これらは全て自然言語の意味役割・様相論理の一般的な語彙に対応しており、Geminiは
訓練データにある英語の意味論だけで正しく解けた。

**伝わらなかったもの**: AMPが独自に定めた**閾値→特定表現への変換テーブル**
(0.85以上は"almost certainly"、"inferred"は"Apparently,")。これは仕様書(spec §9.2)を
読まなければ再現不可能な、AMP固有の恣意的な文体規約であり、意味の本質ではない。

これは`foundational-doubts.md`の90・91番(自己記述性の限界)の評価を精密化する:
「フィールド名・act語彙のような**構造の骨格**は自然言語の一般語彙をそのまま使っている
ため、未学習のAIにも伝わる。一方、**表層の言い回し変換**(数値→副詞のような)は
AMP固有の取り決めなので伝わらない」。悪いニュースではない——伝わらなかったのは
「人間の読みやすさのための追加の化粧」であって、Geminiの出力(数値+根拠の種類を
明示)はむしろAMPが意図している「曖昧性のなさ」をそのまま保っている。**閾値変換への
依存を減らすほど、AMPは仕様を教えなくても通じるプロトコルに近づく**、という
設計上の示唆が得られた。

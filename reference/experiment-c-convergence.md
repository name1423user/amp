# 実験C: 同一意味・別表現の収束性

「AMPが表現ではなく意味を抽出できているか」を検証する実験
(`v2-goal-necessity-proof.md`の後継、ユーザー提案の再優先順位に基づく)。

## 方法

意味的には同一だが言い回し(丁寧さ・構文)が異なる4つの自然言語指示を用意し、
**それぞれ独立したサブエージェント**(互いの出力を見せない)にAMP化させた。

- A: "Send file.a to AI-A."(命令形)
- B: "Please send AI-A the file.a."(丁寧な命令形)
- C: "I need you to send file.a over to AI-A."(必要性の表明)
- D: "Could you send AI-A file.a?"(疑問形の依頼)

## 結果

4つとも、`id`/`timestamp`(こちらが個別に指定した値)を除いて**完全に同一の
JSON構造**になった:

```json
"act": "request",
"content": {
  "predicate": { "lemma": "send", "tense": "present", "polarity": "affirmative" },
  "roles": {
    "agent":     { "refs": ["entity:agent.b"] },
    "patient":   { "refs": ["entity:file.a"] },
    "recipient": { "refs": ["entity:agent.a"] }
  }
}
```

`amp render`にかけると4つとも同一の英文になった:

```
AI-A requests AI-B to send file.a to AI-A.
AI-A requests AI-B to send file.a to AI-A.
AI-A requests AI-B to send file.a to AI-A.
AI-A requests AI-B to send file.a to AI-A.
```

## 測定結果

| 指標 | 結果 |
|---|---|
| ① 構造一致率(act/predicate/roles) | 4/4 = 100% |
| ② AMP→自然言語の一致 | 4/4 = 100%(上記render結果) |
| ③ 丁寧さ・言い回しの混入 | 0/4 = 混入なし |

`attitude`(confidence/necessity等)にも一切差が出なかった——"Could you...?"の
遠慮がちな疑問形も、"I need you to..."の強い必要性の表明も、`request`という
同じactと同じroles構造に収束し、どちらのニュアンスも(良くも悪くも)残らなかった。

## 意義

これは実験A・Bとは逆方向の証拠になる。実験A・Bは「AMPで表現できない情報が
落ちる」ことを示したが、実験Cは**「AMPで表現される範囲については、表現の
揺れに影響されず同じ構造に収束する」**ことを示した。

これでAMPの性質がかなり明確になった:

> **AMPは、自然言語のうち`act`/`predicate`/`roles`が表す次元(誰が誰に何を
> するか)については、表現の違いを正規化して同じ構造に落とす。それ以外の次元
> (urgency・条件節・トーン)は、そもそも受け皿が無いため保持しない。**

これはgap-analysisの2・3番(正規形の定義、同一意味の複数表現)に対する
初めての実証的な裏付けになる——ADR-021・ADR-012のような「一本化」の設計判断が、
JSON構造のレベルだけでなく、**自然言語からJSONへの変換段階でも実際に機能して
いる**ことが分かった。

## 次にやるなら

- 逆方向(同じAMP構造から異なる自然言語を生成させ、それをまた別のAIにAMP化
  させて元に戻るか)のラウンドトリップ
- 丁寧さがより極端なケース(例: 命令口調 vs 非常に婉曲的な依頼)で同じ収束が
  起きるかの追試
- act自体が変わりうる境界ケース(例: "You must send it now" のような、
  requestとinformの中間的な表現)で収束が崩れるかを見る

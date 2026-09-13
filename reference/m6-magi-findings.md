# M6: MAGI での実利用 — 実施記録と過不足

`00-判断書.md` 判断7 / `02-作業手順.md` M6 に基づき、実際の MAGI 合議1件
([`magi-decision-001.md`](magi-decision-001.md) — amp v0.1 を今すぐ公開するか
dogfooding してから公開するか、をMAGI自身で判断させたもの)を
amp のメッセージに変換して英文化した。

## 変換結果(v0.1 の時点)

カタログ: [`examples/magi-catalog.json`](../examples/magi-catalog.json)
メッセージ: [`examples/magi-messages.jsonl`](../examples/magi-messages.jsonl)

```
$ amp render --catalog examples/magi-catalog.json examples/magi-messages.jsonl
MAGI evaluated 4 options.
MAGI recommends the dogfood-first plan to Claude.
```

## 足りなかった機能 → 対応(v0.2)

1. **content の再帰(R-4 が具体化した)** — MAGI の実際の推奨内容は
   「dogfood-first plan」のような単一の名詞ではなく、「B(dogfoodingしてから
   公開する)を選ぶべきだ」という命題そのものである。v0.1 には embedded
   clause がないため、推奨内容を**カタログに固有名詞としてでっち上げて**
   から `recommend` の patient に押し込んだ。

   → **対応済み**。`patient` role が `{"clause": {...}}` を取れるように
   した(深さ上限1。節の中に節は不可・`InvalidValue`)。上のメッセージを
   実際に書き直すと、でっち上げの固有名詞なしで表現できる:

   ```
   $ amp render --catalog examples/magi-catalog.json examples/magi-messages.jsonl
   MAGI evaluated 4 options.
   MAGI recommends that Claude adopt amp.
   ```

   **追記(思想の再確認で修正)**: 最初の実装は `Claude adopts amp`
   (indicative)を出していたが、これは「Claudeがampを採用している」という
   **事実の記述**に読めてしまい、「まだ起きていない、提案されている行為」
   というJSON側の意味との区別が英文にした瞬間に消える。これは本プロジェクト
   の核 ── JSONを一意の真実にして英文をその決定的な射影にすることで曖昧さを
   消す ── に反する省略だったので、mandative subjunctive(recommend/suggest/
   insist/demand/require/propose/request/ask の埋め込み節は原形)を実装して
   `adopt` に修正した。`clause-indicative-non-mandative` golden test で
   非mandative動詞(state等)はindicativeのままであることも固定してある。

   `agent`/`recipient` は refs 限定のまま(clauseにする用途が今のところ
   ない)。深いネスト(節の中の節)は未対応。ゴールデンテストは
   `clause-patient-recommend` / `clause-indicative-non-mandative` /
   `clause-mandative-negative` / `err-clause-too-deep` /
   `err-role-neither-refs-nor-clause` / `err-role-both-refs-and-clause`
   ([`tests/golden.jsonl`](../tests/golden.jsonl))。

2. **attitude 層(判断3で凍結)の必要性が具体的な形で確認できた** —
   MAGI の出力は `decision: conditional` `decision_confidence: medium`
   のように態度情報が本質的な内容を占める。今回は「MAGI recommends X」と
   confidence を無視して事実化したが、「MAGIはmedium程度の確信度でXを
   推奨した」を監査ログとして残せないのは実利用上の実害として感じられた。

   → **対応済み**。`reference/spec-revised.md` §3.7/§4.4 の設計(語順固定・
   inform は confidence 0.5以上必須)をそのまま実装した(`amp/render.py`)。
   `decision_confidence: medium` は 0.5〜0.65 の範囲としてマッピングすれば
   `possibly` で表現できる:

   ```
   "attitude": {"confidence": 0.6}
   → "MAGI possibly recommends that Claude adopts amp."
   ```

   ゴールデンテストは `attitude-confidence-only` /
   `attitude-full-spec-example`(spec §4.4 の例文そのもの) /
   `attitude-necessity-negative` / `err-attitude-*` 3件。
   判断3の「覆すべき条件:なし」どおり、外部条件を待たずに実装した。

## 過剰だった/使わなかった機能

- 過去形の生成規則を1回(`evaluate` past)使ったのみで、否定文・3人称単数
  以外の活用は今回のMAGI実運用では一度も必要にならなかった
- `refs` の proper 混在・10件超などの複雑な列挙分岐(判断6)は不要だった。
  ただし1回の実運用だけでは「そもそも要らない」と断定する材料にならない
  (判断書の言う「何件か消えるはず」を裏付けるにはさらに実運用が必要)

## 副次的な発見(バグではなく仕様どおりの挙動)

ID命名でハイフンを使おうとして `InvalidValue` で弾かれた
(`^(entity|type):[a-z][a-z0-9_]*(\.[a-z0-9_]+)*$` はアンダースコアのみ
許可、ハイフン不可)。仕様(§2 ID の形式)どおりの正しい拒否であり、
バリデーションが機能していることの確認になった。命名時にハイフンに
手が伸びやすいという運用上の小さな摩擦として記録するのみ。

## MAGI dogfooding の判断そのものについて

上記の変換対象となった判断(公開すべきか)自体の Decision Record は
[`magi-decision-001.md`](magi-decision-001.md) を参照。結論:
**dogfooding(本ドキュメント)を先に行い、検証してからPyPI公開に進む
(公開時は名前衝突のため改名が必要)**。

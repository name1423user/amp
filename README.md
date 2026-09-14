# amp

AI間メッセージプロトコル — 構造化JSON(意図・役割・指示対象)を英文1行に変換する。監査ログ用途。

## 動く例

```bash
pip install amp-protocol
amp render --catalog examples/catalog.json examples/messages.jsonl
```

```
AI-B sends a.json to AI-A.
AI-B sends a.json.
AI-A and AI-B send a.json.
AI-B sent a.json to AI-A.
```

標準入力も使える(`-`)。エラーのある行は stderr に出て終了コード1。`--skip-errors` を付けるとその行をスキップして続行する。

```bash
cat examples/messages.jsonl | amp render --catalog examples/catalog.json -
amp render --catalog examples/catalog.json --skip-errors messages.jsonl
```

## 対応している act

ADR-011 の7語彙を全て実装している。

| act | 例文 |
|---|---|
| `inform` | `AI-B sends 3 files to AI-A.` |
| `request` | `AI-A requests AI-B to send 3 files to AI-A.` |
| `query` | `Does AI-B send 3 files to AI-A?` (`gap`で疑問詞疑問文も: `Who sends 3 files to AI-A?`) |
| `commit` | `AI-B will send 3 files to AI-A.` |
| `reject` | `AI-B refuses to send 3 files to AI-A.` |
| `failure` | `AI-B failed to send 3 files to AI-A.` |
| `close` | `AI-A ends the conversation.` |

`attitude`(確信度・情報源・必然性)も付けられる:

```json
"attitude": { "confidence": 0.9, "evidence": "inferred", "necessity": "should" }
```
→ `"Apparently, AI-B almost certainly should send 3 files to AI-A."`

`patient` は埋め込み節にもできる(深さ1まで):

```json
"patient": { "clause": { "predicate": {...}, "roles": {...} } }
```
→ `"MAGI recommends that Claude adopt amp."`

`inform`/`commit`は進行形・完了形も使える:

```json
"predicate": { "lemma": "send", "tense": "present", "aspect": "perfect" }
```
→ `"AI-B has sent a.json."`

role に `props`(スケールなし属性)・`measurements`(スケールあり属性、型ごとの閾値で形容詞化)も付けられる(単一ref限定):

```json
"patient": { "refs": ["entity:file.a"], "props": ["prop:encrypted"],
             "measurements": { "prop:size": { "value": 4.2, "unit": "unit:gigabyte" } } }
```
→ `"...an encrypted 4.2 GB file..."`

## 仕様

- 実装対象の確定仕様: [`spec/01-v0.1仕様.md`](spec/01-v0.1仕様.md)
- 判断とその理由(handshakeを実装しない理由など): [`amp-handoff/amp-handoff/00-判断書.md`](../amp-handoff/amp-handoff/00-判断書.md)
- act拡張の経緯: [`reference/act-expansion.md`](reference/act-expansion.md)
- MAGIでの実利用と、そこで見つかった過不足: [`reference/m6-magi-findings.md`](reference/m6-magi-findings.md)
- 正解の定義は仕様書ではなく [`tests/golden.jsonl`](tests/golden.jsonl)。仕様と食い違ったらテストが正

## 実験

AMPのどの構造化要素が自然言語に対して実際に価値を持つのかを、自己申告ではなく
客観的な採点で切り分けるための実験基盤が [`experiment/`](experiment/) にある。
4つの対称実験(entity reference / condition / urgency / time role)の固定された
計画は [`reference/experiment-plan-symmetric.md`](reference/experiment-plan-symmetric.md)、
harnessの使い方は [`experiment/README.md`](experiment/README.md) を参照。この
段階では仕様(`spec/`)・実装(`amp/`)は変更していない。

## 意図的に実装していないもの

独立に書かれた第二の実装が現れる(または具体的な接続予定が立つ)まで、handshake・語彙衝突解決・3者以上の会話は実装しない。理由は判断書を参照。単一実装の段階ではテストしようがないコードを増やすだけになるため。

## 独立実装、歓迎します

このプロトコルが実用になる条件は「独立に書かれた2つの実装が相互運用できる」ことです([判断書](../amp-handoff/amp-handoff/00-判断書.md)参照)。現在の実装はPython製のこの1本のみで、`amp render`が実際に検証してきたのはAI自身が生成したメッセージ([`reference/v1.0-roundtrip-verification.md`](reference/v1.0-roundtrip-verification.md))と、仕様書を渡していない別ベンダーのAI(Gemini)がどこまで意味を読み取れるか([`reference/gemini-blind-test.md`](reference/gemini-blind-test.md))までです。「別の実装がこの仕様を読んで、独立に同じ結論を出すか」はまだ一度も検証されていません。

別言語・別実装者によるrenderer実装を歓迎します。最小要件:

- [`spec/01-v0.1仕様.md`](spec/01-v0.1仕様.md) に準拠すること(この文書だけで実装できるように書かれています)
- [`tests/golden.jsonl`](tests/golden.jsonl) の入力→期待英文のペアを再現できること(仕様書と食い違ったらgolden.jsonlが正)
- 可能であれば、[`examples/v1-roundtrip-messages.jsonl`](examples/v1-roundtrip-messages.jsonl) のような実際のAI間メッセージ交換で動作確認されていること

実装ができたら、[GitHub Issue/PR](https://github.com/name1423user/amp) で教えてください。相互運用性の検証(同じメッセージを両実装に通して同じ英文が出るか)を一緒にやりたいです。

## 開発

```bash
pip install -e ".[dev]"
pytest
python tests/inflection_probe.py  # M0: 屈折ライブラリの疎通確認
```

CI は push/PR ごとに GitHub Actions で `pytest` を実行する([`.github/workflows/test.yml`](.github/workflows/test.yml))。

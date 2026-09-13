# amp

AI間メッセージプロトコル v0.1 — 構造化JSON(意図・役割・指示対象)を英文1行に変換する。監査ログ用途。

## 動く例

```bash
pip install -e .
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

## 仕様

- 実装対象の確定仕様: [`spec/01-v0.1仕様.md`](spec/01-v0.1仕様.md)
- v0.1 でやらないこと(handshakeなど)とその理由: 引き継ぎ資料の `00-判断書.md` 参照
- 正解の定義は仕様書ではなく [`tests/golden.jsonl`](tests/golden.jsonl)。仕様と食い違ったらテストが正

## 開発

```bash
pip install -e ".[dev]"
pytest
python tests/inflection_probe.py  # M0: 屈折ライブラリの疎通確認
```

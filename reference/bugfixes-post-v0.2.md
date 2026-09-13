# v0.2完成後に見つけたバグの修正記録

7 act実装後の棚卸しで、「意図的に手を付けていない」バケツ(handshake等)とは別に、
単純なバグを4件発見・修正した。§6の「エラーは必ずmessage_id/field_path付きの
例外として出す」「それらしい英文を黙って出さない」という契約を破っていた。

## 1. envelope必須フィールドが未検証だった

`id`/`conversation`/`timestamp`/`receiver`が欠けていても素通りしていた
(`protocol`と`act`しかチェックしていなかった)。仕様§3の必須フィールドを
`render_message`の冒頭で検証するようにした。`receiver`が配列でない場合も
`InvalidValue`。

## 2. メッセージ本体がobjectでないと生の`AttributeError`でクラッシュしていた

`{"just a string"}`のような不正なJSONを流すと、`message.get()`で
`AttributeError`がそのまま外に漏れていた(§6が保証する「必ずAmpError」を
破る)。`content`/`predicate`/`roles`/`attitude`/各roleの値についても
同様の穴があった(非object値を渡すと`in`演算子や`.get()`でクラッシュ、
または文字列への部分一致で誤判定する)。`_as_object`ヘルパーで一括して
型を検証し、非objectなら`InvalidValue`にするよう統一した。

## 3. catalogが`type`/`parent`参照の実在性を検証していなかった

`type: "type:does_not_exist"`という個体を定義しても、catalog読み込み時
にはエラーにならず、その個体がproperな固有名詞として使われる限り
(generic_labelを引く経路を通らない限り)誰にも気づかれずに動き続けて
いた。読み込み時に`type`/`parent`の参照先が実在し`kind`が正しいことを
検証するようにした。

## 4. (3の派生、最も深刻) `proper: true`なのに`label`が無いと`None`が英文に出ていた

```
$ amp render --catalog <label無しのproper個体を含むcatalog> ...
None ends the conversation.
```

これはクラッシュですらなく、**それらしく見えて間違った英文**を黙って
出していた。§6が名指しで禁止しているパターンそのもの
(「エラーを握りつぶして『それらしい英文』を出さないこと。黙って間違った
英文を出す方が、エラーで止まるより有害」)。catalog読み込み時に
`proper: true`の個体には`label`を必須とするようにした。

## 修正箇所

- [`amp/catalog.py`](../amp/catalog.py) — kind/type/parent/labelの構造検証を追加
- [`amp/render.py`](../amp/render.py) — `_as_object`で非object値を一律検証、
  envelope必須フィールド検証、message自体の型検証
- テスト: `tests/golden.jsonl`(err-message-not-object 等8件追加)、
  `tests/test_catalog_structure.py`(新規)

78件全通過。既存の65件に回帰なし。

# act 拡張の記録(判断2の履行)

`00-判断書.md` 判断2:「v0.1 は `inform` のみ。この判断を覆すべき条件: M4(ゴールデンテスト全通し)が終わったとき。そこから act を1つずつ足す。」

M4 は完了済み(golden.jsonl 全通過)。以下の順で1つずつ足した(1つ足すごとに golden test を先に書いて確認):

1. `request` — 「AI-A requests AI-B to send 3 files to AI-A.」(`reference/spec-revised.md` §4.1)。envelopeの`sender`を要請者として使い、`content.roles`はinformと同じ意味のまま流用。新フィールドなし
2. `query` — 疑問文。`gap`フィールド(§4.2)のみ新規。`time`/`location`のgapは対応する role が未実装のため明示的にエラー
3. `commit` — 「will」。attitudeのnecessity機構をそのまま流用(法助動詞という点で同じ形)
4. `reject` / `failure` — 「refuses to / failed to」。requestと違い、要請者は要らず agent が主語兼行為者
5. `close` — 「ends the conversation」。roleを取らない唯一のact。主語はenvelopeの`sender`

これで ADR-011 の7語彙(`inform`/`request`/`query`/`commit`/`reject`/`failure`/`close`)を全て実装した。詳細仕様は `spec/01-v0.1仕様.md` §9.3〜§9.4、テストは `tests/golden.jsonl` の各act向けケース。

## 意図的に対応していないもの

- 各actの`patient`が埋め込み節(`clause`, §9.1)になるケース ── `inform`の`recommend`以外では実例が出ていない
- `query`のattitude ── confidence副詞を疑問文の語順にどう乗せるか根拠がない
- `commit`とnecessityの併用 ── `will`と法助動詞は英語として両立しない(2つ目のモーダルを英語は許さない)
- `reject`/`failure`が要請した第三者を明示するケース(「AI-CがAI-Bに頼んだ送信をAI-Bが拒否した」等) ── 今のところ実例なし

# dogfooding round 2 — 未使用だった6act・v0.3機能を実データで動かす

magi-decision-002 の検証(実データでの使用実績が`inform`2件のみという指摘)を受けて、
実際に**このセッションで起きた本物の事実**を、これまで実データで一度も使われて
いなかった act・機能を使って英文化した。捏造したデータは無い(GitHub APIから
直接取得したスター数以外は、このセッション内で実際に交わされたやり取りそのもの)。

```
$ amp render --catalog examples/magi-catalog.json examples/magi-decision-002-messages.jsonl
MAGI has evaluated 3 options.
MAGI requests Claude to test amp.
Claude will test amp.
Does amp exist?
MAGI reports an unstarred repository.
```

| act/機能 | 対応する実データ | 結果 |
|---|---|---|
| `inform` + `aspect: perfect` | MAGIが3択を評価し終えたこと | 一発で通った |
| `request` | MAGIがClaudeに追加検証を求めたこと(magi-decision-002のNext Action) | 一発で通った |
| `commit` | Claudeが追加検証を約束すること | 一発で通った |
| `query` | "amp-protocol"というPyPI名が実際に空いているか(時点情報で不確実) | 通ったが下記の**簡略化**あり |
| `props`/`measurements`(threshold) | GitHubリポジトリの実際のスター数(0) | 一発で通った。`gh api`で直接取得した本物の数値 |

## 見つかった限界(正直に書く)

1. **`query`は簡略化を強いられた**。本当に聞きたいのは「amp-protocolはPyPI上で
   利用可能で**ある**か」(連結動詞 be + 形容詞 available)だが、v0.3の文法は
   `predicate.lemma`が及物・自動詞のどちらであれ**動詞**であることを前提にして
   おり、「主語 is 形容詞」という構文(be動詞+補語)を表現する経路がない。
   `props`/`measurements`は名詞句の中の修飾語としてしか使えず、述語の位置には
   置けない。やむを得ず「amp exists」(存在するか)という別の、やや近いだけの
   命題に置き換えた。**これは実際に困った箇所であり、想像で仕様を広げるべき
   か迷うところだが、今回は実例1つだけなので見送る**(困った、という記録だけ残す)。

2. **`reject`/`failure`は今回も実データ0件のまま**。このセッション中に「拒否した」
   「失敗した」という実際の出来事が一件も起きなかったため、無理に捏造せず
   見送った。実運用ゼロという事実は変わっていない — 次に実際の拒否・失敗が
   起きたときに初めて埋まる。

3. **props/measurementsの実データは1件だけ**(スター数)。`props`(スケールなし
   属性)の実データはまだゼロ。

## 結論

request/commit/query/aspect(perfect)/measurements(threshold)は**コード変更なしで**
実データに耐えた。見つかった限界(1)は新しい機能追加の話ではなく、v0.3の設計上
意図的にスコープ外にしてきた「述語位置の形容詞」という別カテゴリの話で、今の
grammatical scope(動詞+名詞句)を素直に守った結果の限界。無理に広げず記録のみ。

これでmagi-decision-002の懸念(6act・v0.3機能が実運用0件)はほぼ解消した
(reject/failureのみ引き続き0件、実際の出来事待ち)。公開判断に戻ってよい。

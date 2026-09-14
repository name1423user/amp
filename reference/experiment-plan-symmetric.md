# 実験計画の固定: 4つの対称実験(entity reference / condition / urgency / time role)

「可変strictness(NL → MAMP → Full AMP)」という仮説が出た後の指示として、**今回は
仕様変更を一切行わず、実験基盤の整備と実験計画の固定だけを行う**。この文書はその
固定された計画そのものであり、以後の実験実施はこの文書のシナリオ・gold answer・
評価指標を変更せずに行う。変更が必要になった場合は、この文書を改訂した上で
`git log` に残る形で明示的に行うこと(実験結果を見てから黙って基準をずらさない)。

harnessの実装(コード)は [`experiment/`](../experiment/) 、使い方は
[`experiment/README.md`](../experiment/README.md) を参照。この文書は「何を測るか」、
`experiment/`は「どう測るか」の分担。

---

## §0. 今回変更しないもの(絶対条件の確認)

以下は本変更のどのコミットにも含まれていない。CIの`pytest`はこれらのファイルを
一切変更しないことまでは検証できないが、少なくとも`amp/`パッケージのコードと
`spec/`は本変更で一切触れていない。

- `spec/01-v0.1仕様.md` の仕様
- `amp/`配下の実装(`catalog.py`/`render.py`/`errors.py`等)
- `type: nl / mamp / amp` のようなenum、またはそれに類する新しいメッセージ種別
- MAMPの正式定義(entity-only MAMPを含む)
- SVO(主語-動詞-目的語)の新しい構造化レイヤー
- `condition` / `urgency` / `time` roleの新規スキーマ化
- `tests/golden.jsonl`

`experiment/`配下は`amp`パッケージから独立したツリーであり(`experiment/schema.py`
の冒頭に明記)、`amp`を一切importしない。実験用シナリオに登場するAMP風JSON
(例: `experiment/scenarios/entity_reference/*.json`内の例)は**人間・AIの読解力を
測るための例示テキストであり、`amp.render`に通して検証されたものではない**。
`entity:report-final.pdf`のようなIDは`spec`のID正規表現(ハイフン不可)を厳密には
満たさないが、これは`reference/experiment-h-full-vs-minimal-vs-nl.md`など既存の
実験記録がそのまま使ってきた表記を踏襲したものであり、実験の意図(受信側の読解を
測る)には影響しない。

**実験結果を見てから仕様やgold answerを変更する仕組みは、意図的に実装していない。**
`experiment/runner.py`はscenarioファイルを読むだけで書き込まない。
`experiment/analysis/aggregate.py`もscenarioディレクトリには書き込まない
(`experiment/README.md`「Pipeline」参照、`tests/test_experiment_harness.py`の
`test_write_trial_never_touches_scenarios_dir`がこれを回帰テストする)。

---

## §1. gold answerの確定ポリシー

各シナリオファイルは`gold_status`を持つ(`experiment/schema.py`参照):

| 値 | 意味 |
|---|---|
| `reused_validated` | gold answerが、既に`reference/`内で(別の、今回より前の)実験によって記録された結果に由来する。シナリオの表面文言(登場人物名・ファイル名等)を変えていても、検証されたパターンの再現である場合はこちらに分類する |
| `draft_pending_review` | 今回このタスクの中でClaudeが新規に作成した(または既存シナリオを大きく改変した)シナリオ。gold answerはシナリオ作者(Claude)自身が仮に置いたものであり、**別の人間またはセッションによるレビューを経ていない** |

`experiment/runner.py`の`run_trial`は`gold_status: draft_pending_review`の
シナリオに対して、`allow_draft_gold=True`を明示しない限り例外を送出して実行を
拒否する(`experiment/README.md`「Scenario file schema」参照)。これは「Claudeが
シナリオを生成した場合でも、生成したものをそのままgoldとして採用しない」という
実装指示を、ドキュメント上の注意書きではなく**コード上の強制**として実装した
もの。draft状態のシナリオを走らせて良いのは動作確認・パイロットのためのdry runの
みであり、その結果を「実験の発見」として報告してはならない。

本ラウンドでは以下のシナリオが`draft_pending_review`である(§2〜§5で個別に詳細)。
正式なgold answerとして扱う前に、シナリオ作成者(Claude)とは別の人間によるレビュー
が必要:

- entity reference: `entity-case2-*`(3ファイル)
- condition: `condition-after-case1-*`(2ファイル、コード上「新規」扱い。理由は§3参照)、`condition-if-case1-*`(2ファイル)
- urgency: 全8ファイル(旧実験に客観的な行動評価の先例が無いため)
- time role: 全2ファイル(同上)

`reused_validated`なのは entity reference の `entity-case1-*`(3ファイル)と
condition の `condition-until-case1-*`(2ファイル)のみ。

---

## §2. 実験1: entity reference

### 仮説

`reference/experiment-h-full-vs-minimal-vs-nl.md`が初回実施した「entity参照の
優位性はAMPプロトコル全体に由来するのか、refs相当の最小構造だけで再現するのか」
という問いを、**シナリオ/gold answer/runnerを分離した再現可能な形**に整理する。
新しい主張は追加しない——これは実験Hの正式化であり、実験Hの発見(Full AMPと
Minimal AMPが同じ結果になった)を追試・拡張することが目的。

### 独立変数

`condition`(表現形式)。3水準:

| 値 | 内容 |
|---|---|
| `nl` | 自然言語のみ |
| `full_amp` | `act`/`predicate`/`agent`/`patient`/`recipient`をフル生成したAMP JSON |
| `minimal_structured` | `{"patient": "...", "recipient": "..."}`という、entity参照だけの独立した構造体(`act`も動詞も持たない) |

**注記(実装指示7番への対応)**: 将来の比較候補として、以下のA〜Dを記録して
おくが、**今回はB(NL+entity annotation)を実装しない**。

| 記号 | 内容 | 本ラウンドでの扱い |
|---|---|---|
| A | Natural Language | `nl`条件として実装済み |
| B | NL + entity annotation(自然文中に`[entity:report.pdf]`のような角括弧参照を埋め込む) | **未実装**。理由は下記「MAMPの形の曖昧さ」参照 |
| C | Minimal structured representation | `minimal_structured`条件として実装済み |
| D | Full AMP | `full_amp`条件として実装済み |

#### MAMPの形の曖昧さについての注記

このタスクの元になったレビュー(可変strictness仮説の検討)で指摘した通り、
「entity参照のみのMAMP」には**構造的に異なる2つの実現形**があり、両者は残る
曖昧性の性質が異なる:

- 実現形1(=上表のC): `{"patient": "...", "recipient": "..."}`という独立した
  構造体。自然文の統語(語順)が一切残らないため、role割り当ての曖昧性を持たない
- 実現形2(=上表のB): `"Send [entity:report.pdf] to [entity:alex]."`のように、
  自然文の中にentity参照を差し込む形。entity自体は一意に定まるが、"Send X to Y"
  という英文の語順に依存してrole(どちらが送る対象でどちらが受け手か)を推測する
  必要が残る

本ラウンドで`minimal_structured`(実現形1)のみを実装したのは、これが
`experiment-h`が実際に検証したMinimal AMPの定義そのものであり(`reference/experiment-h-full-vs-minimal-vs-nl.md`
19-20行目)、**既存の検証済み実験をそのまま再現・整理する**という今回のタスクの
範囲に収まるため。実現形2(B)は`reference/improvement-proposal-philosophy-review.md`
438行目の補記が触れているだけで一度も実験されておらず、これを追加するのは
「新しい実験デザインの導入」であり、今回の「既存実験の整理」という範囲を超える。
次のラウンドの候補としてここに明記するに留める(§6参照)。

### シナリオ

| case_id | gold_status | 由来 |
|---|---|---|
| `entity-case1` | `reused_validated` | `experiment-h`ラウンド2(S4)の「直近性 vs 動詞の意味的対応」競合パターンをそのまま再現(report-final.pdf / report-final-v2.pdf / report-final-reviewed.pdf) |
| `entity-case2` | `draft_pending_review` | case1と同型の競合構造を別ドメイン(請求書)で複製したもの。`experiment-h`の「限界」節が要求した「n数を増やす」ための第一歩だが、Claudeが今回新規作成したため未レビュー |

各caseは`nl`/`full_amp`/`minimal_structured`の3ファイル(計6ファイル)。

### gold answer

各caseにつき`{"entity": "<正解ファイル名>", "recipient": "<正解の宛先>"}`。
正解は「動詞と実際に結びついている対象」(例: case1ならTurn 1で"send"と結びついた
`report-final.pdf`)であり、「最も直近に言及された対象」(distractor)ではない。

### 評価指標

`experiment/scorers/entity_reference.py`: `parsed.entity == gold.entity`かつ
`parsed.recipient == gold.recipient`で`correct: bool`。自己申告の`confidence`は
`self_report`として記録するのみで、正誤判定には使わない(実装指示4番)。

### 成功条件(このラウンドの実験計画としての成功条件)

シナリオ/gold/runnerが分離され、`full_amp`と`minimal_structured`が同一の
scoring基準で比較可能な形で用意されていること。**性能上の「成功」(AMPが勝つ)は
この計画の成功条件ではない**——実験Hは既にFull AMP=Minimal AMPという結果を
示しており、それを再現しても反証しても、計画としては両方とも正しく機能した
ことになる。

### 反証条件

`full_amp`と`minimal_structured`の正答率に有意な差が出れば、実験Hの
「entity参照の優位性はrefs相当の最小構造だけで再現する」という暫定的な発見は
反証される(=`act`/`predicate`を含むフル構造に、entity参照だけでは代替できない
独自の価値があることになる)。

### 既知の限界(実装指示13番)

**この実験が明らかにできること**: `full_amp`と`minimal_structured`の間で、
entity/recipientの参照解決精度に差があるかどうか。

**この実験が明らかにできないこと**(`experiment-h-full-vs-minimal-vs-nl.md`
「限界と次にやるなら」2番からそのまま引き継ぐ、絶対に忘れてはならない限界):
**Minimal AMP(entity参照のみ)で「行為タイプ」(送る/削除する/転送する等、
何をすべきか)が本当に伝達できるかは、この実験でもまだ検証できない。**
本ラウンドのシナリオは全て、周辺のNL文脈(Turn1〜6)が「送る」という行為を
既に明示しており、`minimal_structured`条件でも受信側は文脈から行為を補える。
行為タイプの伝達を独立変数として測るには、複数のもっともらしい行為
(送る/転送する/削除する等)が拮抗し、かつentity自体は一意に定まるシナリオを
別途設計する必要がある——これは次のラウンドの最優先候補(§6)。

また、n=2(caseが2つ)は統計的な検証には遠く、`entity-case2`は未レビューの
draftである。samples数を増やす作業も次のラウンドに持ち越す。

---

## §3. 実験2: condition(until / after / if)

### 仮説

`reference/experiment-e-condition-structure.md`が`until`について自己申告
(「判断できない」→「判断できる」)で示した効果を、**実際の行動(送るべきか
どうかの判断)の正誤**という客観指標に置き換えて測定する。加えて、
`until`/`after`/`if`が本当に同じ「condition」という括りに入れてよいかを
横並びで見る(`reference/improvement-proposal-philosophy-review.md`§5が
提起した論点)。

### 独立変数

`condition`(構造の有無)。2水準:

| 値 | 内容 |
|---|---|
| `without_condition_field` | 元の条件節(until/after/if節)を落とし、平叙文の指示・約束だけを残した文面 |
| `with_condition_field` | 条件節を明示した文面 |

さらに`case_id`の接頭辞(`condition-until-`/`condition-after-`/`condition-if-`)
で条件の種類を区別する。

### シナリオと由来

| case_id | 種類 | gold_status | 由来・注記 |
|---|---|---|---|
| `condition-until-case1` | until | `reused_validated` | `experiment-e-condition-structure.md`のシナリオそのもの(AI-Aが確認するまでfile.aを送ってはいけない) |
| `condition-after-case1` | after | `draft_pending_review` | `experiment-b-comparison-matrix.md`の"after he finishes reviewing it"を下敷きにしているが、`improvement-proposal-philosophy-review.md`§5が指摘した代名詞照応の混入(“he”が誰を指すか)を除去するため人物を実体名(AI-A)に置き換えた。**これは表面的な言い換えではなく、測定対象そのものを変える改変**(照応問題を切り離すことが目的)なので、そのまま`reused_validated`とはせず、改めてdraft扱いにした |
| `condition-if-case1` | if | `draft_pending_review` | `if`(仮定条件)は`improvement-proposal-philosophy-review.md`§5が明記する通り、これまで一度も実例が無い。今回が最初の実験デザインであり、シナリオの妥当性自体(「意向を示すだけの発言」を承認と区別できるか)がレビュー待ち |

各caseは`without_condition_field`/`with_condition_field`の2ファイル(計6ファイル)。

### gold answer

`{"action": "send_now" | "do_not_send" | "cannot_determine"}`。判断基準:

- シナリオが定める「本当の意図」(条件節が本来あった場合の正しい行動)を
  gold answerとして固定する。`with_condition_field`版は条件が明示されているため
  常にgold通りに答えられるはず(天井の確認)
- `without_condition_field`版は**情報が失われた状態でも同じgold answerを目指す**
  ——つまり「情報が無いから分からなくて当然」ではなく、「情報が無いことで
  実際に間違った行動を選んでしまうか」を測る設計(実装指示8番の要求どおり)。
  `until`は「送らないでおく」方向の過剰な保守化、`after`は「送ってしまう」
  方向の過剰な積極化という、**逆方向の失敗リスクをそれぞれ検証する**ように
  意図的に設計した(詳細は各シナリオファイルの`metadata.risk_direction`)

例外は`condition-until-case1-without_condition`で、これは元の`experiment-e`が
実際に測った「判断できない」という自己申告と地続きの設計だが、今回は
「confirmしたという事実が来た時点で送るべきだ」という一意の正解(`send_now`)を
gold answerとして固定し、それを言い当てられるかで測る(§0で述べた通り、
`cannot_determine`は「常に安全な逃げ」ではなく、`condition`スコアラーの実装上、
`until`ケースの「本当は送るべきだったのに`cannot_determine`や`do_not_send`と
答えてしまう」という下振れも、`send_now`という単一のgoldに対する不正解として
検出される)。

### 評価指標

`experiment/scorers/condition.py`: `parsed.action == gold.action`。
`gold.action == "cannot_determine"`なのに`parsed.action`がそれ以外(=根拠なく
断定した)の場合は`detail.overconfident_guess = true`を別途記録する
(本ラウンドのシナリオでは`cannot_determine`をgoldに置いたケースは無いが、
将来ケースを追加する際にこの検出ロジックをそのまま使えるようにしてある)。

### 成功条件

3種類(until/after/if)が同一の評価軸・同一のファイル形式で走らせられること。
`experiment-e`が個別に持っていた「until限定の自己申告」という測定方法を、
汎用的な行動ベースの測定に置き換えられていること。

### 反証条件

`improvement-proposal-philosophy-review.md`§5が示した通り、以下のいずれかが
反証パターンになる:

- until/after/ifの3種類とも同水準の効果(with群の正答率がwithout群を明確に
  上回る)が再現されれば、`condition: {type, clause}`という単一の統一カテゴリ
  案([`experiment-e-condition-structure.md`](experiment-e-condition-structure.md)
  の仮設計)が3種類とも支持される
- `until`/`after`はうまく再現するが`if`だけ効果が乏しい、または`if`の
  gold answer自体の妥当性にレビューで疑義が出れば、`if`を`condition`という
  括りから切り離す、または`condition`という括り自体を再検討する根拠になる
  (これは本ラウンドで既に予期している——`condition-if-case1`のmetadataに
  「gold answerの前提自体が論点になりうる」ことを明記済み)

### 既知の限界

- `condition-after-case1`と`condition-if-case1`は共にdraft。特に`if`は
  「"looks fine, no changes needed"を承認とみなすかどうか」という、シナリオ
  設計者の解釈に依存した部分がgold answerに入り込んでいる。これは
  `improvement-proposal-philosophy-review.md`§5が事前に警告していた
  「`if`は実例ゼロ」という弱さがそのまま今回のdraftにも表れたもので、
  隠さずそのまま記録する
- caseは各種類1つのみ(n=1)。`improvement-proposal-philosophy-review.md`が
  要求する「複数type・複数シナリオでの再現」という基準にはまだ届いていない
- **この実験が明らかにできること**: 条件節の構造化の有無が、特定の1つの
  follow-up fact(confirmしたか/reviewを始めたか/承認したか)に対する行動判断の
  正誤に影響するかどうか
- **この実験が明らかにできないこと**: 複数の条件が同時に成立する場合
  (AND/OR)、条件の入れ子、`until`/`after`/`if`以外の条件表現(unless等)。
  これらは`improvement-proposal-philosophy-review.md`§5・§6が既に「実例ゼロ、
  追加しない」と結論しており、本実験もその結論を覆す設計にはしていない

---

## §4. 実験3: urgency

### 仮説

`reference/experiment-a-intent-roundtrip.md`が観測した「urgency(緊急性)は
AMPへの変換の入口で正直に失われる」という1件の実例を、**実際に行動の順序を
誤らせるかどうか**という客観指標で追試する。旧実験は自己申告(「urgencyを
表現できなかった」)のみで、行動結果は一度も測っていない——これが今回、
この実験を一から設計する理由(既存資料に流用できる客観測定は存在しない)。

新しい`urgency`フィールドは設計しない(実装指示9番)。あくまで「今のAMPで
この情報を落とすと実害が出るか」だけを見る。

### 独立変数

`condition`。2水準:

| 値 | 内容 |
|---|---|
| `nl` | urgencyを示す自然言語表現(right now / today 等)を残したままの2つの依頼文 |
| `full_amp_dropped` | 同じ2つの依頼を、urgencyに対応するフィールドを持たない現行AMPの`request`としてレンダリングした場合の形(urgency情報は構造的に置き場所が無いため、そのまま欠落する) |

### シナリオ

| case_id | 緊急度の対比 | gold_status |
|---|---|---|
| `urgency-case1` | "right now"(5分後にAlexが発表) vs "eventually" | `draft_pending_review` |
| `urgency-case2` | "today" vs "when you have time" | `draft_pending_review` |

両方とも「2つの依頼のうちどちらを先に処理すべきか」を1つ選ばせる形式。
`case1`は実験Aで実際に観測された極端な対比(right now/eventually)を再現し、
`case2`はより微妙な対比(today/when you have time、実装指示9番が例示した
4フレーズのうち残り2つ)を新たに設計した。

各caseは`nl`/`full_amp_dropped`の2ファイル(計4ファイル)。

### gold answer

`{"first_task": "task_1" | "task_2"}`。正解は常に「urgencyの高い方のタスク」
(task_1)。`full_amp_dropped`条件でもgold answerは変えない——構造上その情報を
受け取れないはずの条件で、それでも正しい優先順位を選べるかどうかを見る設計
(NL条件が天井、AMP条件で正答率が落ちるかどうかが問い)。

### 評価指標

`experiment/scorers/urgency.py`: `parsed.first_task == gold.first_task`。

### 成功条件

`nl`条件と`full_amp_dropped`条件を同一の質問文形式・同一の採点基準で比較
できること。

### 反証条件

`full_amp_dropped`条件の正答率が`nl`条件と有意差が無ければ、「urgency情報の
欠落は実害にならない」という逆方向の発見になる——これは
`experiment-a-intent-roundtrip.md`が示した「1件のみの脱落確認」を、まさに
反証しうる形で追試したことになり、`improvement-proposal-philosophy-review.md`
§9-10ロードマップ3番が要求する「まず実害を測ってから構造を検討する」の
「実害が無かった」という結果も、対等な成果として記録する。

### 既知の限界

- 全シナリオが`draft_pending_review`。本実験は今回はじめて設計されたもので、
  再利用できる過去のgold answerが存在しない
- **この実験が明らかにできること**: 2択という単純化されたタスク優先順位
  判断において、urgency情報の欠落が選択を誤らせるか
- **この実験が明らかにできないこと**: 3つ以上のタスクが競合する場合、
  urgencyの度合いが連続的に変化する場合(閾値がどこにあるか)、`urgency`
  フィールドを実際に追加した場合にどの程度の値域(3値/5値等)が必要かは、
  本実験のスコープ外(実装指示9番が明示的に「構造を先に設計しない」と
  指定している範囲)

---

## §5. 実験4: time role(event_time vs message_time)

### 仮説

`reference/improvement-proposal-philosophy-review.md`§9-10ロードマップ4番が
提案した最小の切り口——「`time` role全体」ではなく「事象時刻(event_time) vs
メッセージ送信時刻(message_time)の区別だけ」——を、初めて客観的な行動指標で
検証する。

### 独立変数

`condition`。2水準:

| 値 | 内容 |
|---|---|
| `with_explicit_event_time` | メッセージ本文が事象の発生時刻を明示的に述べている |
| `message_time_only` | 現行AMPのpredicateがtense(過去/現在)しか持たず、事象の時刻を表す場所が無いため、envelopeの`timestamp`(送信時刻)しか手がかりが無い |

### シナリオ

`time-case1`(1ケースのみ、2ファイル)。改善提案書ロードマップ4番が例示した
"The report was uploaded at 10:00"(event_time) / "This message was sent at
10:00"(message_time)の対比をそのまま踏襲。

### gold answer

`{"event_time": "<HH:MM または 'unknown'>", "message_time": "<HH:MM>"}`。
`message_time_only`条件では事象の時刻はメッセージのどこにも書かれていない
ため、正しい答えは`"unknown"`——「分からないと正直に言えるか」自体が
gold answerである点は、条件(condition)実験の`cannot_determine`と同じ設計
思想(honest uncertainty is the correct answer, not a guess)。

### 評価指標

`experiment/scorers/time_role.py`: `parsed.event_time == gold.event_time`。
不正解時、`parsed.event_time == gold.message_time`であれば
`detail.conflated_with_message_time = true`を記録し、「時刻を答えられな
かった」のか「メッセージ送信時刻と混同した」のかを区別できるようにした。

### 成功条件

「事象時刻」と「メッセージ送信時刻」を区別させる質問文と、その混同を機械的に
検出できるscorerが揃っていること。

### 反証条件

`message_time_only`条件でも受信側が`"unknown"`と正直に答え続け、
`conflated_with_message_time`が発生しなければ、「event_time/message_timeの
混同は実害にならない」という結果になり、time roleの拡張自体の必要性が
(このシナリオでは)裏付けられなかったことになる。

### 既知の限界

- n=1。`draft_pending_review`
- **この実験が明らかにできること**: 事象時刻の手がかりが完全に無いとき、
  受信側がメッセージ送信時刻を事象時刻と混同するかどうか
- **この実験が明らかにできないこと**: タイムゾーン、相対時刻表現
  ("recently"等)、時刻の精度(秒/分)、複数の事象が異なる時刻に起きた場合の
  時系列関係——これらは`improvement-proposal-philosophy-review.md`が
  明示的に「time role全体からではなく最小の切り口から」と指定した範囲外
  であり、意図的にスコープ外にしている

---

## §6. モデル横断

`experiment/README.md`「Cross-model runs」に実装の詳細を記載。この計画上の
方針は:

- 同一のscenarioファイル(同一の`prompt`・同一の`gold`)を、Claude系・
  Gemini系それぞれに通す
- promptも採点方法(scorer)もモデルごとに変えない。変更が必要になった場合は
  差分を`metadata`または別途の記録として明示し、暗黙に変えない
  (実装指示11番)
- `reference/experiment-cross-model-verification.md`が確立した「評価軸を
  分離する」設計(entity identification / reference ambiguity / pragmatic
  interpretation / confidence を別々に聞く)は、本ラウンドのscorer設計
  (`entity`/`recipient`のみを客観的に問う。confidenceは`self_report`止まり)
  に既に反映されている

本ラウンドではモデル横断の実行(実際にGeminiで走らせること)はスコープに
含めない——実行基盤(harness)の整備が目的であり、`experiment/README.md`
「Backends」に記載の通り、実際の実行(Claude・Geminiいずれも)は
`ManualTranscriptBackend`を介した手動の実行ステップとして今後行う。

---

## §7. 次のラウンドの候補(本ラウンドでは着手しない)

以下は本ラウンドの計画を実施・拡張する際の次の一手の候補であり、今回は
実装しない:

1. entity referenceで「行為タイプの伝達」を独立変数にしたシナリオを追加
   (§2の既知の限界で述べた、experiment-hが未解決のまま残した最重要の穴)
2. entity referenceの実現形B(NL+entity annotation、自然文への埋め込み)を
   `condition`の値として追加し、実現形C(独立構造体)との差を測る
3. `entity-case2`・`condition-after-case1`・`condition-if-case1`・urgency
   全ケース・time-case1の`draft_pending_review`を、別の人間またはセッション
   によるレビューで`reused_validated`に格上げする(またはレビューの結果
   シナリオ設計そのものを修正する)
4. 各実験のn数を増やす(現状は主要な発見パターンにつき1〜2ケースのみ)
5. 実際にモデル(Claude・Gemini)を通してtrialを実行し、
   `experiment/analysis/aggregate.py`で集計する

いずれも、この文書のgold answerやscorerの定義を変更する形での「あとから
基準をずらす」拡張ではなく、新しいシナリオファイル・新しい`condition`値の
追加という形で行うこと。

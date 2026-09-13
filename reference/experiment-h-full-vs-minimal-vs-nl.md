# 実験H: Full AMP vs Minimal AMP vs NL(AMPの必要最小量を測る)

`improvement-proposal-philosophy-review.md` 巻末「補記」で最優先実験(§9-10ロードマップ
1番)として設計された、`AMPの価値は本当にentity参照(refs)なのか`を検証する実験。
entity参照の優位性が「AMPプロトコル全体」に由来するのか、「refs相当の最小構造」だけで
再現するのかを、自己申告ではなく**正答率**で切り分ける。

## 方法

過去の実験(F/F-2/G/L3-matrix/cross-model-verification)と同じ**ブラインドテスト方式**を
採用: 受信側役のAI(Sonnet、新規セッション、実験の目的は一切明かさない)に、曖昧な
candidate群を含むカタログと会話文脈、そして3条件いずれかの「最終メッセージ」だけを渡し、
どのentityを対象と判断したかを機械的に採点する(自己申告のconfidenceは補助指標)。

3条件(提案書の設計どおり):

- **A: Natural Language** — 例: `"Send Alex the report."`
- **B: Full AMP** — 現行の`act`/`content`(predicate+agent/patient/recipient+refs等)をフル生成したJSON
- **C: Minimal AMP** — `act`も`predicate`も持たない、entity参照だけの最小構造。例:
  `{"patient": "entity:report-final-reviewed.pdf", "recipient": "entity:alex"}`

各条件でJSONのスキーマ説明は一切与えない(gemini-blind-test.mdと同じ方針——構造の
骨格が説明なしで伝わるかどうか自体も観察対象)。

## ラウンド1: 素朴な競合設計(3シナリオ)

提案書の例(`report-final.pdf` / `report-final-v2.pdf` / `report-final-reviewed.pdf`)を
下敷きに、「直近の話題」と「正解」を意図的にずらした3シナリオ(report/budget/invoice)を
作成し、A/B/Cそれぞれで受信側役に判定させた。

| シナリオ | 正解entity | NL FILE | NL conf | Full AMP FILE | Minimal AMP FILE |
|---|---|---|---|---|---|
| S1 report | report-final-reviewed.pdf | ✓ 正解 | 中 | ✓ 正解 | ✓ 正解 |
| S2 budget | budget-approved.xlsx | ✓ 正解 | 高 | ✓ 正解 | ✓ 正解 |
| S3 invoice | invoice-2024-101.pdf | ✓ 正解 | 中 | ✓ 正解 | ✓ 正解 |

### 発見: FILE判定に差が出なかった——設計の失敗

3シナリオとも自然言語側が正解した。原因を精査すると、**文脈の中で答えを
NL自身が明言してしまっていた**ことが分かった(例: S1は"Chris just finished
reviewing the report — that's the version we should send out."と、後段の
"v2 draft"への言及は単なる「混同注意」の警告であって、本物の参照競合には
なっていなかった)。これは実験G「試行1: 質問設計の失敗」と同型の罠——
**狙った曖昧性を、質問設計自体が実際には要求していなかった**。

一方で、この3シナリオはRECIPIENT判定で興味深い非対称を示した(下記コラム参照)。

## ラウンド2: 実験Gで実証済みの競合パターンを流用(S4)

素朴な設計が失敗したため、実験G試行3(直近性 vs 動詞の意味的対応の競合)と同型の
構造をそのまま流用した:

```
Turn1: Colleague: "Can you get report-final.pdf ready to send to Alex?"
Turn2: You: "Sure."
Turn3: Colleague: "Also, take a look at report-final-v2.pdf."
Turn4: You: "OK."
Turn5: Colleague: "And report-final-reviewed.pdf needs attention too."
Turn6: You: "Noted."
Turn7: Colleague: <最終メッセージ>
```

正解は`report-final.pdf`(動詞"send"と結びつくのはTurn1のみ)。直近性は
`report-final-reviewed.pdf`(直前の話題)を favor する——実験Gと全く同じ
「直近性 vs 意味的対応」の競合構造。

### 結果

| 条件 | FILE | RECIPIENT | CONFIDENCE | 複数解釈 |
|---|---|---|---|---|
| A: NL("Go ahead and send it to Alex.") | **判定不能** | Alex(名前のみ、ID化できず) | 低い | **はい** |
| B: Full AMP | report-final.pdf ✓ | entity:alex ✓ | 高い | いいえ |
| C: Minimal AMP | report-final.pdf ✓ | entity:alex ✓ | 高い | いいえ |

自然言語側の理由(そのまま引用): 「"it"はreport-final.pdf、report-final-v2.pdf、
report-final-reviewed.pdfのいずれも指しうる。3つとも話題に上っており、最も
直近の話題(reviewed版)が"送るべき対象"だと明言的に確認されたことは一度もない」。

**実験Gと完全に同じパターンが、独立したシナリオ(catalog・文脈を全て変更)で
再現した**: 自然言語は複数の競合する手がかりの間で判定を拒否し、Full AMP・
Minimal AMPはどちらも構造上一意に定まる。

## 発見1: entity参照の優位性はrefsだけで再現する(Full AMP ≈ Minimal AMP)

ラウンド1・2を通じて、**Full AMPとMinimal AMPは全4シナリオで完全に同じ結果
(FILE正解・RECIPIENT正解・confidence高い・複数解釈なし)** だった。act/predicate
の有無はFILE/RECIPIENT判定の正答率に一切影響しなかった。

これは提案書・巻末補記が示した解釈パターン表の

> NL 62% / Full AMP 98% / Minimal AMP 97% →
> 「AMPの優位性はほぼentity参照(refs)だけで説明できる」

に対応する結果である。今回のサンプル数(n=4)は正式な統計的検証には
遠いが、**方向としては「entity参照の優位性はAMPプロトコル全体ではなく、
refs相当の最小構造だけで再現する」という仮説を支持する**。

## 発見2: RECIPIENT判定における非対称(ただし要注意・測定アーティファクトの疑い)

ラウンド1の3シナリオ全てで、自然言語側は「送り先」を判定不能とした
(理由: カタログに"Alex"/"board"/"Acme AP"に対応するentity IDが存在しない
ため、正しい人物・組織は特定できても「entity:alexのようなID」には解決
できない、という誠実な回答)。Full AMP・Minimal AMPはどちらも
`recipient`フィールドに直接IDが書かれているため常に正解した。

**この差は測定アーティファクトである可能性が高い**: そもそも実験に
渡したカタログには人物・組織のentityを一つも含めておらず(ファイルの
IDのみ)、AMP側のメッセージには`entity:alex`等のIDを実験者(筆者)が
直接埋め込んだ。つまりこの比較は「NL側が名前からIDへの変換手段を
与えられていない」条件と「AMP側にIDが最初から書いてある」条件を
比べているに過ぎず、**AMPの構造的優位性の証拠としては使えない**
(FILE判定のような、同一カタログ内での参照競合を問う設計になっていない)。
参考情報として記録するに留め、本実験の主結論には含めない。

## 限界と次にやるなら

1. **サンプル数が少ない**(genuine ambiguityを作れたのはS4の1ケースのみ)。
   実験Gの経験則どおり、狙った曖昧性を実際に要求する質問設計は難しく、
   今回もラウンド1の3シナリオは失敗作だった。次はS4と同型の競合パターンを
   3〜4件、catalogとcontextを変えて複製し、n数を増やす必要がある(F-2・
   L3-matrixが辿ったのと同じ拡張)。
2. **act/predicateの価値をFILE/RECIPIENT正答率だけで測るのは片手落ち**。
   今回の全シナリオで、周辺のNL文脈が常に「送る」という行為自体を
   明示していたため、Minimal AMP(`patient`/`recipient`のみ)でも
   受信側は「何をすべきか」を文脈から補えてしまった。**もしAMPメッセージ
   単体で(周辺のNL文脈なしに)行為の種類まで伝える必要がある場面を
   作れば、Full AMPとMinimal AMPの差が初めて出る可能性がある**——
   これは巻末補記が最後に触れた「Minimal AMPの中でも複数の実現形が
   考えられる」という次段階の論点そのもの。次はこの「行為タイプの
   伝達」を独立した評価軸として切り出すべき。
3. **RECIPIENT結果は測定アーティファクト**(上記発見2)であり、
   カタログに人物・組織entityを含めた上でNL側にも命名解決の
   手段を与える再設計が必要。
4. モデル横断検証(cross-model-verification.mdと同様、Geminiでの追試)は
   未実施。今回はSonnetのみ。
5. n=4のうち3件(ラウンド1)は「設計の失敗」に終わったが、これ自体を
   実験Gの教訓の**独立した再現**として記録する価値がある——狙った
   参照競合を作る質問設計は、想像以上に間違えやすい。

## 結論(暫定)

サンプル数は少ないが、方向性は明確に出た:

> **自然言語が崩れる本物の参照競合(実験G型)を作れたシナリオ(n=1)では、
> Full AMPとMinimal AMPは完全に同じ結果(正解・高confidence・曖昧性なし)
> だった。** これは「entity参照の優位性はAMPプロトコル全体に由来するのではなく、
> refs相当の最小構造だけで説明できる」という、巻末補記が最も強い発見パターン
> として挙げた仮説(NL 62% / Full 98% / Minimal 97%型)の方向性を支持する。

ただし今回の設計は(a)サンプル数がn=1(genuine ambiguity条件)と小さく、
(b)act/predicateが担うはずの「行為タイプの伝達」という別軸を測れていない、
という2つの理由で、巻末補記が要求する「Minimal AMPだけで代替できるか」
への最終的な答えにはまだ届いていない。次の一手は、上記「限界と次にやるなら」
1・2番の拡張(n数を増やし、行為タイプの伝達を独立して測る設計)である。

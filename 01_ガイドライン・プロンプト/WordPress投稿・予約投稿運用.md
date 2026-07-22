# WordPress投稿・予約投稿運用

HPブログをWordPressへ安全に投稿・予約するための正規手順。この文書を投稿運用の正本とし、固定HTMLの内容は `ブログ記事執筆マスターガイド.md` セクション11を正本とする。

## 固定要素の不変条件

公開・予約対象の記事は、次の順序と個数を守る。

1. TL;DR：1つ
2. 執筆者情報：1つ
3. 目次：1つ
4. 本文
5. 参考文献：研究を引用した場合のみ1つ
6. 免責事項：1つ
7. LINE案内：CTAボタンの前だけ。フッター内には入れない
8. 公式LINEボタン：1つ
9. フッター：中央配置の画像→区切り線→住所・院情報→区切り線
10. JSON-LD：1つ、記事末尾

フッターは `wp_fixed_elements.py` の `CANONICAL_FOOTER` と完全一致させる。画像には `text-align: center` と `aligncenter` を指定する。

自動preflightは、固定要素の個数・順序、LINE案内ブロック、正規フッター、JSON構文を検査する。TL;DRの内容、TOCリンクの意味的一致、免責・CTAの文章品質、JSON-LDノードの妥当性までは代替しないため、最終3種QAと人による確認を省略しない。

## 標準フロー

### 1. ローカル原稿の固定要素チェック

WordPressへ接続せずに検査する。

```bash
python3 post_to_wp.py "HPブログ記事/投稿前/記事名.md" --preflight-only
```

エラーがあれば `$wp-fixed-elements` で直し、本文と固定要素を含む全体QAをやり直す。固定要素を後から修正した場合も、スタイル・医療広告・文字混入の3チェックを再実行する。

### 2. WordPressへ下書き投稿

```bash
python3 post_to_wp.py "HPブログ記事/投稿前/記事名.md" --draft --create-terms
```

`post_to_wp.py` は投稿前に固定要素を自動検査する。検査は用語作成・画像アップロード・投稿APIより先に実行され、失敗時はWordPressへ書き込まない。

### 3. WordPress下書きの整形と固定要素同期

対象IDを確認し、必ずdry-runから始める。

```bash
python3 format_wp_drafts.py inventory
python3 format_wp_drafts.py fixed-elements --status draft --ids POST_ID
python3 format_wp_drafts.py fixed-elements --status draft --ids POST_ID --apply
python3 format_wp_drafts.py fixed-elements --status draft --ids POST_ID

python3 format_wp_drafts.py format --ids POST_ID
python3 format_wp_drafts.py format --ids POST_ID --apply
```

最後のfixed-elements dry-runが `PENDING=0` で、各記事の `errors` が空であることを確認する。

### 4. 次の予約枠を取得して投稿準備

```bash
python3 format_wp_drafts.py next-slot
python3 format_wp_drafts.py prepare --ids POST_ID --first-at NEXT_SLOT
python3 format_wp_drafts.py prepare --ids POST_ID --first-at NEXT_SLOT --apply
python3 format_wp_drafts.py plan --ids POST_ID --first-at NEXT_SLOT --plan PLAN.json
```

`NEXT_SLOT` には `next-slot` が返したISO 8601日時をそのまま使う。既存の予約日時は動かさず、最新予約の2日後13:00（JST）へ追加する。

### 5. WordPress上の完成稿を全体QA

WordPressのedit-context本文をQA用ファイルへ読み取り出力する。

```bash
python3 format_wp_drafts.py export --status draft --ids POST_ID --out-dir QA_EXPORT_DIR
```

コマンドが表示した `EXPORT_DIR` 内の `POST_ID.html` をQA対象にする。`manifest.json` の本文ハッシュ・status・日時も保存し、承認対象との取り違えを防ぐ。

固定要素を含む完成稿に対して、次の3チェックを実行する。

- japanese-blog-style-guard
- medical-compliance-checker
- chinese-char-detector

修正した場合はplanを作り直し、3チェックをすべて再実行する。合格した内容ハッシュだけを承認する。

```bash
python3 format_wp_drafts.py approve --plan PLAN.json --ids POST_ID
```

### 6. 予約をdry-runしてから適用

```bash
python3 format_wp_drafts.py schedule --plan PLAN.json
python3 format_wp_drafts.py schedule --plan PLAN.json --apply
```

`schedule` はQA承認、本文ハッシュ、予約キュー、WordPressタイムゾーン、固定要素を再検証する。いずれかが変わっていたら予約しない。

### 7. 予約後の再検証

```bash
python3 format_wp_drafts.py fixed-elements --status future --ids POST_ID
```

`PENDING=0`、`errors=[]`、`status=future`、予定日時がplanどおりであることを確認して完了とする。

## 予約投稿を一括修正する場合

予約済み記事の固定要素だけを同期する場合も、dry-run→apply→再dry-runの順を変えない。

```bash
python3 format_wp_drafts.py fixed-elements --status future --all
python3 format_wp_drafts.py fixed-elements --status future --all --apply
python3 format_wp_drafts.py fixed-elements --status future --all
```

- `--all` は対象が本当に全予約記事の場合だけ使う。通常は `--ids` を使う。
- apply前に変更対象のedit-context全文をJSONへバックアップする。
- 更新payloadは本文だけとし、`status`、`date`、`date_gmt` が不変であることを再取得して確認する。
- 途中失敗時は、失敗した当該記事を含む試行済み記事をバックアップ内容へ戻す。
- 正規状態で再実行した場合は、バックアップもPOSTも行わない。

## 禁止事項

- 予約投稿に `post_to_wp.py --publish` を使わない。
- 予約・公開記事に `post_to_wp.py --update-post-id` を使わない。同CLIは下書き以外を拒否する。
- WordPress管理画面で複数の予約日時を手作業変更しない。
- dry-runを確認せず `--apply` を実行しない。
- QA後に固定要素を変更したまま予約しない。
- バックアップやエラーを確認せず、失敗した処理を別コマンドで上書きしない。

## 実装上の正本

- 固定HTMLと文章：`ブログ記事執筆マスターガイド.md` セクション11
- 自動検査・正規フッター：`wp_fixed_elements.py`
- ローカル投稿：`post_to_wp.py`
- WordPress下書き整形・承認・予約・予約済み記事修正：`format_wp_drafts.py`
- 自動テスト：`tests/test_wp_fixed_elements.py`

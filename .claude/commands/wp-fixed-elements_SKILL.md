---
name: wp-fixed-elements
description: HPブログ記事のWordPress固定要素を追加・修復・検査する。投稿前の原稿整形、固定要素の不足確認、WordPress下書き・予約投稿の固定要素同期で使用する。
---

# WordPress固定要素

対象はこのリポジトリのHPブログ記事に限定する。本文内容は変えず、固定要素だけを扱う。

## 必ず読むファイル

- `01_ガイドライン・プロンプト/ブログ記事執筆マスターガイド.md` セクション11〜14
- `.Codex/skills/wp-fixed-elements/reference.md`（固定HTMLの正本）
- 投稿・予約・WordPress上の修正を行う場合は `01_ガイドライン・プロンプト/WordPress投稿・予約投稿運用.md`

## 手順

1. 対象記事を全文読む。
2. TL;DR、執筆者情報、目次、参考文献、免責事項、LINE案内、LINEボタン、フッター、JSON-LDを個別に数える。一部があるだけで完成と判断しない。
3. `TL;DR → 執筆者 → 目次 → 本文 → 参考文献（任意）→ 免責 → LINE案内 → CTA → 中央画像 → 院情報 → JSON-LD` の順にする。
4. LINE案内はCTA前だけに置き、フッター内から削除する。
5. フッターは正本から完全一致でコピーし、画像を中央配置して院情報を画像下へ置く。
6. `python3 post_to_wp.py "対象ファイル" --preflight-only` を実行し、全エラーを直す。
7. 固定要素を含む記事全体に、スタイル・医療広告・文字混入の3種QAを実行する。

## WordPress運用

- WordPressへはまず下書きとして投稿する。
- 予約は `format_wp_drafts.py` の `plan → approve → schedule` だけを使う。
- 予約記事の修正は `fixed-elements --status future --ids ...` をdry-run→apply→再dry-runの順で行う。
- `post_to_wp.py --update-post-id` を予約・公開記事に使わない。
- `--all` は全件が対象だと確認できた場合だけ使う。

固定要素を後から変更した場合はQA承認を無効とし、3種QAをすべてやり直す。

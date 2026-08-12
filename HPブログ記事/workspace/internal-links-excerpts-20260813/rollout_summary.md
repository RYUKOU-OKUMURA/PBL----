# 内部リンク・抜粋パッチ（2026-08-13）

公開記事3本を更新。タイトル・公開日時・スラッグは不変。

## 対象
| ID | 変更 |
|----|------|
| 965 | 抜粋のみ。ミルウォーキー装具／ボストンブレースの固定範囲を先頭に |
| 612 | 抜粋のみ。「首の詰まり」「上を向くと痛い」と受診目安を先頭に |
| 976 | 本文に #1999・#2079 への文中リンク＋関連記事リスト先頭へ追加。抜粋・タイトルは据え置き |

## QA
- medical-compliance-checker: 公開可（変更箇所のみ）
- chinese-char-detector: 混入なし
- japanese-blog-style-guard: 旧本文の全面リライトではないため未実施

## 実行
```bash
python3 HPブログ記事/workspace/internal-links-excerpts-20260813/apply_patch.py plan
python3 HPブログ記事/workspace/internal-links-excerpts-20260813/apply_patch.py apply
python3 HPブログ記事/workspace/internal-links-excerpts-20260813/apply_patch.py verify
```

## ロールバック
`backup_965.json` / `backup_612.json` / `backup_976.json` から本文・抜粋・タイトルを復元。

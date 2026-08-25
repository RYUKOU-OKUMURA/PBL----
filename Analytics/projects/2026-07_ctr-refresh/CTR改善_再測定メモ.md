# CTR改善 再測定メモ（2026-08-14）

## いつ
- **2026-08-14（木）09:00** — launchd / カレンダーでリマインド
- 集計期間: **2026-08-07 〜 2026-08-13**（7日）
- ベースライン: `Analytics/periodic/2026-07-23_2026-07-29`

## 対象
| ID | 変更内容（2026-07-30 apply） |
|----|------------------------------|
| 965 | タイトル・抜粋・4装具比較表 |
| 612 | タイトル・抜粋・導入 |
| 976 | 抜粋・H2×2・関連記事4本 |

## 実行コマンド（1行）

```bash
bash Analytics/scripts/remeasure_ctr_improvements.sh --notify
```

ドライラン:

```bash
bash Analytics/scripts/remeasure_ctr_improvements.sh --dry-run
```

## 仕掛け一覧

| 仕掛け | 内容 |
|--------|------|
| **launchd** | `bash Analytics/scripts/install-ctr-remeasure-reminder.sh install` |
| **カレンダー** | `Analytics/reminders/2026-08-14_CTR再測定.ics` をダブルクリックで登録 |
| **レポート出力** | `Analytics/periodic/2026-08-07_2026-08-13/ctr_remeasure_report.md` |

## launchd 管理

```bash
bash Analytics/scripts/install-ctr-remeasure-reminder.sh status
bash Analytics/scripts/install-ctr-remeasure-reminder.sh uninstall   # 解除時
```

## 関連
- ロールアウト詳細: `HPブログ記事/workspace/ctr-refresh-20260730/rollout_summary.md`

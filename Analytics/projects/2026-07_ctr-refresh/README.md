# 2026-07 CTR改善 再測定

965 / 612 / 976 のタイトル・抜粋変更（2026-07-30 apply）の効果測定。

- ロールアウト: `HPブログ記事/workspace/ctr-refresh-20260730/`
- ベースラインCSV: `Analytics/periodic/2026-07-23_2026-07-29/`
- 再測定メモ: `CTR改善_再測定メモ.md`
- 8/14 の launchd 実行は `dotenv` 未導入で失敗している（`logs/ctr-remeasure.err`）

再測定の出力先は `measure_YYYY-MM-DD_YYYY-MM-DD/`（periodic には増やさない）。

```bash
bash Analytics/scripts/remeasure_ctr_improvements.sh --notify
```

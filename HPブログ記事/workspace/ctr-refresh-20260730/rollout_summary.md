# CTR改善ロールアウト完了（2026-07-30）

## 対象
| ID | 変更内容 |
|----|---------|
| 965 | タイトル・抜粋・4装具比較表 |
| 612 | タイトル・抜粋・導入3段落 |
| 976 | 抜粋・H2×2・関連記事4本（タイトル据え置き） |

## QA
- 各記事 composer-2.5-fast で medical / chinese-char / style-guard を実施
- 965: 比較表列名・装具名をQA反映
- 612: GSCクエリ「首の詰まり」をタイトル先頭に、導入を僕視点+受診目安に
- 976: 「今回紹介した」削除

## ベースライン（効果測定用）
- 期間: Analytics/periodic/2026-07-23_2026-07-29
- 965: GSC 284imp / 0click（12日）
- 612: GSC 57imp / 0click
- 976: PV leader、GSC 7click/189imp

## 再計測目安
2026-08-13 〜 08-20 に同指標を比較

## ロールバック
`backup_*.json` + `python3 wp_ctr_refresh.py` の rollback 相当は backup JSON から手動復元

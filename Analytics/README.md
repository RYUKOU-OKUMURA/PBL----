# Analytics — GA4 × WordPress × Search Console

フィジカルバランスラボ整体院 HP の分析データ保管。

## クイックスタート

```bash
# 直近の完了済みカレンダー半月（1–14日 または 15–末日）
bash Analytics/scripts/run_periodic.sh

# 進行中の半月を同じフォルダへ上書き
bash Analytics/scripts/run_periodic.sh --current

# dry-run
bash Analytics/scripts/run_periodic.sh --dry-run
```

生成物（期間フォルダ内）:
- `ga4_wp_gsc_analysis.csv` … 記事別 PV・セッション・GSC（クエリ×ページ由来。クリックは過少）
- `ga4_wp_gsc_analysis_queries.csv` … クエリ×ページ
- `gsc_site.csv` … サイト全体の検索クリック・表示（判断の正）
- `gsc_pages.csv` … ページ単位の検索（トップ・about を含む）
- `meta.json` … 窓の役割と実際の取得終了日

数値の確認は Cursor の Canvas。期間の見分けは [periodic/INDEX.md](periodic/INDEX.md)。

## フォルダ構成

```
Analytics/
├── README.md
├── 整理方針.md
├── scripts/
│   ├── run_periodic.sh
│   ├── period_window.py
│   └── generate_report_html.py
├── periodic/
│   ├── INDEX.md              # 正系列 / 月次 / ad-hoc の案内
│   ├── canonical.txt
│   ├── YYYY-MM-DD_YYYY-MM-DD/
│   └── ad-hoc/               # 転がし14日。比較に使わない
└── projects/                 # 特派
```

**正データ:** CSV  
**比較系列:** `periodic/canonical.txt`  
**ビュー:** Cursor Canvas（通常） / HTML（任意）

## セットアップ

```bash
pip install -r requirements.txt
```

`.env` に以下を設定（[.env.example](../.env.example) 参照）:

| 変数 | 用途 |
|------|------|
| WP_URL, WP_USER, WP_APP_PASSWORD | WordPress 記事取得 |
| GA4_PROPERTY_ID | GA4 プロパティID |
| GOOGLE_APPLICATION_CREDENTIALS | サービスアカウント JSON |
| GSC_SITE_URL | Search Console サイトURL |

## 定期運用

```bash
bash Analytics/scripts/run_periodic.sh
bash Analytics/scripts/run_periodic.sh --current
bash Analytics/scripts/run_periodic.sh --ad-hoc          # 例外の直近14日
bash Analytics/scripts/run_periodic.sh --end 2026-08-14  # その日を含む半月
```

月次など半月以外は `--output-dir` で場所を指定する:

```bash
python analyze_content_seo.py --start 2026-07-13 --end 2026-08-12 \
  --output-dir Analytics/periodic/2026-07-13_2026-08-12
```

指定しない場合、半月以外は `periodic/ad-hoc/` に入る。

## HTML 生成（任意）

```bash
python Analytics/scripts/generate_report_html.py --index
python Analytics/scripts/generate_report_html.py --all-periodic
```

## その他スクリプト

```bash
python Analytics/scripts/ga4_traffic_trend_analysis.py
python Analytics/scripts/search_growth_barrier_analysis.py
python Analytics/scripts/tv_redcode_spike_deep_analysis.py
python Analytics/scripts/build_tv_impact_excel.py
```

## 命名ルール

- **periodic 正系列:** カレンダー半月 `YYYY-MM-01_YYYY-MM-14` / `YYYY-MM-15_YYYY-MM-末日`
- **ad-hoc:** 上記以外の取得
- **projects:** `YYYY-MM_テーマ`

詳細は [整理方針.md](整理方針.md) と [periodic/INDEX.md](periodic/INDEX.md)。

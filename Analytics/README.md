# Analytics — GA4 × WordPress × Search Console

フィジカルバランスラボ整体院 HP の分析データ保管。

## クイックスタート

```bash
# 直近14日のデータ取得（CSV のみ・推奨）
bash Analytics/scripts/run_periodic.sh

# dry-run（実行コマンドの確認のみ）
bash Analytics/scripts/run_periodic.sh --dry-run
```

生成物:
- `Analytics/periodic/YYYY-MM-DD_YYYY-MM-DD/ga4_wp_gsc_analysis.csv`
- `Analytics/periodic/YYYY-MM-DD_YYYY-MM-DD/ga4_wp_gsc_analysis_queries.csv`

数値の確認・解説は Cursor の Canvas で行う。ブラウザ用 HTML が必要なときだけ後述のコマンドで生成する。

## フォルダ構成

```
Analytics/
├── README.md
├── 整理方針.md
├── scripts/
│   ├── run_periodic.sh        # 2週間定期取得（CSV）
│   └── generate_report_html.py  # HTML が必要なときのみ
├── periodic/                  # 定期取得（YYYY-MM-DD_YYYY-MM-DD/）
└── projects/                  # 特派分析
```

**正データ:** CSV  
**ビュー:** Cursor Canvas（通常） / HTML（任意・オンデマンド）

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
# 基本（今日を終了日として直近14日）
bash Analytics/scripts/run_periodic.sh

# 終了日を指定
bash Analytics/scripts/run_periodic.sh --end 2026-05-21

# 手動で期間指定
python analyze_content_seo.py --start 2026-05-08 --end 2026-05-21
```

### periodic フォルダの中身

| ファイル | 内容 |
|----------|------|
| `ga4_wp_gsc_analysis.csv` | 記事別 PV・セッション・GSC |
| `ga4_wp_gsc_analysis_queries.csv` | クエリ×ページ |
| `summary.md` | 任意。人間向け要約 |

## HTML 生成（任意）

定期取得では生成しない。ブラウザで開きたいときだけ:

```bash
# 1期間 + 横断 index
python analyze_content_seo.py --start 2026-05-08 --end 2026-05-21 --html

# 横断 index のみ
python Analytics/scripts/generate_report_html.py --index

# periodic 一括 + index
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

- **periodic:** `YYYY-MM-DD_YYYY-MM-DD`（開始_終了）
- **projects:** `YYYY-MM_テーマ`（例: `2026-03_tv-redcode`）

詳細は [整理方針.md](整理方針.md) を参照。

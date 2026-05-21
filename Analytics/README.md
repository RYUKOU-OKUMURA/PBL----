# Analytics — GA4 × WordPress × Search Console

フィジカルバランスラボ整体院 HP の分析データ保管・レポート生成。

## クイックスタート

```bash
# 直近14日のデータ取得 + HTML 生成（推奨）
bash Analytics/scripts/run_periodic.sh

# dry-run（実行コマンドの確認のみ）
bash Analytics/scripts/run_periodic.sh --dry-run
```

生成物:
- `Analytics/periodic/YYYY-MM-DD_YYYY-MM-DD/` … CSV + `index.html`
- `Analytics/index.html` … 横断ダッシュボード（動向分析付き）

## フォルダ構成

```
Analytics/
├── README.md
├── 整理方針.md
├── index.html                 # 横断ダッシュボード（自動生成）
├── scripts/
│   ├── run_periodic.sh        # 2週間定期取得
│   └── generate_report_html.py
├── periodic/                  # 定期取得（YYYY-MM-DD_YYYY-MM-DD/）
└── projects/                  # 特派分析（index.html 自動生成可）
```

**正データ:** CSV  
**ビュー:** HTML（自動生成。Looker Studio は使用しない）

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
python analyze_content_seo.py --start 2026-05-08 --end 2026-05-21 --html
```

### periodic フォルダの中身

| ファイル | 内容 |
|----------|------|
| `ga4_wp_gsc_analysis.csv` | 記事別 PV・セッション・GSC |
| `ga4_wp_gsc_analysis_queries.csv` | クエリ×ページ |
| `index.html` | 自動生成レポート |
| `summary.md` | 任意。人間向け要約 |

## HTML 生成

```bash
# 横断 index（動向メモ・推移グラフ・累積TOP10・projects リンク）
python Analytics/scripts/generate_report_html.py --index

# periodic 一括 + index
python Analytics/scripts/generate_report_html.py --all-periodic

# projects HTML 化
python Analytics/scripts/generate_report_html.py --all-projects

# 1プロジェクトのみ
python Analytics/scripts/generate_report_html.py --project Analytics/projects/2026-03_tv-redcode
```

### 横断 index の内容

- 動向メモ（ルールベース）
- PV / セッション / GSC クリックの推移グラフ
- 前期比列付き periodic 一覧
- 累積 PV TOP10 記事
- projects セクション

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

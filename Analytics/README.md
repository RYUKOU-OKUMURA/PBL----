# GA4 × WordPress × Search Console 統合分析

記事内容とアクセス数の相関、キーワードSEO効果を測定するための分析スクリプトの使い方。

## 概要

- **WordPress**: 記事メタデータ（タイトル・スラッグ・URL）
- **GA4**: ページ別PV・セッション・エンゲージメント
- **Search Console**: 検索クエリ・インプレッション・クリック

URL構造 `https://physical-balance-lab.com/1714/` のパス部分（1714）で照合。

## セットアップ

### 1. 依存パッケージ

```bash
pip install -r requirements.txt
```

または分析用のみ:

```bash
pip install python-dotenv requests google-analytics-data google-api-python-client google-auth
```

### 2. 環境変数（.env）

`.env.example` を参考に設定:

| 変数 | 用途 |
|------|------|
| WP_URL, WP_USER, WP_APP_PASSWORD | WordPress 記事取得 |
| GA4_PROPERTY_ID | GA4 プロパティID（数字のみ） |
| GOOGLE_APPLICATION_CREDENTIALS | サービスアカウントJSONのパス |
| GSC_SITE_URL | Search Console のサイトURL（未設定時は WP_URL から推測） |

### 3. Google Cloud 設定

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. **Google Analytics Data API** と **Search Console API** を有効化
3. サービスアカウント作成 → JSON キーをダウンロード
4. GA4: プロパティの「管理」→「プロパティのアクセス管理」でサービスアカウントを閲覧者として追加
5. Search Console: サイトの「設定」→「ユーザーと権限」でサービスアカウントを追加

## 使い方

```bash
# 直近28日間の統合分析（CSV出力）
python analyze_content_seo.py

# 期間指定
python analyze_content_seo.py --start 2025-01-01 --end 2025-01-31

# JSON出力
python analyze_content_seo.py --format json -o Analytics/analysis.json

# WordPress のみ取得（GA4/GSC 未設定時）
python analyze_content_seo.py --wp-only

# 別フォルダに出力
python analyze_content_seo.py --output-dir 分析結果/2025-03
```

## 出力

デフォルトの出力先: `Analytics/` フォルダ

- **メインCSV** (`ga4_wp_gsc_analysis.csv`): 記事別の PV・セッション・GSC クリック・インプレッション
- **クエリ別CSV** (`*_queries.csv`): 検索クエリ×ページのインプレッション・クリック・順位

## MCP と Python の推奨

- **Python スクリプト（本実装）**: 定期レポート、再現性、バッチ処理向け
- **GA4 MCP**: Cursor 内での対話的な分析向け。必要に応じて [googleanalytics/google-analytics-mcp](https://github.com/googleanalytics/google-analytics-mcp) を追加可能

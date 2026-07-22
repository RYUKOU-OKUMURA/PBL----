# AGENTS.md - PBL情報発信プロジェクト統合ガイド

PBL（フィジカルバランスラボ整体院）の情報発信コンテンツを制作するためのCodex統合ワークフロー。

---

## プロジェクト構造

```
PBL情報発信/
├── 01_ガイドライン・プロンプト/   # 執筆ガイド・SEOガイド・年間スケジュール
│   ├── ブログ記事執筆マスターガイド.md   # HPブログの全ルール
│   ├── WordPress投稿・予約投稿運用.md     # 投稿・予約・一括修正の正規手順
│   ├── SEO技術ガイド.md                  # SEO・構造化データ
│   └── 年間スケジュール.md               # LINEコラム年間テーマ
├── HPブログ記事/                  # HPブログ記事の保管先
├── LINEコラム/                    # LINEコラム記事の保管先
├── 03_研究資料・レビュー/         # PubMedリサーチ結果等
├── 身体系/                        # Obsidian Clippings（身体系）へのシンボリックリンク
├── post_to_wp.py                  # WordPress投稿スクリプト
├── format_wp_drafts.py            # WordPress下書き整形・承認・予約・固定要素同期
├── wp_fixed_elements.py           # 固定要素の共通検査・正規フッター
├── .Codex/
│   └── skills/                    # Codex用スキル定義
└── .claude/
    ├── agents/                    # Claude用サブエージェント定義
    └── commands/                  # Claude用コマンド/スキル定義
```

---

## コンテンツ種別と制作パイプライン

### HPブログ記事パイプライン

整体院HPに掲載する専門的なブログ記事。約3000文字、PASONA構成。

**ステップ1: リサーチ**
- テーマに関連するエビデンスが必要な場合、`pubmed-researcher` サブエージェントを起動
- 日本語テーマ → MeSH用語変換 → PubMed検索 → エビデンスレベル評価
- 結果は `03_研究資料・レビュー/` に保存を検討

**ステップ2: 執筆**
- `seitai-blog-pasona` スキルを使用
- 必ず `01_ガイドライン・プロンプト/ブログ記事執筆マスターガイド.md` を参照
- PASONA構成: Problem → Agitation → Solution → Narrow down → Action
- 一人称「僕」、です・ます調、専門用語は直後に平易説明
- 約3000文字、モバイルファースト

**ステップ3: WordPress固定要素の挿入**

`wp-fixed-elements` スキルを使用し、`01_ガイドライン・プロンプト/ブログ記事執筆マスターガイド.md` のセクション11〜13に従って固定要素を挿入する:
- TL;DR、執筆者情報、目次、免責事項、LINE CTA、フッター、JSON-LD
- 記事末尾は「参考文献（任意）→免責→LINE案内→CTA→中央画像→院情報→JSON-LD」の順にする
- LINE案内はCTA前だけに置き、フッター内へ重複させない
- 固定要素を含めた全体を次のQA対象にする

**ステップ4: 全体QA（1記事なら3つを並列実行）**

固定要素挿入後、以下の3つのサブエージェントを起動する。QA対象は **本文＋TL;DR＋執筆者情報＋目次＋免責事項＋LINE CTA＋フッター＋JSON-LD** の全体。

1. **japanese-blog-style-guard** - ブログスタイル準拠チェック
   - 一人称・文体・ナラティブ比率・PASONA構成・文字数・見出し構造
2. **medical-compliance-checker** - 薬機法・医療広告ガイドライン準拠チェック
   - 効果の断定・効能の保証・最上級表現・体験談の誇張
3. **chinese-char-detector** - 中国語文字混入チェック
   - 簡体字・繁体字・異体字の検出と修正

```
// 1記事のQA並列実行のイメージ（最大3つのTaskを同一メッセージで呼び出す）
Task(japanese-blog-style-guard, "記事ファイルパスを渡してチェック依頼")
Task(medical-compliance-checker, "記事ファイルパスを渡してチェック依頼")
Task(chinese-char-detector, "記事ファイルパスを渡してチェック依頼")
```

複数記事を扱う場合は、記事単位で順番に実行する。1つのメッセージで多数の記事や多数のTaskを同時起動しない。

**ステップ5: 修正**
- 3つのQA結果を統合し、メインセッションが記事を修正
- 重大な違反（薬機法Critical Violation等）は必ず修正してから次へ

**ステップ6: 投稿準備完了**
- 修正後、固定要素を含む全体に未レビュー箇所が残っていないことを確認
- `01_ガイドライン・プロンプト/WordPress投稿・予約投稿運用.md` に従う
- `post_to_wp.py --preflight-only` 合格後、WordPressへはまず下書き投稿する
- 予約は `format_wp_drafts.py` の `plan → approve → schedule` のみを使う
- 予約後は `fixed-elements --status future --ids ...` で `PENDING=0` と `errors=[]` を確認する

---

### LINEコラムパイプライン

LINE公式アカウントで配信する短めの健康コラム。15〜25行。

**ステップ1: テーマ確認**
- `01_ガイドライン・プロンプト/年間スケジュール.md` で該当週のテーマを確認
- 前後のコラムとの内容重複を避ける

**ステップ2: 執筆**
- `line-column-writer` スキルを使用
- 季節フック → 問題提起 → 専門的洞察 → 実践アドバイス → 励ましの締め(^^)/
- 絵文字は控えめ（2〜3個）、専門用語は使わない
- 15〜25行、モバイルファースト

**ステップ3: QA（2つを並列実行）**

LINEコラムでは style-guard は不要（ブログ専用）。以下の2つを並列実行:

1. **medical-compliance-checker** - 薬機法チェック
2. **chinese-char-detector** - 中国語文字混入チェック

**ステップ4: 修正**
- QA結果に基づき修正

**ステップ5: 保存**
- ファイル名: `YYYY-MM-DD_【タイトル】.md`
- 保存先: `LINEコラム/YYYY/`
- 配信曜日は毎週水曜日

---

## サブエージェント一覧

| エージェント | 用途 | 起動タイミング |
|-------------|------|---------------|
| `pubmed-researcher` | PubMed論文検索・エビデンス収集 | リサーチ段階（エビデンスが必要な場合） |
| `japanese-blog-style-guard` | ブログスタイル準拠チェック | HPブログ記事のQA段階 |
| `medical-compliance-checker` | 薬機法・医療広告準拠チェック | 全コンテンツのQA段階（プロアクティブに実行） |
| `chinese-char-detector` | 中国語文字混入チェック | 全コンテンツのQA段階（プロアクティブに実行） |

## スキル一覧

| スキル | 用途 |
|-------|------|
| `seitai-blog-pasona` | HPブログ記事の執筆（PASONA構成） |
| `medical-ad-compliance` | 医療広告・薬機法まわりの表現チェック |
| `wp-fixed-elements` | WordPress投稿前の固定要素追加 |
| `line-column-writer` | LINEコラムの執筆 |
| `pubmed-research` | PubMed検索の手動実行ガイド |

---

## 重要ルール

### ファイル命名
- HPブログ: `NN_タイトル.md`（シリーズ） or `タイトル.md`（単発）
- LINEコラム: `YYYY-MM-DD_【タイトル】.md`
- ファイル名に `"` `'` `` ` `` `\` `$` `!` を使わない

### QAは省略しない
- HPブログは固定要素挿入後、**必ず** QAサブエージェントを実行する
- QA対象は本文だけでなく、TL;DR、執筆者情報、CTA、フッター、JSON-LDを含む記事全体
- 特に medical-compliance-checker は薬機法リスクがあるため省略厳禁

### WordPress投稿・予約
- `post_to_wp.py --publish` に未来日を渡して直接予約しない
- 予約・公開記事を `post_to_wp.py --update-post-id` で更新しない
- `format_wp_drafts.py fixed-elements` は必ずdry-run→apply→再dry-runの順で使う
- `--all` は全件が対象だと確認できた場合だけ使い、通常は `--ids` を使う
- 固定要素を変更した場合は本文を含む3種QAをすべてやり直す

### 既存ガイドを参照する
- 執筆前に必ず該当するマスターガイドを読み込む
- 前回の記事を確認し、内容・表現の重複を避ける

---

## エラー記録・教訓

### 2026-02-06: 複数Task同時実行による拒否エラー

**発生状況**:
- 5つの記事に対してQAチェックを実行するため、1つのメッセージで5つのTaskツールを同時に呼び出した
- ユーザーによりツール使用が拒否され、記事3・4のチェックが完了しなかった

**エラーメッセージ**:
> "The user doesn't want to proceed with this tool use... STOP what you are doing and wait for the user to tell you how to proceed."

**原因**:
- 1つのメッセージで多数のTaskツールを同時に呼び出したことで、ユーザーが承認するのを躊躇した
- TeamCreateとTaskCreateの組み合わせが複雑になりすぎ、エージェント管理が困難になった

**教訓**:
- 複数のTaskを同時に実行する場合は、事前にユーザーに確認を取るか、段階的に実行する
- TeamCreateは慎重に使用し、シンプルなアプローチを優先する
- ファイル削除以外はユーザーに許可を求める必要はない（ユーザー指定）

**今後の対策**:
- 複数記事のQAチェックを実行する場合、1記事ずつ順番に実行するか、3つ以内のTaskに分割して実行する
- TeamCreateを使用する場合は、必ず完了後にTeamDeleteを実行し、リソースを適切に管理する

---

## Cursor Cloud specific instructions

### 概要

このリポジトリはPython 3.12ベースのCLIツール群（Webアプリケーションではない）。主要コンポーネントは以下の通り:

| スクリプト | 用途 | 外部依存 |
|-----------|------|---------|
| `post_to_wp.py` | 固定要素preflight＋WordPress下書き投稿 | WordPress REST API（`.env`の`WP_URL`/`WP_USER`/`WP_APP_PASSWORD`） |
| `format_wp_drafts.py` | 下書き整形・QA承認・予約・固定要素同期 | WordPress REST API |
| `wp_fixed_elements.py` | 投稿前固定要素の共通検査 | なし |
| `analyze_content_seo.py` | GA4 × WordPress × Search Console 統合分析 | WordPress REST API + Google APIs（サービスアカウントJSON必要） |
| `Analytics/*.py` | 各種トラフィック分析スクリプト | Google APIs |

### 依存関係

- `pip install -r requirements.txt` で全依存がインストールされる
- Node.js/Docker/データベースは不要

### スクリプト実行

- **接続なしpreflight**: `python3 post_to_wp.py <markdown_file> --preflight-only`
- **WordPress下書き投稿**: `python3 post_to_wp.py <markdown_file> --draft [-v]`
- **予約記事の固定要素確認**: `python3 format_wp_drafts.py fixed-elements --status future --ids <ID...>`
- **SEO分析（WPのみ）**: `python3 analyze_content_seo.py --wp-only`（GA4/GSCはサービスアカウントJSONが必要で、Cloud VMでは利用不可）

### 注意点

- `.env` ファイルにWordPress認証情報が含まれている。`WP_URL`、`WP_USER`、`WP_APP_PASSWORD`が正しく設定されていればWordPress APIは使用可能
- `GOOGLE_APPLICATION_CREDENTIALS` はローカルmacOSパスを参照しており、Cloud VMでは無効。GA4/GSC関連機能はスキップされるが、`analyze_content_seo.py --wp-only`モードでWordPressデータのみの分析は可能
- `身体系/` シンボリックリンクはローカルGoogle Driveパスを参照しており、Cloud VMでは無効（壊れたシンボリックリンク）。動作には影響なし
- 固定要素の自動テストは `python3 -m unittest discover -s tests -v` で実行する
- 記事内容の品質管理はQAサブエージェント（`japanese-blog-style-guard`、`medical-compliance-checker`、`chinese-char-detector`）が担当する

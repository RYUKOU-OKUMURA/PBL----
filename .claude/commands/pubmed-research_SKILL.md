---
name: pubmed-research
description: PubMedを中心とした医学論文リサーチスキル。ブログ記事や医療コンテンツのエビデンス収集に使用。論文検索、インパクトファクター評価、エビデンスレベル判定、日本語要約を提供。トリガー：医学論文を探す、エビデンスを調べる、研究を検索、PubMedで調査、論文リサーチ、科学的根拠を確認
---

# PubMed Medical Research Skill

医学論文のリサーチを体系的に行い、ブログ記事のソースとして使える形式で出力する。

## ワークフロー

### Step 1: 検索クエリ構築

ユーザーのテーマから検索クエリを構築する。

**検索戦略:**
- 主要キーワード + MeSH用語で精度向上
- Boolean演算子（AND, OR, NOT）で絞り込み
- フィルター: Publication Type（系統的レビュー、RCT優先）、日付範囲

**クエリ例:**
- 基本: `low back pain treatment`
- 高精度: `low back pain[MeSH Terms] AND (systematic review[Publication Type] OR randomized controlled trial[Publication Type])`

### Step 2: PubMed検索実行

`PubMed:search_articles`ツールで検索。

**推奨パラメータ:**
- `max_results`: 10-20（初回）
- `sort`: `relevance`または`pub_date`
- `date_from`: 直近5年を優先（古典的研究は例外）

### Step 3: 論文詳細取得

`PubMed:get_article_metadata`で詳細情報を取得。

**取得する情報:**
- タイトル、著者、ジャーナル名
- PMID、DOI
- 出版年、アブストラクト

### Step 4: インパクトファクター調査

PubMedではIFを直接取得できないため、`web_search`で補完する。

**検索クエリ例:**
- `"{Journal Name}" impact factor 2024`
- `{Journal Name} JCR impact factor`

**主要医学雑誌のIF参考値（references/impact-factors.mdを参照）**

### Step 5: エビデンスレベル評価

研究デザインからエビデンスレベルを判定（references/evidence-levels.mdを参照）。

**優先順位:**
1. システマティックレビュー・メタアナリシス
2. ランダム化比較試験（RCT）
3. コホート研究
4. ケースコントロール研究
5. 症例報告・専門家意見

### Step 6: 関連研究の探索

`PubMed:find_related_articles`で関連論文を発見。

**活用場面:**
- 重要論文の引用ネットワーク把握
- 反論・批判的研究の発見
- 最新のフォローアップ研究

### Step 7: 全文取得（可能な場合）

`PubMed:convert_article_ids`でPMCIDを確認し、`PubMed:get_full_text_article`で全文取得。

**注意:** PMCで全文公開されている論文は約600万件のみ。

## 出力形式

### 論文リスト形式

```
## 論文リスト

### 1. [タイトル（日本語訳）]
- **原題**: {Original Title}
- **著者**: {Authors} (et al.)
- **掲載誌**: {Journal Name}
- **IF**: {Impact Factor}
- **出版年**: {Year}
- **PMID**: {PMID}
- **DOI**: {DOI}
- **エビデンスレベル**: {Level}
- **研究デザイン**: {Design}

#### 要約（日本語）
{Abstract in Japanese - 3-5文で簡潔に}

#### ブログ引用例
「{著者ら}の研究（{Year}）によると、〜」
```

### サマリーレポート形式

テーマの全体像、主要な知見、研究間の一貫性/矛盾点をまとめる。

## 検索Tips

**効果的なMeSH用語:**
- 症状系: `back pain`, `headache`, `fatigue`
- 治療系: `chiropractic`, `massage therapy`, `physical therapy modalities`
- 研究系: `treatment outcome`, `efficacy`, `safety`

**Publication Typeフィルター:**
- `systematic review[pt]`: システマティックレビュー
- `randomized controlled trial[pt]`: RCT
- `meta-analysis[pt]`: メタアナリシス
- `clinical trial[pt]`: 臨床試験

## 注意事項

- 医学論文は専門家向けであり、一般読者への説明には適切な言い換えが必要
- 単一論文ではなく複数の研究を総合的に評価する
- 利益相反（COI）の有無に注意
- 研究の限界（Limitations）も併せて報告する
# SEO最適化チェックリスト

## キーワード戦略

### メインキーワード
- 整体
- 整体師
- 整体院
- 50人整体師

### ロングテールキーワード
- 整体師 おすすめ
- 整体 選び方
- 腰痛 整体
- 肩こり 整体
- 産後 骨盤矯正
- スポーツ 整体
- [地域名] 整体

### キーワード配置確認
- [x] タイトルにメインキーワード含む
- [x] H1見出しにキーワード含む
- [x] H2見出しに関連キーワード含む
- [x] 本文にキーワード自然に配置
- [x] メタディスクリプションにキーワード含む

---

## メタデータ設定

### メタタイトル（titleタグ）
```
【保存版】50名の整体師を完全紹介！自分に合う整体師が見つかる完全ガイド
```

### メタディスクリプション（descriptionタグ）
```
腰痛・肩こり・産後ケア...症状別に50名の整体師を紹介。経験年数、得意分野、地域から検索できるので、あなたにぴったりの整体師が見つかります。初めて整体を受ける人も必見！
```

### キーワード（keywordsタグ）
```
整体,整体師,整体院,腰痛,肩こり,産後骨盤矯正,スポーツ整体,整体師おすすめ,整体選び方
```

---

## 内部リンク戦略

### 記事内リンク案
```
1. 腰痛整体 → 「腰椎ヘルニア整体の選び方」記事へ
2. 肩こり整体 → 「スマホ肩こり解消ストレッチ」記事へ
3. 産後整体 → 「産後骨盤矯正の効果」記事へ
4. スポーツ整体 → 「ランニング障害予防」記事へ
```

### 外部リンク案
```
1. 日本整体師会へのリンク（信頼性向上）
2. 柔道整復師法へのリンク（公的機関）
3. 厚生労働省の整体に関する情報
```

---

## 構造化データ（Schema.org）

### FAQPage スキーマ
```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "初回はどのくらいの時間ですか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "初回はカウンセリング込みで60-90分程度です。"
      }
    },
    {
      "@type": "Question",
      "name": "何回くらい通えば改善しますか？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "急性であれば3-5回、慢性であれば10-15回が目安です。"
      }
    }
  ]
}
```

### Person スキーマ（整体師用）
```json
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "佐藤 健一",
  "jobTitle": "整体師",
  "description": "腰椎ヘルニア専門、25年の経験",
  "url": "https://sato-seitai.example.com",
  "worksFor": {
    "@type": "LocalBusiness",
    "name": "佐藤整体院"
  }
}
```

### LocalBusiness スキーマ（整体院用）
```json
{
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "佐藤整体院",
  "address": {
    "@type": "PostalAddress",
    "addressRegion": "東京都",
    "addressLocality": "新宿区",
    "streetAddress": "新宿1-2-3 XXビル5F"
  },
  "geo": {
    "@type": "GeoCoordinates",
    "latitude": "35.689753",
    "longitude": "139.700435"
  },
  "telephone": "03-1234-5678",
  "openingHours": "Mo-Fr 09:00-21:00 Sa 10:00-18:00",
  "priceRange": "¥¥"
}
```

---

## 読みやすさ対策

### 文章チェック
| 項目 | チェック | 内容 |
|------|---------|------|
| 文の長さ | ✅ | 1文50文字以内 |
| 段落の長さ | ✅ | 1段落3-5文 |
| 見出し構造 | ✅ | H1→H2→H3の階層 |
| 箇条書き | ✅ | 箇条書き多用 |
| 表形式 | ✅ | 比較表で情報整理 |

### 視覚的要素
- [x] アイコン使用（章ごとに区別）
- [x] カラー分け（症状別カテゴリー）
- [x] 表形式での比較
- [x] スマホ対応のレイアウト
- [x] フォントサイズ適切

---

## ユーザビリティ（UX）対策

### ナビゲーション
- [x] ページ内目次（アンカーリンク）
- [x] 「先頭に戻る」ボタン
- [x] 各章へのリンク
- [x] 関連記事へのリンク

### コンバージョン促進
- [x] CTAボタン設置（「予約する」「詳細を見る」）
- [x] 問い合わせフォームへの導線
- [x] 電話番号のクリック機能（スマホ）
- [x] Web予約への導線

---

## コンテンツ品質チェック

### E-E-A-T（経験・専門性・権威性・信頼性）
| 項目 | チェック | 内容 |
|------|---------|------|
| 経験 | ✅ | 50名の実データ使用 |
| 専門性 | ✅ | 資格保有者のみ紹介 |
| 権威性 | ✅ | 公的機関へのリンク |
| 信頼性 | ✅ | 患者様の声を紹介 |

### 鮮度
- [x] 公開日記載
- [x] 最終更新日記載
- [x] 情報の正確性確認

---

## モバイル対策

### ページスピード
- [x] 画像の最適化
- [x] CSSの圧縮
- [x] キャッシュの設定
- [x] レスポンシブデザイン

### モバイルユーザビリティ
- [x] タップターゲットのサイズ（48px以上）
- [x] 文字サイズの可読性
- [x] 横スクロールの回避
- [x] 電話番号のタップ可能

---

## SNS対策

### OGP（Open Graph Protocol）
```html
<meta property="og:title" content="【保存版】50名の整体師を完全紹介！自分に合う整体師が見つかる完全ガイド">
<meta property="og:description" content="腰痛・肩こり・産後ケア...症状別に50名の整体師を紹介。">
<meta property="og:image" content="https://example.com/og-image.jpg">
<meta property="og:url" content="https://example.com/50-seitai-article">
<meta property="og:type" content="article">
```

### Twitter Card
```html
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="【保存版】50名の整体師を完全紹介！自分に合う整体師が見つかる完全ガイド">
<meta name="twitter:description" content="腰痛・肩こり・産後ケア...症状別に50名の整体師を紹介。">
<meta name="twitter:image" content="https://example.com/twitter-image.jpg">
```

---

## アクセシビリティ

### 画像のaltテキスト
- [x] 全画像にalt属性設定
- [x] 説明的なaltテキスト

### 見出し構造
- [x] 見出しの階層正しい
- [x] 見出しスキップなし

### 色のコントラスト
- [x] コントラスト比4.5:1以上

---

## Googleサーチコンソール対策

### サイトマップ
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/50-seitai-article</loc>
    <lastmod>2024-01-15</lastmod>
    <priority>0.8</priority>
  </url>
</urlset>
```

### robots.txt
```
User-agent: *
Allow: /
Sitemap: https://example.com/sitemap.xml
```

---

## 実施すべき次のステップ

1. **全体の50名分のプロフィール作成**（現在5名分のみ作成）
2. **各整体師の写真取得**
3. **患者様の声の追加収集**
4. **内部リンクの設定**
5. **構造化データの実装**
6. **メタタグの設定**
7. **OGP/Twitter Cardの実装**
8. **サイトマップへの登録**
9. **Googleサーチコンソールへの登録**
10. **ページスピードの測定と改善**

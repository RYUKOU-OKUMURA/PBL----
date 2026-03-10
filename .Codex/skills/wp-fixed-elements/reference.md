# WordPress固定要素 HTMLスニペット集

`01_ガイドライン・プロンプト/ブログ記事執筆マスターガイド.md` セクション11より。固定URL・画像パスはそのまま使用する。

---

## 1. TL;DR（要約）

```html
<p class="tldr">本記事のポイントを80〜120字で簡潔に。数字や具体的根拠を1つ以上含める。</p>
```

---

## 2. 執筆者情報

```html
<p><img class="alignleft wp-image-361 size-medium"
    src="https://physical-balance-lab.com/wp/wp-content/uploads/2024/05/プロフィール写真-300x300.jpg"
    alt="プロフィール写真" width="300" height="300" /></p>
<p>&nbsp;</p>
<p>&nbsp;</p>
<p>&nbsp;</p>
<p>&nbsp;</p>
<p>&nbsp;</p>
<p>この記事を監修している人：奥村龍晃（柔道整復師資格保有）<br />
ーーーーーーーーーーーーーーーーーーーーーーーーーーーーーー</p>
<p>こんにちは！</p>
<p>脊柱側弯症専門のフィジカルバランスラボ整体院、<br />
院長の奥村龍晃です。</p>
<p>&nbsp;</p>
```

---

## 3. 目次

見出しに応じて `href` と `id` を対応させる。日本語のまま使用。

```html
<nav class="toc"><strong>目次</strong>
<ol>
  <li><a href="#はじめに">はじめに</a></li>
  <li><a href="#なぜ起こるのか">なぜ起こるのか</a></li>
  <li><a href="#解決の方向性">解決の方向性</a></li>
  <li><a href="#今日からできること">今日からできること</a></li>
  <li><a href="#まとめと次の一歩">まとめと次の一歩</a></li>
</ol>
</nav>
```

---

## 4. 免責事項

```html
<div class="disclaimer">
<strong>※免責事項</strong><br />
本記事の内容は一般的な情報提供を目的としており、個別の診断や治療を意図したものではありません。<br />
痛みや不調がある場合、運動中に痛みが出た場合は中止し、必要に応じて医療機関にご相談ください。<br />
2週間以上症状が続く場合は、専門家への受診をおすすめします。
</div>
```

---

## 5. LINE案内とCTAボタン

```html
<div>&nbsp;</div>

<div>
<p>公式LINEから24時間受け付けてます！<br />
お困りのことがありましたら、<br />
いつでもお問い合わせください(^^)/</p>
</div>

<p>&nbsp;</p>

<div class="q_button_wrap"><a class="q_custom_button q_custom_button3" href="https://lin.ee/cZKMhZ6" target="_blank" rel="noopener">公式LINE</a></div>

<p>&nbsp;</p>
```

---

## 6. フッター

```html
<footer>
<p>公式LINEから24時間受け付けてます！<br />
お困りのことがありましたら、<br />
いつでもお問い合わせください(^^)/</p>

<p><img class="alignleft size-full wp-image-629"
    src="https://physical-balance-lab.com/wp/wp-content/uploads/2024/05/ogp.jpg"
    alt="レッドコード整体" width="1200" height="630" /><br />
ーーーーーーーーーーーーーーーーーーーーーーーーーーーー</p>

<p>〒464-0026<br />
愛知県名古屋市千種区井上町117 井上協栄ビル2階<br />
名古屋市営地下鉄東山線「星ヶ丘駅」2番口徒歩2分<br />
愛知、名古屋で脊柱側弯症の治療なら『レッドコード整体』<br />
フィジカルバランスラボ整体院</p>

<p>ーーーーーーーーーーーーーーーーーーーーーーーーーーーー</p>
</footer>
```

---

## 7. 参考文献（任意）

研究エビデンスを引用した場合のみ。免責事項の前に配置。

```html
<h2 id="references">参考文献</h2>
<ul>
  <li>論文タイトル（著者名）<br />
      <a href="https://pubmed.ncbi.nlm.nih.gov/xxxxx/">https://pubmed.ncbi.nlm.nih.gov/xxxxx/</a></li>
  ...
</ul>
```

---

## 8. JSON-LD テンプレート

記事タイトル・TL;DR・「今日からできること」の内容に応じて埋める。

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Article",
      "headline": "記事タイトル",
      "description": "TL;DRと同一",
      "author": {
        "@type": "Person",
        "name": "奥村龍晃",
        "jobTitle": "柔道整復師"
      },
      "publisher": {
        "@type": "Organization",
        "name": "フィジカルバランスラボ整体院",
        "url": "https://physical-balance-lab.com"
      }
    },
    {
      "@type": "HowTo",
      "name": "記事テーマに沿った名称",
      "step": [
        {"@type": "HowToStep", "name": "項目1の見出し", "text": "項目1の要約"},
        {"@type": "HowToStep", "name": "項目2の見出し", "text": "項目2の要約"},
        {"@type": "HowToStep", "name": "項目3の見出し", "text": "項目3の要約"}
      ]
    }
  ]
}
</script>
```

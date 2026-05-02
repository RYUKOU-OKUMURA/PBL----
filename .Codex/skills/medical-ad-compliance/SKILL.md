---
name: medical-ad-compliance
description: Review healthcare marketing copy for compliance with Japanese medical advertising rules, including 医療広告ガイドライン, あはき法, 柔整法, and nearby risk areas such as 誇大表現, 比較優良表現, 体験談, and ビフォーアフター表現. Use when Codex is asked to do an 広告チェック, コンプライアンス確認, 薬機法チェック, 公開前レビュー, or rewrite blog posts, LINE columns, website copy, LPs, and profile text for clinics, osteopathic practices, acupuncture, or seitai businesses.
---

# Medical Ad Compliance

Use this skill to reduce publication risk before healthcare-related copy goes live. Treat the result as an editorial compliance review, not legal advice.

## Load This Resource

- Load `reference.md` when you need statutory detail, channel-specific nuance, or rewrite examples.

## Workflow

1. Read the entire draft and identify the content type: blog article, LINE column, website page, profile, CTA block, testimonial section, or campaign copy.
   - For repository HP blog articles, confirm that fixed elements are included in scope: body, TL;DR, author block, CTA, footer, and JSON-LD.
   - Classify the business type as one of `医療機関 / 柔整 / 整体 / 混合`.
2. Scan high-risk claims first: guaranteed outcomes, cure language, superiority claims, exclusive claims, disease inducement, medical-act wording, testimonials, and before/after framing.
3. Check profession-specific restrictions. Distinguish between medical institutions, あはき, 柔整, and seitai-like businesses because the applicable risk profile changes.
4. Quote the exact risky phrase and explain why it is risky in plain Japanese.
5. Rewrite each risky phrase with safer wording that preserves the intended meaning.
6. End with a clear verdict using exactly one of: `公開可`, `要修正`, `法務確認`, `公開不可`.

## What To Flag

- 効果効能の断定: `治る`, `完治`, `必ず改善`, `絶対によくなる`
- 最上級・比較優良: `No.1`, `最高`, `唯一`, `他院より優れている`
- 医療行為の暗示: `診断`, `治療`, `処方`, `医療的に証明`
- 専門性の過剰訴求: `交通事故専門`, `骨盤矯正専門`, `唯一の技術`
- 体験談と結果保証: treatment-result stories, post-treatment changes, before/after images, or anonymous episodes that imply efficacy
- 相談例の逸脱: `よくある相談例` を超えて改善結果や施術後変化を示している表現
- 誘引性の高い疾患名の使い方: disease keywords used as direct acquisition bait
- 無資格業態での医療用語: seitai or similar services using physician-like language

## Rewrite Rules

- Prefer soft, support-oriented phrasing such as `改善を目指す`, `負担軽減をサポートする`, `ご相談ください`.
- Preserve factual business information when it is allowed: practitioner name, location, hours, reservation availability, parking, contact details.
- If evidence or credentials are mentioned, avoid turning them into superiority or guarantee claims.
- When in doubt, downgrade certainty, remove competitive positioning, and use `法務確認` if the expression may require expert judgment.

## Output Format

Use a compact markdown report:

```md
## 広告コンプライアンスチェック結果

- 対象: [title or file]
- 業態: 医療機関 / 柔整 / 整体 / 混合
- 確認範囲: 本文 / TL;DR / 執筆者情報 / CTA / フッター / JSON-LD
- 総合判定: 公開可 / 要修正 / 法務確認 / 公開不可

| カテゴリ | 判定 | 問題箇所 | 修正案 |
|---|---|---|---|

### 修正優先度が高い項目
- ...

### 補足
- ...
```

Always include the exact phrase to change and a concrete safer rewrite.

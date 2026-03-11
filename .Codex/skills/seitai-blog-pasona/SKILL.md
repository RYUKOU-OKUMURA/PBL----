---
name: seitai-blog-pasona
description: Write HP blog articles for this repository's seitai or clinic website using the established PASONA-based structure and voice. Use when Codex is asked to draft, rewrite, or expand a 健康ブログ記事, 整体院HP記事, 症状解説記事, セルフケア記事, or repository blog draft that should use first-person `僕`, `です・ます調`, patient-friendly explanations, and an approximately 3000-character flow.
---

# Seitai Blog PASONA

Use this skill for full website blog articles, not short social or LINE posts. Preserve warmth, specificity, and readable explanations for non-experts.

## Repository Context

- Read [ブログ記事執筆マスターガイド.md](/Users/ryukouokumura/マイドライブ（okumura@physical-balance-lab.net）/PBL情報発信/01_ガイドライン・プロンプト/ブログ記事執筆マスターガイド.md) before drafting.
- Read [SEO技術ガイド.md](/Users/ryukouokumura/マイドライブ（okumura@physical-balance-lab.net）/PBL情報発信/01_ガイドライン・プロンプト/SEO技術ガイド.md) when metadata, structured data, or search framing matters.
- Review nearby articles in the same series or folder so the new draft does not repeat the last post.

## Workflow

1. Clarify the article angle, target reader, and repository destination folder.
2. Gather supporting evidence if the claim needs research support. Use `$pubmed-research` when the article depends on literature.
3. Draft in PASONA order: reader problem, why it happens, solution direction, three at-home actions, and the next step.
4. Keep most of the article in natural paragraphs. Use numbered items only for `今日からできること`.
5. Add the required disclaimer at the end.
6. If the article is publication-bound, run `$medical-ad-compliance` before finalizing.

## Voice Rules

- Use first-person `僕`.
- Use `です・ます調`.
- Speak with professional warmth, not textbook distance.
- Explain technical terms immediately in plain Japanese or with a short analogy.
- Include at least one short anonymous patient episode when writing a full article from scratch.
- Avoid exaggerated guarantees, aggressive sales language, and dense blocks of unexplained jargon.

## Structural Rules

- Target roughly 3000 Japanese characters unless the user explicitly wants a different length.
- Use `##` and `###` headings.
- Keep paragraph flow natural. Do not turn the whole article into bullets.
- Make `今日からできること` a numbered list with exactly three actions.
- Include `痛みが出たら中止` in the self-care section.
- End with this disclaimer or a meaning-preserving equivalent:

```md
本記事は一般情報であり、個別の診断・治療を提供するものではありません。
痛みや違和感が出たら中止し、必要に応じて専門家へご相談ください。
```

## Save Path

If the user asks you to save the draft and does not specify a destination, default to `HPブログ記事/投稿前/`.

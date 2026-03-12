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
- Use patient-friendly search language in `title`, `H1`, `TL;DR`, `excerpt`, and major `H2` headings. Keep formal technical terms only where they improve precision or match real search intent.
- When a technical term matters for SEO or accuracy, introduce it once in the first half of the article as `平易語（専門語）` or `専門語、つまり平易語`, then use the plain term for most later mentions.
- Avoid raw clinician-facing terms in body copy, such as `介入`, `個別化`, `エビデンス強度`, and `生活機能スコア`. Rewrite them as patient-friendly phrases like `調整`, `その人に合わせること`, `研究の確かさ`, and `日常生活のつらさ`.
- In body text, introduce studies as `2025年の研究では` or `複数の研究をまとめたレビューでは`. Keep researcher names in references unless naming them is genuinely necessary.
- Include at least one short anonymous patient episode when writing a full article from scratch.
- Avoid exaggerated guarantees, aggressive sales language, and dense blocks of unexplained jargon.

## Structural Rules

- Target roughly 3000 Japanese characters unless the user explicitly wants a different length.
- Use `##` and `###` headings.
- Keep paragraph flow natural. Do not turn the whole article into bullets.
- Keep the reader-facing wording softer than the internal outline. For example, describe the solution flow as `今の状態を確認する → 無理のない調整を進める → 変化を確かめる`, not bare clinician shorthand like `評価→介入→再評価`.
- Make `今日からできること` a numbered list with exactly three actions.
- Include `痛みが出たら中止` in the self-care section.
- End with this disclaimer or a meaning-preserving equivalent:

```md
本記事は一般情報であり、個別の診断・治療を提供するものではありません。
痛みや違和感が出たら中止し、必要に応じて専門家へご相談ください。
```

## Save Path

If the user asks you to save the draft and does not specify a destination, default to `HPブログ記事/投稿前/`.

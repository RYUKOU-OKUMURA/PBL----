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

## Query-First Topic Selection (do this before writing)

Check the latest period's `Analytics/periodic/*/ga4_wp_gsc_analysis_queries.csv` and `HPブログ記事/ネタ帳_検索クエリ由来.md`, then:

1. Pick exactly ONE main query for the article, using wording that exists in real query data (or a natural variant). GSC data (2026-07) shows searchers type direct body-part+symptom phrases (`背中 片側 盛り上がる`, `側弯症 股関節の痛み`) and anxiety/decision words (`手術後 痛み いつまで`, `後遺症`, `できないこと`, `装具 種類`). Category labels like `大人の側弯症` and daily-scene words like `坂道`/`洗濯` have ZERO observed queries.
2. Confirm no existing article already targets the same main query. If one does, improve that article instead of writing a new one — stacking articles on one query splits ranking.

## Workflow

1. Clarify the article angle, target reader, and repository destination folder.
2. Gather supporting evidence if the claim needs research support. Use `$pubmed-research` when the article depends on literature.
3. Draft in PASONA order: reader problem, why it happens, solution direction, three at-home actions, and the next step.
4. Keep most of the article in natural paragraphs. Use numbered items only for `今日からできること`.
5. In the solution section, include a short "see a doctor first" paragraph covering red-flag symptoms (see Safety Red-Flags below).
6. Add the required disclaimer at the end, and a `参考文献` list with working PubMed links for every study you cite.
7. If the article is publication-bound, insert WordPress fixed elements before final QA, then run `$medical-ad-compliance` on the full article including TL;DR, author block, CTA, footer, and JSON-LD.

## Voice Rules

- Use first-person `僕`.
- Use `です・ます調`.
- Speak with professional warmth, not textbook distance.
- Explain technical terms immediately in plain Japanese or with a short analogy.
- Use patient-friendly search language in `title`, `H1`, `TL;DR`, `excerpt`, and major `H2` headings. Keep formal technical terms only where they improve precision or match real search intent.
- When a technical term matters for SEO or accuracy, introduce it once in the first half of the article as `平易語（専門語）` or `専門語、つまり平易語`, then use the plain term for most later mentions.
- Avoid raw clinician-facing terms in body copy, such as `介入`, `個別化`, `エビデンス強度`, and `生活機能スコア`. Rewrite them as patient-friendly phrases like `調整`, `その人に合わせること`, `研究の確かさ`, and `日常生活のつらさ`.
- In body text, introduce studies as `2025年の研究では` or `複数の研究をまとめたレビューでは`. Never write researcher surnames like `Uchidaさんたちの研究` or `Smithらの` in body copy — keep names in the reference list only.
- After citing a study's finding, state its limitation in the same passage: e.g. `横断研究が中心で因果関係は断定できません`, `研究の確かさは高くありません`, `人数は限られています`. A finding without a hedge is incomplete.
- Include at least one short anonymous patient consultation example when writing a full article from scratch.
- Keep anonymous episodes to common worries or de-identified intake concerns. Do not describe treatment results, post-treatment changes, before/after comparisons, or testimonial-style efficacy claims.
- Avoid exaggerated guarantees, aggressive sales language, and dense blocks of unexplained jargon.

## Evidence & Citations (critical for automated drafting)

The strongest recent articles all share the same evidence discipline; weak older ones do not. Follow this exactly.

- Cite only studies you can verify. Every study mentioned in the body MUST appear in the `参考文献` list with a real, working PubMed URL (`https://pubmed.ncbi.nlm.nih.gov/<PMID>/`), and the same PMIDs go into the JSON-LD `citation` array.
- Never fabricate a PMID, journal name, year, sample size, or finding. If you cannot confirm a study exists, do not cite it — write the point as general physiology instead, or run `$pubmed-research` first.
- Do not overstate. The body claim must not exceed what the study supports. Prefer `〜の可能性が示されました` / `関連が報告されました` over `〜が証明された` / `必ず〜する`.
- Put the study type and its limitation next to the claim (systematic review / meta-analysis / RCT / cross-sectional / cohort), e.g. `2019年の8研究レビューでは…ただし横断研究が中心で因果関係は断定できません`.

## Safety Red-Flags (required paragraph)

Inside the solution section, add one short paragraph that tells the reader when to see a doctor instead of relying on self-care. Cover the relevant subset of: 安静時・夜間も強い痛み、しびれや力の入りにくさが広がる、発熱や体重減少、転倒・外傷後の痛み、症状が悪化していく。Frame it calmly as `セルフケアより先に医療機関での確認を優先してください`, not as fear-mongering. Make it specific to the article's symptom.

## Structural Rules

- Target roughly 3000 Japanese characters of body text unless the user explicitly wants a different length.
- Title pattern: lead with the main query's exact wording — `〈主クエリの語〉のはなぜ？〈体のしくみ〉をやさしく解説`. Keep daily-scene words (坂道, 立ち上がり, 洗濯…) OUT of the title (use them in H2s and body); never lead the title with category labels like `大人の側弯症`.
- TL;DR (80–120 chars, one sentence) should carry one concrete study figure, e.g. `2020年の21研究メタ解析では…`.
- In the solution section, open by splitting the symptom by moment/situation (例: 座っている間か、離殿の瞬間か、立ち切った後か) so the reader can locate where load concentrates. This "which moment hurts" framing is a signature of the best articles.
- The anonymous episode must be framed as a typical intake worry — add a clause like `これは施術後の変化ではなく、来院時によくある悩みとして紹介しています` so it never reads as a before/after testimonial.
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

## Writing Rhythm (anti-monotony)

- One sentence-level test decides deletions: does the sentence update the situation (body, research, patient, the writer's clinical reasoning) or only the document (「ここからは〜を見ていきます」「この記事では〜をお伝えしました」)? Document-only sentences get deleted; the next section's first sentence should simply start concrete.
- State research limitations as facts about the research (`坂道を調べた研究ではないので、そこまでは言えません`), never as document-usage notes (`記事内では〜という範囲で参考にします`).
- Do not open 3+ consecutive paragraphs with the same `〇〇年の研究では` pattern — reorder by the reader's question, vary openings (scene / question / what is still unknown), and land each study on the concrete moment described just before it.
- Avoid runs of 3+ long declarative sentences; insert a short anchor sentence or a patient's quoted phrase.
- Keep tension from the reader's own naive question (`平地は平気なのに、なぜ坂だけつらいのか`) or the writer's clinical reasoning (`僕がまず分けて見るのは〜`). Never from asserting something false to overturn it later, and never from fear.

## Save Path

If the user asks you to save the draft and does not specify a destination, default to `HPブログ記事/投稿前/`.

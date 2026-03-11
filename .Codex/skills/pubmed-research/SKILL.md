---
name: pubmed-research
description: Search, triage, and summarize medical literature from PubMed for repository health content. Use when Codex needs to gather scientific evidence, find PubMed papers, check research support for a health claim, collect systematic reviews or RCTs, translate a Japanese topic into English MeSH search terms, or prepare citation-ready notes for blog posts, LINE columns, and research memos.
---

# PubMed Research

Use primary sources first. Prefer PubMed, PubMed Central, and publisher pages over secondary summaries.

## Load This Resource

- Load `references/evidence-levels.md` when you need to rank study designs or explain why one paper is stronger than another.

## Workflow

1. Translate the user's Japanese topic into English keywords and likely MeSH terms.
2. Build a search that combines condition, intervention or exposure, and outcome. Add study design filters when the user wants stronger evidence.
3. Prefer recent evidence by default, usually the last 5 years, unless the topic needs landmark older papers.
4. Prioritize systematic reviews, meta-analyses, guidelines based on reviews, and RCTs. Use lower-level evidence only when better studies are scarce.
5. Extract citation data, study design, sample or population, key findings, and limitations.
6. Summarize the included papers in Japanese and give a practical note on how each paper could support or weaken the article claim.

## Search Rules

- Use official PubMed URLs or NCBI sources whenever possible.
- If the user asks for the latest evidence, sort or filter by publication date and state the exact publication year.
- Distinguish between study type, evidence strength, and clinical relevance. They are related but not identical.
- If impact factor is requested and a reliable primary source is not accessible, say that it could not be verified instead of guessing.
- Note retractions, major limitations, tiny sample sizes, and conflict-of-interest signals when visible.

## Output Format

For each paper, include:

- Original title
- Journal and publication year
- PMID and DOI when available
- Study design and evidence level
- Short Japanese summary
- One-line note for how the repository could cite or use the finding

If the user requests a literature roundup, add a short synthesis section that explains where the evidence is consistent and where it conflicts.

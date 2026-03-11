---
name: wp-fixed-elements
description: Add the repository's required WordPress fixed elements to a blog draft before posting, including TL;DR, author block, table of contents, disclaimer, LINE CTA, footer, and JSON-LD. Use when Codex is asked to prepare a blog article for WordPress, insert fixed HTML snippets, add front matter tags, or check whether a repository blog draft is ready for `post_to_wp.py`.
---

# WP Fixed Elements

Use this skill only for repository HP blog articles. Edit the article in place and preserve the writer's substantive content.

## Load This Resource

- Load `reference.md` for the canonical HTML snippets and fixed URLs.

## Workflow

1. Read the target markdown file completely.
2. Detect whether fixed elements already exist. If `class="tldr"` or `<nav class="toc">` is present, avoid duplicating those blocks.
3. Insert the fixed blocks in this order: TL;DR, author block, TOC near the top; disclaimer, LINE CTA, footer, and JSON-LD near the end.
4. Convert article `##` headings into anchored `<h2 id="...">` form when needed for the TOC.
5. Preserve `## メタディスクリプション` and `## サジェストキーワード` sections.
6. Add or replace front matter `tags:` with the repository's required tag set.
7. Verify the result is still readable markdown-plus-HTML and that no block was duplicated.

## Generation Rules

- Write TL;DR as 80-120 Japanese characters.
- Include at least one concrete number or measurable detail in TL;DR.
- Build the TOC from actual `##` headings except metadata sections.
- Use Japanese heading text as anchor ids unless the target file already uses a different established pattern.
- Replace a plain-text disclaimer with the canonical HTML disclaimer when present.
- Keep any article-specific references section before the disclaimer block.

## Output Expectations

After editing, report:

- which file was modified
- whether elements were newly inserted or already present
- any sections that need human confirmation, such as an unusual heading structure or missing numbered self-care steps for JSON-LD `HowTo`

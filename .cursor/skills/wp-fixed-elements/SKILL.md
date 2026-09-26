---
name: wp-fixed-elements
description: Add, repair, and validate the repository's required WordPress fixed elements, including TL;DR, author block, TOC, references, disclaimer, LINE CTA, canonical footer, and JSON-LD. Use when preparing an HP blog for WordPress, checking a local draft before `post_to_wp.py`, or safely synchronizing fixed elements in WordPress draft or future posts.
---

# WP Fixed Elements

Use this skill only for repository HP blog articles. Preserve the substantive article and change only required fixed elements.

## Load This Resource

- Load `reference.md` completely for canonical HTML and fixed URLs.
- Load `../../../01_ガイドライン・プロンプト/WordPress投稿・予約投稿運用.md` before posting, scheduling, or modifying WordPress posts.

## Workflow

1. Read the target markdown file completely.
2. Count every fixed element independently. Never infer completeness from only TL;DR or TOC.
3. Insert or repair blocks in this order: TL;DR → author → TOC → body → references when used → disclaimer → LINE invitation → LINE button → canonical footer → JSON-LD.
4. Keep the LINE invitation only before the button. Never put invitation text inside the footer.
5. Copy the footer from `reference.md` exactly. Keep the image centered and place the address block below it.
6. Convert article `##` headings into anchored `<h2 id="...">` when required by the TOC.
7. Preserve metadata sections and add or replace the required front matter `tags:`. Select only relevant values from the fixed whitelist below; never invent, create, or retain any other tag.
8. Run `python3 post_to_wp.py "TARGET" --preflight-only`. Fix every reported error before any WordPress write.
9. Run final style, medical-compliance, and character QA on the complete article after fixed elements are final. Any later fixed-element edit resets this QA gate.

## Generation Rules

### Fixed WordPress Tag Whitelist

Choose only tags that are relevant to the article. Do not attach all tags to every article. The complete allowed set is:

- `股関節痛`
- `名古屋市`
- `フィジカルバランスラボ整体院`
- `整体`
- `名東区`
- `星ヶ丘`
- `千種区`
- `レッドコード整体`
- `坐骨神経痛`
- `肩こり`
- `脊柱側弯症`
- `脊柱管狭窄症`
- `腰椎椎間板ヘルニア`
- `腰痛`
- `五十肩`
- `ぎっくり腰`
- `ぶら下がり整体`

Reject publication when `tags:` is missing, empty, duplicated, or contains a value outside this list. Never create a new WordPress tag. Treat `wp_fixed_elements.ALLOWED_WP_TAGS` as the executable source of truth.

- Write TL;DR as 80-120 Japanese characters.
- Include at least one concrete number or measurable detail in TL;DR.
- Build the TOC from actual `##` headings except metadata sections.
- Use Japanese heading text as anchor ids unless the target file already uses a different established pattern.
- Replace a plain-text disclaimer with the canonical HTML disclaimer when present.
- Keep any article-specific references section before the disclaimer block.
- Keep exactly one LINE button, footer, and JSON-LD block.
- Treat `wp_fixed_elements.py` as the executable source of truth for preflight and canonical-footer validation.

## WordPress Safety

- Create a draft with `post_to_wp.py`; do not directly schedule with a future `date` and `--publish`.
- Confirm that every selected tag resolves to an existing WordPress tag and that the draft response contains the exact requested tag IDs. Stop on any mismatch.
- Schedule only through `format_wp_drafts.py` plan → approve → schedule.
- Treat the publication plan's `tags` as locked QA state. Recheck the exact non-empty allowed tag set during approval, immediately before scheduling, and after scheduling.
- If any post-schedule check fails, restore every attempted post to its complete before-schedule draft state, including tags, and verify the rollback. Never leave an unverified `future` post.
- Export the WordPress edit-context HTML with `format_wp_drafts.py export` and use that file for final QA before approval.
- For WordPress fixed-element repair, run `fixed-elements` without `--apply`, review the report, apply, then rerun until `PENDING=0` and `errors=[]`.
- Prefer `--ids`; use `--all` only when every post in the selected status is intentionally in scope.
- Never use `post_to_wp.py --update-post-id` on future or published posts.

## Output Expectations

After editing, report:

- which file was modified
- which elements were inserted, repaired, or already canonical
- the preflight result
- that the full article, including fixed elements, still needs final style/compliance/character QA before posting
- any sections that need human confirmation, such as an unusual heading structure or missing numbered self-care steps for JSON-LD `HowTo`

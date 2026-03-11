---
name: line-column-writer
description: Write short health columns for a clinic or seitai practice's LINE official account in the established repository voice. Use when Codex is asked to create a LINEコラム, short seasonal health tip, weekly broadcast text, reader-friendly prevention advice, or a light educational post for patients and followers. This skill fits outputs around 15-25 lines, warm Japanese copy, weekly scheduling, and repository save paths under `LINEコラム/YYYY/`.
---

# Line Column Writer

Use this skill for weekly LINE content that feels human, warm, and easy to read on a phone. Keep the delivery lightweight; this is not a full blog article.

## Repository Context

- Read [年間スケジュール.md](/Users/ryukouokumura/マイドライブ（okumura@physical-balance-lab.net）/PBL情報発信/01_ガイドライン・プロンプト/年間スケジュール.md) when the date matters.
- Review the nearest existing columns in the same month or season to avoid repetition.

## Workflow

1. Fix the delivery date first. If the user gives only a theme, infer the likely season from the requested publication date or current schedule.
2. Pick one concrete reader problem. Do not solve three problems in one column.
3. Draft in five beats: seasonal hook, problem empathy, simple professional insight, one or two practical actions, encouraging close.
4. Keep paragraphs short for mobile reading and avoid mechanical section headers.
5. If asked to save, use `LINEコラム/YYYY/YYYY-MM-DD_【タイトル】.md`.

## Style Rules

- Use `です・ます調`.
- Keep the tone warm, encouraging, and slightly lively.
- Use few emojis. Two or three per column is enough.
- End with `(^^)/`.
- Avoid overtly AI-like framing such as `【1】`, `【ポイント】`, or rigid mini-headings.
- Avoid medical jargon. If a technical term is unavoidable, explain it immediately in plain Japanese.
- Avoid fear-based persuasion and guaranteed outcomes.

## Structural Targets

- Target 15-25 lines.
- Keep most lines to a phone-friendly visual width.
- Prefer one specific action with a number, duration, or frequency, such as `コップ1杯`, `5回`, or `1時間に1回`.
- Add a short personal touch only when it improves warmth and credibility.

## Output

When drafting from scratch, provide:

1. A title in the format `【タイトル】`
2. The column body
3. The suggested save path if the user wants the file written

If the user asks for review instead of drafting, rewrite only the lines that break these rules.

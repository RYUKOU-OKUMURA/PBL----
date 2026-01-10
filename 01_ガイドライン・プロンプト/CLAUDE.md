# CLAUDE.md / CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.  
このファイルは、このリポジトリでコードを扱う際にClaude Code (claude.ai/code) へのガイダンスを提供します。

## Repository Overview / リポジトリ概要

This directory contains LINE column articles written by Okumura, a physical therapist and clinic director. The columns are health-focused articles distributed via LINE to patients and followers, covering topics like posture, seasonal health concerns, and preventive care.  
このディレクトリには、理学療法士・院長の奥村によって書かれたLINEコラム記事が含まれています。これらのコラムは患者やフォロワーにLINEで配信される健康に焦点を当てた記事で、姿勢、季節の健康問題、予防ケアなどのトピックを扱っています。

## Content Structure / コンテンツ構造

The repository contains:  
リポジトリには以下が含まれています：
- Multiple markdown files with LINE column articles (【title】.md format)  
  LINEコラム記事の複数のmarkdownファイル（【タイトル】.md形式）
- `okumura_line_column_prompt.yaml` - A comprehensive prompt guide for writing new columns in Okumura's style  
  `okumura_line_column_prompt.yaml` - 奥村のスタイルで新しいコラムを書くための包括的なプロンプトガイド

## Key Writing Guidelines / 主要な執筆ガイドライン

When creating or editing LINE columns:  
LINEコラムを作成または編集する際：

1. **Always maintain Okumura's writing style**:  
   **常に奥村の文体を維持する**：
   - Warm, approachable tone using です・ます調  
     です・ます調を使用した温かく親しみやすい文調
   - Strategic use of exclamation marks (！) for emphasis  
     強調のための感嘆符（！）の戦略的使用
   - Consistent use of emoticons: 💦 (concern), 🌸 (positivity), (^^)/ (closing)  
     絵文字の一貫した使用：💦（心配）、🌸（ポジティブ）、(^^)/（締め）
   - Personal touches including family anecdotes  
     家族のエピソードを含む個人的なタッチ

2. **Follow the established structure**:  
   **確立された構造に従う**：
   - Opening: Seasonal/weather hook (1-2 sentences)  
     導入：季節・天候のフック（1-2文）
   - Problem identification: Relatable health concern (2-3 paragraphs)  
     問題の特定：共感できる健康問題（2-3段落）
   - Professional insight: Simple explanations without jargon (1-2 paragraphs)  
     専門的洞察：専門用語を使わないシンプルな説明（1-2段落）
   - Practical solution: Specific, actionable advice (1-2 paragraphs)  
     実践的解決策：具体的で実行可能なアドバイス（1-2段落）
   - Closing: Encouraging message ending with (^^)/  
     締め：(^^)/で終わる励ましのメッセージ

3. **Content guidelines**:  
   **コンテンツガイドライン**：
   - Length: 15-25 lines for mobile readability  
     長さ：モバイル読みやすさのため15-25行
   - Focus on preventive care and "90歳でも自分の脚で歩ける体" (walking at 90)  
     予防ケアと「90歳でも自分の脚で歩ける体」（90歳での歩行）に焦点
   - Include specific, memorable details (5kg for head weight, コップ1杯 for water)  
     具体的で記憶に残る詳細を含める（頭の重さに5kg、水にコップ1杯）
   - Avoid medical jargon and overly technical explanations  
     医学専門用語や過度に技術的な説明を避ける

## Working with Columns / コラムでの作業

When asked to:
以下を求められた場合：
- **Analyze columns**: Focus on structure, tone, recurring themes, and author's voice
  **コラム分析**：構造、文調、繰り返されるテーマ、著者の声に焦点を当てる
- **Create new columns**: Use `okumura_line_column_prompt.yaml` as reference
  **新しいコラム作成**：`okumura_line_column_prompt.yaml`を参考にする
- **Edit columns**: Maintain consistency with existing style and formatting
  **コラム編集**：既存のスタイルと書式との一貫性を保つ

### File Creation and Naming / ファイル作成と命名規則

When creating new LINE columns:
新しいLINEコラムを作成する際：

1. **Always create a new file** - Never overwrite existing columns
   **常に新しいファイルを作成** - 既存のコラムを上書きしない

2. **Use date-prefixed filenames** in the format: `YYYY-MM-DD_【title】.md`
   **日付プレフィックス付きファイル名**を使用：`YYYY-MM-DD_【タイトル】.md`
   - Example: `2025-10-22_【運動会の翌週こそ要注意！遅れてくる筋肉痛のケア】.md`
   - 例：`2025-10-22_【運動会の翌週こそ要注意！遅れてくる筋肉痛のケア】.md`

3. **Publication schedule** - Columns are typically published on Wednesdays
   **公開スケジュール** - コラムは通常水曜日に公開される
   - When dating new columns, use the next available Wednesday
     新しいコラムに日付を付ける際は、次に利用可能な水曜日を使用
   - Review existing files in `投稿済み/` folder to determine the latest publication date
     最新の公開日を確認するには、`投稿済み/`フォルダ内の既存ファイルを確認

4. **Avoid dangerous characters in filenames** - These characters cause shell issues:
   **ファイル名に危険な文字を使わない** - これらの文字はシェルで問題を引き起こします:
   - `"` (double quote / ダブルクォート)
   - `'` (single quote / シングルクォート)
   - `` ` `` (backtick / バッククォート)
   - `\` (backslash / バックスラッシュ)
   - `$` (dollar sign / ドル記号)
   - `!` (exclamation mark / エクスクラメーション)

   If a filename contains these characters, scripts like `post_to_wp.py` may fail.
   これらの文字がファイル名に含まれていると、`post_to_wp.py` などのスクリプトが失敗する可能性があります。

## Avoiding Repetition / 繰り返しの回避

When creating multiple columns, especially consecutive ones (e.g., year-end → new year):
複数のコラムを作成する際、特に連続するもの（例：年末→新年）：

1. **Avoid content overlap** - Check previous columns to ensure different angles and content
   **内容の重複を避ける** - 前回のコラムを確認し、異なる角度と内容を確保する

2. **Vary the format** - Don't always use "3 points" format; sometimes focus on a single theme
   **形式を変える** - 常に「3つのポイント」形式を使わず、1つのテーマに絞ることもある

3. **Avoid repeating phrases** - Watch for overused phrases like「たったこれだけ？」「痛みが取れた」
   **フレーズの繰り返しを避ける** -「たったこれだけ？」「痛みが取れた」などの使いすぎに注意

4. **Leverage milestones** - Use anniversaries (12周年 etc.) and seasonal events for unique content
   **節目を活かす** - 周年記念（12周年など）や季節のイベントを活かしたユニークな内容に

5. **Core message rotation** - Distribute these throughout the year:
   **コアメッセージのローテーション** - 年間を通じてこれらを配分：
   - 水分補給 (Hydration) - 2-3 times per month / 月2-3回
   - ストレッチ (Stretching) - 2 times per month / 月2回
   - 理念「90歳でも自分の脚で歩ける体」(Philosophy) - 6 times per year / 年6回

## Important Notes / 重要な注意事項

- This is not a code repository but a content repository for health-related articles
  これはコードリポジトリではなく、健康関連記事のコンテンツリポジトリです
- All content should maintain the professional yet personal voice established by Okumura
  すべてのコンテンツは奥村によって確立された専門的でありながら個人的な声を維持すべきです
- When creating new content, prioritize readability on mobile devices (LINE app)
  新しいコンテンツを作成する際は、モバイルデバイス（LINEアプリ）での読みやすさを優先してください
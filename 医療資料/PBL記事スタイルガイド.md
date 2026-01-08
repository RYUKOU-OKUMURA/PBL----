poml_version = "1.0"
guide_id = "pbl_article_style"
lang = "ja"

[meta]
name = "PBL記事スタイルガイド"
owner = "PBL（フィジカルバランスラボ整体院）"
purpose = "誰が書いても同じ品質で、PBLらしい語り口のブログを再現する"
audience = ["来院検討者", "一般読者", "ライト層の臨床家"]

[voice]
person = "僕"
politeness = "です・ます調"
tone = ["専門性", "やさしさ", "励まし"]
rhetorical_questions = true
direct_address = true
story_mini_episode = true  # 匿名の短いエピソードを各記事で1つ以上

[readability]
mobile_first = true
paragraph_sentences = "2-4"
heading_levels = ["##", "###"]
bold_usage = "重要語の最小限強調"
color_usage = "媒体仕様に依存。乱用しない"

[structure]
flow = ["Problem", "Agitation", "Solution", "NarrowDown", "Action"]
word_target = 3000
narrative_ratio_min = 0.7  # 本文の7割以上はプレーンな段落で書く
heading_labels_included = false  # 見出しに（Problem）等のラベルは記載しない

[bullets]
allowed_sections = ["NarrowDown", "Checklists", "References", "Q&A"]
max_per_section = 5
nested = false
numbers_preferred = true  # 箇条書きは可能なら番号付き
avoid_in = ["Problem", "Agitation", "Solution", "Action"]

[sections.Problem]
goals = ["読者の悩みの代弁", "安心の提供"]
requirements = ["一人称『僕』で語りかける", "匿名の短いエピソードを1つ"]
min_paragraphs = 2
forbid_bullets = true

[sections.Agitation]
goals = ["なぜ起こるかを解像度高く説明", "放置リスクを穏やかに明示"]
requirements = ["専門用語→直後に平易説明", "比喩を1つ以上"]
min_paragraphs = 2
forbid_bullets = true

[sections.Solution]
goals = ["評価→介入→再評価の流れを具体化", "読者が安全に想像できる描写"]
requirements = ["痛みゼロ原則の明記", "段階的進行の説明", "徒手×運動の橋渡し"]
min_paragraphs = 2
forbid_bullets = true

[sections.NarrowDown]
goals = ["今日からできる3項目", "安全・再現性・短時間"]
requirements = ["目安（回数/時間）", "痛みが出たら中止"]
bullets_only = true
items = 3

[sections.Action]
goals = ["要点の再掲", "前向きな一言", "次回や予約への自然な導線"]
requirements = ["誇大表現の禁止", "一般情報である旨を再掲しても良い"]
min_paragraphs = 1
forbid_bullets = true

[terminology]
explain_immediately = true  # 専門語は直後に平易化
examples = [
  { term = "神経筋制御", plain = "筋肉と神経のチームワーク" },
  { term = "ウィークリンク", plain = "動作の鎖の中の弱い環" },
  { term = "免荷", plain = "体重の一部を預けて負担を軽くする工夫" },
  { term = "不安定性", plain = "小さな揺れで微調整を引き出す刺激" }
]

[safety]
disclaimer_required = true
disclaimer_text = "本記事は一般情報であり、個別の診断・治療を提供するものではありません。痛みや違和感が出たら中止し、必要に応じて専門家へご相談ください。"
pain_zero_principle = true
contraindications_note = true
numbers_language = "『約』『目安』を添える"
prohibited = ["誇大表現", "断定的な効果保証", "他者誹謗"]

[seo]
title_rule = "構成案の固定タイトルを優先。必要時のみ最小修正"
keywords_guidance = "院名/サービス名（レッドコード整体）と症状語を自然に含める"
slug_policy = "日本語タイトル.md。公開時にCMS仕様へ対応"

[templates.series_article]
name = "シリーズ記事（PASONA＋ナラティブ）"
body = """
## はじめに
読者の悩みを代弁し、匿名の短いエピソードを1つ入れる。僕一人称、です・ます調。

## なぜ起こるのか
専門語→直後に平易説明。比喩を使い、放置リスクは脅かさず淡々と。

## 解決の方向性
評価→介入→再評価の流れを文章で具体化。痛みゼロ原則と段階進行。

## 今日からできること
1. 〜（目安：回数/時間）
2. 〜（痛みが出たら中止）
3. 〜（安全で再現性が高い）

## まとめと次の一歩
要点をやさしく再掲し、前向きな一言で締める。必要なら相談/予約への導線を自然に提示。
"""

[templates.single_article]
name = "単発記事（研究レビュー/HowTo/症例）"
body = """
（研究レビュー）
## 背景
## 研究の要点（対象/手法/主要結果）
## 何が言えるか（示唆）
## 限界と注意点（一般化の範囲）
## 実践への翻訳（読者が取れる一歩）

（How To）
## 注意事項（安全・禁忌）
## 前提（対象・目的）
## 手順（番号付きで具体的に）
## 頻度・回数・所要時間の目安
## よくある失敗と対策

（症例ストーリー）
## 来院背景と主訴（匿名）
## 評価（所見と仮説）
## 介入（意図と実施）
## 結果（変化と解釈）
## 学び（一般化できるポイント）
"""

[references]
citation_policy = "ファイル名や論文名を末尾『出典』欄に明記"
placement = "本文末尾"

[checklist]
items = [
  "一人称が『僕』で統一されている",
  "です・ます調で語尾の揺れがない",
  "専門語の直後に平易な説明がある",
  "ナラティブ比率が0.7以上（箇条書きは主にNarrowDownのみ）",
  "評価→介入→再評価の流れが文章で説明されている",
  "見出し（##/###）と段落長がスマホ向けに最適化",
  "『今日からできること』が3項目・安全・再現性高い",
  "誇大表現の排除と安全ディスクレーマーの明記",
  "見出しに（Problem/Agitation等）のラベル表記がない",
  "保存先・ファイル名が構成案に一致（NN_固定タイトル.md形式）",
  "OPSガイドの進捗チェック更新"
]

[examples]
term_plain_pairs = [
  "神経筋制御=筋肉と神経のチームワーク",
  "ウィークリンク=動作の鎖の中の弱い環",
  "免荷=体重の一部を預けて負担を軽くする",
  "不安定性=小さな揺れで微調整を引き出す"
]

[ops]
save_format = "Markdown（UTF-8, LF）"
series_dir_rule = "構成案で指定されたディレクトリ"
file_naming = "NN_構成案の固定タイトル.md（NNは2桁の連番: 01, 02, ...）"
numbering_width = 2
numbering_start = 1
progress_update = "agent/ブログ記事執筆ガイドライン.md のチェックリストを更新"

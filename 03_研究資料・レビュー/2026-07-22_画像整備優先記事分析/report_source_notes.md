# レポート作成ノート

## レポートの目的

- 判断: どの公開記事から記事別アイキャッチと本文画像を整備するか
- 読者: 院のコンテンツ運用担当者（product stakeholders）
- 主期間: 2025-07-20〜2026-07-19
- 補助期間: 2026-04-21〜2026-07-19
- 主指標: GA4 `screenPageViews`
- 補助指標: Search Consoleのページ別クリック・表示回数、GA4直近90日のPVペース
- 公開状態と画像実装の正本: WordPress REST API

## Executive Report必須構造との対応

1. Title: `アクセス上位記事の画像整備候補`
2. Executive Summary: 結論、現状、最低作業量、最初の実施単位
3. Key findings with visual evidence: 上位20記事のPVランキングチャートと全20記事の明細表
4. Recommended next steps: 5記事ずつ4回に分ける実施案
5. Further questions: 既存写真を残す範囲、本文3枚の定義、アイキャッチ比率
6. Caveats and assumptions: 共通確定日、URL結合率、GSCの欠測、機械的画像判定

## チャート契約

- 分析質問: 12か月のアクセスがどの記事へ集中しているか
- 一文の結論: 上位20記事が公開記事PVの77.9%を占め、上位から画像整備する効果が大きい
- family / type: Comparison & Ranking / `horizontalBar`
- 行数: 上位20記事の20行
- x: 記事ラベル、y: 12か月PV
- 補助フィールド: 90日PV、GSCクリック、本文固有画像数、本文追加目安、推奨作業
- palette: single-root preferred（単系列。凡例なし）
- 表示面: Data Analytics MCP report、全幅
- フォールバック: 長い記事名の正確な照合は直後の明細表で行う

## データ品質

- GA4ページ行: 411行。APIの`rowCount`と返却行数が一致
- Search Consoleページ行: 140行、クエリ×ページ行: 1,496行。25,000行ページングの安全上限未到達
- WordPress公開記事: 218件。ID・URLとも一意
- GA4に結合した公開記事: 194件（記事数88.99%）。数値投稿URLのPVでは96.86%をカバー
- 上位20件はすべて現在公開中で、投稿IDの重複なし
- 90日PVは12か月PV以下、90日GSCクリックは12か月クリック以下であることを検証
- 負の指標値なし

## 画像監査の定義

- 共通アイキャッチ: メディアID 314（217記事で再利用）
- 本文固定画像として除外: 361（著者）、487（旧共通施術写真）、629（フッター）
- `src`もメディアIDもない空の`img`タグは画像数に含めない
- 本文の追加目安は「記事固有画像を合計3枚にする」前提で計算
- 既存の写真・装具画像・図解は内容価値を個別目視してから維持／置換を決める

## 可視化の省略

- 時系列チャートは今回の主目的が順位選定であるため省略。12か月と90日の比較は明細表へ残した。
- GSCクリックの別チャートは、アクセス順位の主指標と誤解されるのを避けるため省略。検索流入は明細表と主要クエリ列に残した。

## レポートQA

- Data Analytics artifact validator: `ok=true`
- report surface: `report`
- dataset count: 2、source count: 2、snapshot status: `ready`
- MCP artifact renderer: `ok=true`
- 先頭ブロックはレポート名と一致する`#`見出し
- 2番目のブロックは`## Executive Summary`
- 横棒グラフは単系列で色凡例を付けず、長い記事名は短縮ラベルとツールチップで補完
- 正確な記事名・数値・推奨作業は直後の全20件テーブルで確認可能

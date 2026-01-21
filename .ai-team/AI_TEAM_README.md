# AIチーム環境 (pbl-info)

このプロジェクトにはマルチエージェントAIチーム環境が含まれています。

## クイックスタート

```bash
# 1. 環境セットアップ（tmuxセッション作成）
.ai-team/setup.sh

# 2. Claude Code起動
.ai-team/launch-agents.sh
# 各画面でブラウザ認証を行ってください

# 3. PRESIDENTに指示
.ai-team/agent-send.sh president "あなたはpresidentです。指示書に従ってプロジェクトを進めてください"
```

## セッション操作

```bash
# セッション一覧
tmux list-sessions

# PRESIDENTセッションにアタッチ
tmux attach-session -t pbl-info-president
# デタッチ: Ctrl+b, d

# エージェントセッションにアタッチ
tmux attach-session -t pbl-info-agents
# デタッチ: Ctrl+b, d
```

## エージェント一覧

| エージェント | 役割 |
|------------|------|
| president | プロジェクト統括責任者 |
| boss1 | チームリーダー |
| worker1 | 実行担当者A |
| worker2 | 実行担当者B |
| worker3 | 実行担当者C |

## スクリプト

| スクリプト | 説明 |
|-----------|------|
| `.ai-team/setup.sh` | tmuxセッション作成 |
| `.ai-team/launch-agents.sh` | Claude Code一括起動 |
| `.ai-team/agent-send.sh` | エージェントへの指示送信 |
| `.ai-team/project-status.sh` | 進捗確認 |

詳細な指示書: `.ai-team/instructions/`

#!/bin/bash

# 🚀 AIエージェント一括起動 - プロジェクト: pbl-info

SESSION_PREFIX="pbl-info"

echo "🤖 Claude Codeを一括起動します (pbl-info)"
echo ""
echo "⚠️  注意: 各画面でブラウザ認証が必要です"
echo "      認証完了後、Enterを押して次へ進んでください"
echo ""
read -p "続行しますか？ (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "キャンセルしました"
    exit 1
fi

# president 起動
echo ""
echo "👑 PRESIDENT 起動中..."
tmux send-keys -t "${SESSION_PREFIX}-president" "claude --dangerously-skip-permissions" C-m
echo "   → 認証してください (tmux attach-session -t ${SESSION_PREFIX}-president)"

# agents 起動
echo "🤖 エージェント起動中..."
echo "   boss1 (Codex)..."
tmux send-keys -t "${SESSION_PREFIX}-agents:0.0" "codex -m gpt-5.2-codex-high" C-m
echo "   worker1 (Claude)..."
tmux send-keys -t "${SESSION_PREFIX}-agents:0.1" "claude --dangerously-skip-permissions" C-m
echo "   worker2 (Claude)..."
tmux send-keys -t "${SESSION_PREFIX}-agents:0.2" "claude --dangerously-skip-permissions" C-m
echo "   worker3 (Claude)..."
tmux send-keys -t "${SESSION_PREFIX}-agents:0.3" "claude --dangerously-skip-permissions" C-m

echo ""
echo "✅ 起動コマンドを送信しました"
echo ""
echo "📋 各セッションにアタッチして認証してください:"
echo "   tmux attach-session -t ${SESSION_PREFIX}-president"
echo "   tmux attach-session -t ${SESSION_PREFIX}-agents"
echo ""
echo "💡 認証後、以下で指示を送信できます:"
echo "   .ai-team/agent-send.sh president \"プロジェクトを開始してください\""

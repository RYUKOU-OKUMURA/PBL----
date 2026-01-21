#!/bin/bash

# 📊 プロジェクト進捗確認 - プロジェクト: pbl-info

echo "📊 プロジェクト進捗: pbl-info"
echo "================================"
echo ""

# セッション確認
if tmux has-session -t "pbl-info-agents" 2>/dev/null; then
    echo "✅ エージェントセッション: 実行中"
else
    echo "❌ エージェントセッション: 停止中"
fi

if tmux has-session -t "pbl-info-president" 2>/dev/null; then
    echo "✅ プレジデントセッション: 実行中"
else
    echo "❌ プレジデントセッション: 停止中"
fi

echo ""
echo "📋 Worker完了状態:"
echo "-------------------"

for i in 1 2 3; do
    if [[ -f .ai-team/tmp/worker${i}_done.txt ]]; then
        echo "  Worker$i: ✅ 完了"
    else
        echo "  Worker$i: 🔄 作業中"
    fi
done

echo ""
echo "💡 操作:"
echo "   .ai-team/setup.sh      - 環境セットアップ"
echo "   .ai-team/launch-agents.sh - Claude起動"
echo "   .ai-team/agent-send.sh [agent] [msg] - 指示送信"

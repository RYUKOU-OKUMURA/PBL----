#!/bin/bash

# 🚀 Multi-Agent 環境構築 - プロジェクト: pbl-info
# このスクリプトは .ai-team/setup.sh により生成されました

set -e

GREEN='\033[1;32m'
BLUE='\033[1;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

SESSION_PREFIX="pbl-info"

log_info "🧹 既存セッションのクリーンアップ..."
tmux kill-session -t "${SESSION_PREFIX}-agents" 2>/dev/null || true
tmux kill-session -t "${SESSION_PREFIX}-president" 2>/dev/null || true

# 完了ファイルクリア
mkdir -p .ai-team/tmp
rm -f .ai-team/tmp/worker*_done.txt 2>/dev/null || true

log_success "✅ クリーンアップ完了"
echo ""

# agentsセッション作成（4ペイン）
log_info "📺 エージェントセッション作成中..."

tmux new-session -d -s "${SESSION_PREFIX}-agents" -n "agents"
tmux split-window -h -t "${SESSION_PREFIX}-agents:0"
tmux select-pane -t "${SESSION_PREFIX}-agents:0.0"
tmux split-window -v
tmux select-pane -t "${SESSION_PREFIX}-agents:0.2"
tmux split-window -v

# ペイン設定
PANE_TITLES=("boss1" "worker1" "worker2" "worker3")
PANE_COLORS=("31" "34" "34" "34")  # 31=赤, 34=青

for i in {0..3}; do
    tmux select-pane -t "${SESSION_PREFIX}-agents:0.$i" -T "${PANE_TITLES[$i]}"
    tmux send-keys -t "${SESSION_PREFIX}-agents:0.$i" "cd /Users/ryukouokumura/Desktop/boss-workspace/Claude-Code-Communication" C-m
    tmux send-keys -t "${SESSION_PREFIX}-agents:0.$i" "export PS1='(\[\033[1;${PANE_COLORS[$i]}m\]${PANE_TITLES[$i]}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]$ '" C-m
    tmux send-keys -t "${SESSION_PREFIX}-agents:0.$i" "echo '=== ${PANE_TITLES[$i]} ===' && clear" C-m
done

log_success "✅ エージェントセッション作成完了"
echo ""

# presidentセッション作成
log_info "👑 プレジデントセッション作成中..."

tmux new-session -d -s "${SESSION_PREFIX}-president"
tmux send-keys -t "${SESSION_PREFIX}-president" "cd /Users/ryukouokumura/Desktop/boss-workspace/Claude-Code-Communication" C-m
tmux send-keys -t "${SESSION_PREFIX}-president" "export PS1='(\[\033[1;35m\]PRESIDENT\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]$ '" C-m
tmux send-keys -t "${SESSION_PREFIX}-president" "echo '=== PRESIDENT ===' && clear" C-m

log_success "✅ プレジデントセッション作成完了"
echo ""

log_success "🎉 セットアップ完了！"
echo ""
echo "📋 次のステップ:"
echo "  1. セッション確認:"
echo "     tmux list-sessions"
echo ""
echo "  2. Claude Code起動:"
echo "     .ai-team/launch-agents.sh"
echo ""
echo "  3. 指示送信:"
echo "     .ai-team/agent-send.sh president \"プロジェクトを開始してください\""

#!/bin/bash

# 🚀 Agent間メッセージ送信 - プロジェクト: pbl-info

SESSION_PREFIX="pbl-info"

get_agent_target() {
    case "$1" in
        "president") echo "${SESSION_PREFIX}-president" ;;
        "boss1") echo "${SESSION_PREFIX}-agents:0.0" ;;
        "worker1") echo "${SESSION_PREFIX}-agents:0.1" ;;
        "worker2") echo "${SESSION_PREFIX}-agents:0.2" ;;
        "worker3") echo "${SESSION_PREFIX}-agents:0.3" ;;
        *) echo "" ;;
    esac
}

show_usage() {
    cat << EOF
🤖 Agent間メッセージ送信 (pbl-info)

使用方法:
  $0 [エージェント名] [メッセージ]
  $0 --list

利用可能エージェント:
  president - プロジェクト統括責任者
  boss1     - チームリーダー
  worker1   - 実行担当者A
  worker2   - 実行担当者B
  worker3   - 実行担当者C

使用例:
  $0 president "プロジェクトを開始してください"
  $0 boss1 "新しいタスクを割り当てて"
  $0 worker1 "コンポーネントを実装して"
EOF
}

show_agents() {
    echo "📋 利用可能なエージェント (pbl-info):"
    echo "================================"
    echo "  president → ${SESSION_PREFIX}-president    (プロジェクト統括)"
    echo "  boss1     → ${SESSION_PREFIX}-agents:0.0  (チームリーダー)"
    echo "  worker1   → ${SESSION_PREFIX}-agents:0.1  (実行担当A)"
    echo "  worker2   → ${SESSION_PREFIX}-agents:0.2  (実行担当B)"
    echo "  worker3   → ${SESSION_PREFIX}-agents:0.3  (実行担当C)"
}

log_send() {
    local agent="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    mkdir -p .ai-team/logs
    echo "[$timestamp] $agent: SENT - \"$message\"" >> .ai-team/logs/send_log.txt
}

send_message() {
    local target="$1"
    local message="$2"
    echo "📤 送信中: $target ← '$message'"
    tmux send-keys -t "$target" C-c
    sleep 0.3
    tmux send-keys -t "$target" "$message"
    sleep 0.1
    tmux send-keys -t "$target" C-m
    sleep 0.5
}

check_target() {
    local target="$1"
    local session_name="${target%%:*}"
    if ! tmux has-session -t "$session_name" 2>/dev/null; then
        echo "❌ セッション '$session_name' が見つかりません"
        echo "   先に .ai-team/setup.sh を実行してください"
        return 1
    fi
    return 0
}

main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 1
    fi

    if [[ "$1" == "--list" ]]; then
        show_agents
        exit 0
    fi

    if [[ $# -lt 2 ]]; then
        show_usage
        exit 1
    fi

    local agent_name="$1"
    local message="$2"
    local target
    target=$(get_agent_target "$agent_name")

    if [[ -z "$target" ]]; then
        echo "❌ エラー: 不明なエージェント '$agent_name'"
        show_agents
        exit 1
    fi

    if ! check_target "$target"; then
        exit 1
    fi

    send_message "$target" "$message"
    log_send "$agent_name" "$message"
    echo "✅ 送信完了: $agent_name に '$message'"
}

main "$@"

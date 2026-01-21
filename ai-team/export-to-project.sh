#!/bin/bash

# 🚀 Multi-Agent System プロジェクトへのエクスポート
# 使い方: ./export-to-project.sh /path/to/target-directory [project-name]

set -e

# 色付き出力
GREEN='\033[1;32m'
BLUE='\033[1;34m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

show_usage() {
    cat << EOF
🚀 Multi-Agent System プロジェクトへのエクスポート

使用方法:
  $0 <ターゲットディレクトリ> [プロジェクト名]

引数:
  ターゲットディレクトリ  エージェントシステムを導入するプロジェクトのパス
  プロジェクト名        (省略可) tmuxセッション名。省略時はディレクトリ名

使用例:
  $0 ~/projects/my-blog
  $0 ~/projects/web-dev my-web-team

EOF
}

# 引数チェック
if [[ $# -eq 0 ]]; then
    show_usage
    exit 1
fi

TARGET_DIR="$1"
PROJECT_NAME="${2:-$(basename "$TARGET_DIR")}"

# 現在のディレクトリ（このスクリプトの場所）
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log_info "プロジェクトへのエクスポートを開始します..."
echo ""
echo "  ターゲット: $TARGET_DIR"
echo "  プロジェクト名: $PROJECT_NAME"
echo ""

# ターゲットディレクトリの存在確認
if [[ ! -d "$TARGET_DIR" ]]; then
    log_error "ターゲットディレクトリが存在しません: $TARGET_DIR"
    exit 1
fi

# コピーするファイル・ディレクトリのリスト
COPY_ITEMS=(
    "instructions"
    "CLAUDE.md"
    ".gitignore"
)

# .ai-team ディレクトリを作成（AIチーム用ファイルの格納先）
AI_TEAM_DIR="$TARGET_DIR/.ai-team"

log_info "ディレクトリ作成: $AI_TEAM_DIR"
mkdir -p "$AI_TEAM_DIR"
mkdir -p "$AI_TEAM_DIR/logs"
mkdir -p "$AI_TEAM_DIR/tmp"

# ファイルコピー
log_info "ファイルをコピー中..."
for item in "${COPY_ITEMS[@]}"; do
    if [[ -e "$SOURCE_DIR/$item" ]]; then
        cp -r "$SOURCE_DIR/$item" "$AI_TEAM_DIR/"
        log_success "  ✓ $item"
    else
        log_warn "  × $item (存在しません)"
    fi
done

# スクリプト生成（プロジェクト名でカスタマイズ）
log_info "プロジェクト用スクリプトを生成中..."

# setup.sh の生成
cat > "$AI_TEAM_DIR/setup.sh" << SETUP_SCRIPT
#!/bin/bash

# 🚀 Multi-Agent 環境構築 - プロジェクト: $PROJECT_NAME
# このスクリプトは .ai-team/setup.sh により生成されました

set -e

GREEN='\033[1;32m'
BLUE='\033[1;34m'
NC='\033[0m'

log_info() { echo -e "\${BLUE}[INFO]\${NC} \$1"; }
log_success() { echo -e "\${GREEN}[SUCCESS]\${NC} \$1"; }

SESSION_PREFIX="${PROJECT_NAME}"

log_info "🧹 既存セッションのクリーンアップ..."
tmux kill-session -t "\${SESSION_PREFIX}-agents" 2>/dev/null || true
tmux kill-session -t "\${SESSION_PREFIX}-president" 2>/dev/null || true

# 完了ファイルクリア
mkdir -p .ai-team/tmp
rm -f .ai-team/tmp/worker*_done.txt 2>/dev/null || true

log_success "✅ クリーンアップ完了"
echo ""

# agentsセッション作成（4ペイン）
log_info "📺 エージェントセッション作成中..."

tmux new-session -d -s "\${SESSION_PREFIX}-agents" -n "agents"
tmux split-window -h -t "\${SESSION_PREFIX}-agents:0"
tmux select-pane -t "\${SESSION_PREFIX}-agents:0.0"
tmux split-window -v
tmux select-pane -t "\${SESSION_PREFIX}-agents:0.2"
tmux split-window -v

# ペイン設定
PANE_TITLES=("boss1" "worker1" "worker2" "worker3")
PANE_COLORS=("31" "34" "34" "34")  # 31=赤, 34=青

for i in {0..3}; do
    tmux select-pane -t "\${SESSION_PREFIX}-agents:0.\$i" -T "\${PANE_TITLES[\$i]}"
    tmux send-keys -t "\${SESSION_PREFIX}-agents:0.\$i" "cd $(pwd)" C-m
    tmux send-keys -t "\${SESSION_PREFIX}-agents:0.\$i" "export PS1='(\[\033[1;\${PANE_COLORS[\$i]}m\]\${PANE_TITLES[\$i]}\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
    tmux send-keys -t "\${SESSION_PREFIX}-agents:0.\$i" "echo '=== \${PANE_TITLES[\$i]} ===' && clear" C-m
done

log_success "✅ エージェントセッション作成完了"
echo ""

# presidentセッション作成
log_info "👑 プレジデントセッション作成中..."

tmux new-session -d -s "\${SESSION_PREFIX}-president"
tmux send-keys -t "\${SESSION_PREFIX}-president" "cd $(pwd)" C-m
tmux send-keys -t "\${SESSION_PREFIX}-president" "export PS1='(\[\033[1;35m\]PRESIDENT\[\033[0m\]) \[\033[1;32m\]\w\[\033[0m\]\$ '" C-m
tmux send-keys -t "\${SESSION_PREFIX}-president" "echo '=== PRESIDENT ===' && clear" C-m

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
SETUP_SCRIPT

chmod +x "$AI_TEAM_DIR/setup.sh"

# agent-send.sh の生成
cat > "$AI_TEAM_DIR/agent-send.sh" << AGENT_SEND_SCRIPT
#!/bin/bash

# 🚀 Agent間メッセージ送信 - プロジェクト: $PROJECT_NAME

SESSION_PREFIX="${PROJECT_NAME}"

get_agent_target() {
    case "\$1" in
        "president") echo "\${SESSION_PREFIX}-president" ;;
        "boss1") echo "\${SESSION_PREFIX}-agents:0.0" ;;
        "worker1") echo "\${SESSION_PREFIX}-agents:0.1" ;;
        "worker2") echo "\${SESSION_PREFIX}-agents:0.2" ;;
        "worker3") echo "\${SESSION_PREFIX}-agents:0.3" ;;
        *) echo "" ;;
    esac
}

show_usage() {
    cat << EOF
🤖 Agent間メッセージ送信 ($PROJECT_NAME)

使用方法:
  \$0 [エージェント名] [メッセージ]
  \$0 --list

利用可能エージェント:
  president - プロジェクト統括責任者
  boss1     - チームリーダー
  worker1   - 実行担当者A
  worker2   - 実行担当者B
  worker3   - 実行担当者C

使用例:
  \$0 president "プロジェクトを開始してください"
  \$0 boss1 "新しいタスクを割り当てて"
  \$0 worker1 "コンポーネントを実装して"
EOF
}

show_agents() {
    echo "📋 利用可能なエージェント ($PROJECT_NAME):"
    echo "================================"
    echo "  president → \${SESSION_PREFIX}-president    (プロジェクト統括)"
    echo "  boss1     → \${SESSION_PREFIX}-agents:0.0  (チームリーダー)"
    echo "  worker1   → \${SESSION_PREFIX}-agents:0.1  (実行担当A)"
    echo "  worker2   → \${SESSION_PREFIX}-agents:0.2  (実行担当B)"
    echo "  worker3   → \${SESSION_PREFIX}-agents:0.3  (実行担当C)"
}

log_send() {
    local agent="\$1"
    local message="\$2"
    local timestamp=\$(date '+%Y-%m-%d %H:%M:%S')
    mkdir -p .ai-team/logs
    echo "[\$timestamp] \$agent: SENT - \"\$message\"" >> .ai-team/logs/send_log.txt
}

send_message() {
    local target="\$1"
    local message="\$2"
    echo "📤 送信中: \$target ← '\$message'"
    tmux send-keys -t "\$target" C-c
    sleep 0.3
    tmux send-keys -t "\$target" "\$message"
    sleep 0.1
    tmux send-keys -t "\$target" C-m
    sleep 0.5
}

check_target() {
    local target="\$1"
    local session_name="\${target%%:*}"
    if ! tmux has-session -t "\$session_name" 2>/dev/null; then
        echo "❌ セッション '\$session_name' が見つかりません"
        echo "   先に .ai-team/setup.sh を実行してください"
        return 1
    fi
    return 0
}

main() {
    if [[ \$# -eq 0 ]]; then
        show_usage
        exit 1
    fi

    if [[ "\$1" == "--list" ]]; then
        show_agents
        exit 0
    fi

    if [[ \$# -lt 2 ]]; then
        show_usage
        exit 1
    fi

    local agent_name="\$1"
    local message="\$2"
    local target
    target=\$(get_agent_target "\$agent_name")

    if [[ -z "\$target" ]]; then
        echo "❌ エラー: 不明なエージェント '\$agent_name'"
        show_agents
        exit 1
    fi

    if ! check_target "\$target"; then
        exit 1
    fi

    send_message "\$target" "\$message"
    log_send "\$agent_name" "\$message"
    echo "✅ 送信完了: \$agent_name に '\$message'"
}

main "\$@"
AGENT_SEND_SCRIPT

chmod +x "$AI_TEAM_DIR/agent-send.sh"

# launch-agents.sh の生成
cat > "$AI_TEAM_DIR/launch-agents.sh" << LAUNCH_SCRIPT
#!/bin/bash

# 🚀 AIエージェント一括起動 - プロジェクト: $PROJECT_NAME

SESSION_PREFIX="${PROJECT_NAME}"

echo "🤖 Claude Codeを一括起動します ($PROJECT_NAME)"
echo ""
echo "⚠️  注意: 各画面でブラウザ認証が必要です"
echo "      認証完了後、Enterを押して次へ進んでください"
echo ""
read -p "続行しますか？ (y/N) " -n 1 -r
echo
if [[ ! \$REPLY =~ ^[Yy]\$ ]]; then
    echo "キャンセルしました"
    exit 1
fi

# president 起動
echo ""
echo "👑 PRESIDENT 起動中..."
tmux send-keys -t "\${SESSION_PREFIX}-president" "claude --dangerously-skip-permissions" C-m
echo "   → 認証してください (tmux attach-session -t \${SESSION_PREFIX}-president)"

# agents 起動
for i in {0..3}; do
    echo "🤖 エージェント \$i 起動中..."
    tmux send-keys -t "\${SESSION_PREFIX}-agents:0.\$i" "claude --dangerously-skip-permissions" C-m
done

echo ""
echo "✅ 起動コマンドを送信しました"
echo ""
echo "📋 各セッションにアタッチして認証してください:"
echo "   tmux attach-session -t \${SESSION_PREFIX}-president"
echo "   tmux attach-session -t \${SESSION_PREFIX}-agents"
echo ""
echo "💡 認証後、以下で指示を送信できます:"
echo "   .ai-team/agent-send.sh president \"プロジェクトを開始してください\""
LAUNCH_SCRIPT

chmod +x "$AI_TEAM_DIR/launch-agents.sh"

# project-status.sh の生成
cat > "$AI_TEAM_DIR/project-status.sh" << STATUS_SCRIPT
#!/bin/bash

# 📊 プロジェクト進捗確認 - プロジェクト: $PROJECT_NAME

echo "📊 プロジェクト進捗: $PROJECT_NAME"
echo "================================"
echo ""

# セッション確認
if tmux has-session -t "${PROJECT_NAME}-agents" 2>/dev/null; then
    echo "✅ エージェントセッション: 実行中"
else
    echo "❌ エージェントセッション: 停止中"
fi

if tmux has-session -t "${PROJECT_NAME}-president" 2>/dev/null; then
    echo "✅ プレジデントセッション: 実行中"
else
    echo "❌ プレジデントセッション: 停止中"
fi

echo ""
echo "📋 Worker完了状態:"
echo "-------------------"

for i in 1 2 3; do
    if [[ -f .ai-team/tmp/worker\${i}_done.txt ]]; then
        echo "  Worker\$i: ✅ 完了"
    else
        echo "  Worker\$i: 🔄 作業中"
    fi
done

echo ""
echo "💡 操作:"
echo "   .ai-team/setup.sh      - 環境セットアップ"
echo "   .ai-team/launch-agents.sh - Claude起動"
echo "   .ai-team/agent-send.sh [agent] [msg] - 指示送信"
STATUS_SCRIPT

chmod +x "$AI_TEAM_DIR/project-status.sh"

# .gitignore の更新
if [[ -f "$TARGET_DIR/.gitignore" ]]; then
    if ! grep -q "\.ai-team/logs/" "$TARGET_DIR/.gitignore"; then
        echo "" >> "$TARGET_DIR/.gitignore"
        echo "# AI Team (generated)" >> "$TARGET_DIR/.gitignore"
        echo ".ai-team/logs/" >> "$TARGET_DIR/.gitignore"
        echo ".ai-team/tmp/" >> "$TARGET_DIR/.gitignore"
        log_info ".gitignoreを更新しました"
    fi
else
    cp "$AI_TEAM_DIR/.gitignore" "$TARGET_DIR/.gitignore"
    log_info ".gitignoreをコピーしました"
fi

# README追記（必要な場合）
README_ADD="$TARGET_DIR/AI_TEAM_README.md"
cat > "$README_ADD" << EOF
# AIチーム環境 ($PROJECT_NAME)

このプロジェクトにはマルチエージェントAIチーム環境が含まれています。

## クイックスタート

\`\`\`bash
# 1. 環境セットアップ（tmuxセッション作成）
.ai-team/setup.sh

# 2. Claude Code起動
.ai-team/launch-agents.sh
# 各画面でブラウザ認証を行ってください

# 3. PRESIDENTに指示
.ai-team/agent-send.sh president "あなたはpresidentです。指示書に従ってプロジェクトを進めてください"
\`\`\`

## セッション操作

\`\`\`bash
# セッション一覧
tmux list-sessions

# PRESIDENTセッションにアタッチ
tmux attach-session -t ${PROJECT_NAME}-president
# デタッチ: Ctrl+b, d

# エージェントセッションにアタッチ
tmux attach-session -t ${PROJECT_NAME}-agents
# デタッチ: Ctrl+b, d
\`\`\`

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
| \`.ai-team/setup.sh\` | tmuxセッション作成 |
| \`.ai-team/launch-agents.sh\` | Claude Code一括起動 |
| \`.ai-team/agent-send.sh\` | エージェントへの指示送信 |
| \`.ai-team/project-status.sh\` | 進捗確認 |

詳細な指示書: \`.ai-team/instructions/\`
EOF

# 完了報告
echo ""
log_success "🎉 エクスポート完了！"
echo ""
echo "📁 以下のファイルを作成しました:"
echo "   $AI_TEAM_DIR/"
echo "     ├── setup.sh           # 環境セットアップ"
echo "     ├── launch-agents.sh   # Claude起動"
echo "     ├── agent-send.sh      # 指示送信"
echo "     ├── project-status.sh  # 進捗確認"
echo "     ├── instructions/      # 指示書"
echo "     ├── logs/              # 通信ログ"
echo "     └── tmp/               # 一時ファイル"
echo ""
echo "📋 次のステップ:"
echo ""
echo "  1. cd $TARGET_DIR"
echo "  2. .ai-team/setup.sh"
echo "  3. .ai-team/launch-agents.sh"
echo "  4. .ai-team/agent-send.sh president \"プロジェクトを開始してください\""
echo ""

#!/bin/bash

# Slidev自動起動・復旧スクリプト
# このスクリプトは、Slidevサーバーが停止した場合に自動的に再起動します

SLIDE_FILE="思春期特発性側弯症_mermaid_slidev.md"
PORT=3030
LOG_FILE="slidev.log"

echo "🚀 Slidev自動起動スクリプトを開始します..."
echo "📁 スライドファイル: $SLIDE_FILE"
echo "🌐 ポート: $PORT"
echo "📝 ログファイル: $LOG_FILE"
echo ""
echo "停止するには Ctrl+C を押してください"
echo ""

# 既存のSlidevプロセスを終了
pkill -f "slidev.*$SLIDE_FILE" 2>/dev/null

# 無限ループで監視
while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Slidevサーバーを起動します..."
    
    # Slidevを起動（エラーが発生しても続行）
    npx slidev "$SLIDE_FILE" --port $PORT --open 2>&1 | tee -a "$LOG_FILE"
    
    # プロセスが終了した場合
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] Slidevが正常に終了しました"
    else
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  Slidevがエラーで終了しました (終了コード: $EXIT_CODE)"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 5秒後に再起動します..."
        sleep 5
    fi
done
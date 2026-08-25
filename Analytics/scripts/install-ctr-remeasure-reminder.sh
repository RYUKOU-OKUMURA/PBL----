#!/usr/bin/env bash
# 2026-08-14 09:00 JST に CTR再測定を走らせる launchd リマインダーを登録/解除する。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PLIST_SRC="${SCRIPT_DIR}/com.pbl.ctr-remeasure.plist.template"
PLIST_DST="${HOME}/Library/LaunchAgents/com.pbl.ctr-remeasure.plist"
LABEL="com.pbl.ctr-remeasure"

usage() {
  cat <<'EOF'
Usage: install-ctr-remeasure-reminder.sh {install|uninstall|status}

  install   2026-08-14 09:00 に再測定スクリプトを実行する launchd を登録
  uninstall 登録を解除
  status    登録状態を表示
EOF
}

render_plist() {
  sed \
    -e "s|__ROOT__|${ROOT}|g" \
    -e "s|__SCRIPT__|${ROOT}/Analytics/scripts/remeasure_ctr_improvements.sh|g" \
    -e "s|__LOG__|${ROOT}/Analytics/projects/2026-07_ctr-refresh/logs/ctr-remeasure.log|g" \
    -e "s|__ERR__|${ROOT}/Analytics/projects/2026-07_ctr-refresh/logs/ctr-remeasure.err|g" \
    "${PLIST_SRC}"
}

cmd="${1:-}"
case "$cmd" in
  install)
    mkdir -p "${ROOT}/Analytics/projects/2026-07_ctr-refresh/logs"
    chmod +x "${ROOT}/Analytics/scripts/remeasure_ctr_improvements.sh"
    render_plist > "${PLIST_DST}"
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    launchctl bootstrap "gui/$(id -u)" "${PLIST_DST}"
    echo "登録しました: ${PLIST_DST}"
    echo "実行予定: 2026-08-14 09:00（Macのローカル時刻）"
    echo "手動テスト: bash Analytics/scripts/remeasure_ctr_improvements.sh --dry-run"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
    rm -f "${PLIST_DST}"
    echo "解除しました: ${LABEL}"
    ;;
  status)
    if launchctl print "gui/$(id -u)/${LABEL}" >/dev/null 2>&1; then
      echo "登録済み: ${PLIST_DST}"
      launchctl print "gui/$(id -u)/${LABEL}" | rg -n "state =|path =|last exit|runs =|program =" || true
    else
      echo "未登録: ${LABEL}"
    fi
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac

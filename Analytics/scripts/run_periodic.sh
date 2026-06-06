#!/usr/bin/env bash
# 直近14日間の periodic データ取得（CSV のみ）
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

END=""
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: run_periodic.sh [--end YYYY-MM-DD] [--dry-run]

  直近14日（終了日含む）の GA4×WP×GSC データを CSV で取得します。

Options:
  --end DATE    集計終了日（デフォルト: 今日）
  --dry-run     実行コマンドのみ表示
  -h, --help    このヘルプ
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --end)
      END="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "不明な引数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$END" ]]; then
  END="$(date +%Y-%m-%d)"
fi

if [[ "$(uname)" == "Darwin" ]]; then
  START="$(date -v-13d -j -f "%Y-%m-%d" "$END" +%Y-%m-%d)"
else
  START="$(date -d "$END -13 days" +%Y-%m-%d)"
fi

OUT_DIR="Analytics/periodic/${START}_${END}"

if [[ -d "$OUT_DIR" ]]; then
  echo "警告: 既存フォルダを上書き更新します: $OUT_DIR" >&2
fi

PYTHON="${PYTHON:-python3}"
CMD=("$PYTHON" analyze_content_seo.py --start "$START" --end "$END")

echo "集計期間: $START 〜 $END"
echo "出力先:   $OUT_DIR"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: ${CMD[*]}"
  exit 0
fi

exec "${CMD[@]}"

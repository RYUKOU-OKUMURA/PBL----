#!/usr/bin/env bash
# CTR改善（965/612/976）の再測定を実行し、ベースラインと比較レポートを出力する。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

END=""
WINDOW_DAYS=7
NOTIFY=0
SKIP_FETCH=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: remeasure_ctr_improvements.sh [--end YYYY-MM-DD] [--window-days N] [--notify] [--skip-fetch] [--dry-run]

  CTR改善3記事（965/612/976）の再測定を実行します。
  デフォルト終了日: 2026-08-13（8/14朝の再測定想定。--end で上書き可）

Options:
  --end DATE         集計終了日（含む）
  --window-days N    集計日数（デフォルト: 7）
  --notify           macOS通知を表示（launchd用）
  --skip-fetch       既存CSVのみ比較（analyze_content_seo.py をスキップ）
  --dry-run          実行内容のみ表示
  -h, --help         ヘルプ
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --end)
      END="$2"
      shift 2
      ;;
    --window-days)
      WINDOW_DAYS="$2"
      shift 2
      ;;
    --notify)
      NOTIFY=1
      shift
      ;;
    --skip-fetch)
      SKIP_FETCH=1
      shift
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
  END="2026-08-13"
fi

if [[ "$(uname)" == "Darwin" ]]; then
  START="$(date -v-"$((WINDOW_DAYS - 1))"d -j -f "%Y-%m-%d" "$END" +%Y-%m-%d)"
else
  START="$(date -d "$END -$((WINDOW_DAYS - 1)) days" +%Y-%m-%d)"
fi

OUT_DIR="Analytics/periodic/${START}_${END}"
BASELINE_CSV="Analytics/periodic/2026-07-23_2026-07-29/ga4_wp_gsc_analysis.csv"
REPORT="${OUT_DIR}/ctr_remeasure_report.md"
PYTHON="${PYTHON:-python3}"

echo "=== CTR改善 再測定 ==="
echo "期間:     ${START} 〜 ${END}（${WINDOW_DAYS}日）"
echo "出力先:   ${OUT_DIR}"
echo "ベース:   ${BASELINE_CSV}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: ${PYTHON} analyze_content_seo.py --start ${START} --end ${END}"
  echo "dry-run: ${PYTHON} Analytics/scripts/compare_ctr_baseline.py --measure-csv ${OUT_DIR}/ga4_wp_gsc_analysis.csv ..."
  exit 0
fi

mkdir -p Analytics/logs

if [[ "$SKIP_FETCH" -eq 0 ]]; then
  if [[ -f "${OUT_DIR}/ga4_wp_gsc_analysis.csv" ]]; then
    echo "既存CSVを更新します: ${OUT_DIR}/ga4_wp_gsc_analysis.csv"
  fi
  "${PYTHON}" analyze_content_seo.py --start "${START}" --end "${END}"
fi

MEASURE_CSV="${OUT_DIR}/ga4_wp_gsc_analysis.csv"
if [[ ! -f "$MEASURE_CSV" ]]; then
  echo "エラー: 再測定CSVがありません: ${MEASURE_CSV}" >&2
  echo "  --skip-fetch なしで再実行するか、GSC/GA4認証を確認してください。" >&2
  exit 1
fi

"${PYTHON}" Analytics/scripts/compare_ctr_baseline.py \
  --baseline-csv "${BASELINE_CSV}" \
  --measure-csv "${MEASURE_CSV}" \
  --measure-start "${START}" \
  --measure-end "${END}" \
  --output "${REPORT}"

if [[ "$NOTIFY" -eq 1 && "$(uname)" == "Darwin" ]]; then
  osascript -e "display notification \"レポート: ${REPORT}\" with title \"CTR改善 再測定完了\" subtitle \"${START}〜${END}\""
  open -R "${ROOT}/${REPORT}" 2>/dev/null || true
fi

echo ""
echo "完了: ${REPORT}"

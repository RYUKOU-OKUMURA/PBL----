#!/usr/bin/env bash
# カレンダー半月（1–14日 / 15–末日）の periodic データを CSV で取得する。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT"

END=""
CURRENT=0
AD_HOC=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage: run_periodic.sh [--current | --ad-hoc] [--end YYYY-MM-DD] [--dry-run]

  デフォルト: 直近の完了済みカレンダー半月（1–14 または 15–末日）を取得。
  同じ半月フォルダへの再実行は上書き更新します。

Options:
  --current     進行中の半月を取得（フォルダ名は 15–末日など満了日。中身は今日まで）
  --ad-hoc      直近14日を periodic/ad-hoc/ へ（比較系列には使わない）
  --end DATE    その日を含む半月（--ad-hoc のときは14日窓の終了日）
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
    --current)
      CURRENT=1
      shift
      ;;
    --ad-hoc)
      AD_HOC=1
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

if [[ "$CURRENT" -eq 1 && "$AD_HOC" -eq 1 ]]; then
  echo "--current と --ad-hoc は同時に使えません" >&2
  exit 1
fi

PYTHON="${PYTHON:-python3}"
PW_ARGS=()
if [[ "$CURRENT" -eq 1 ]]; then
  PW_ARGS+=(--current)
fi
if [[ "$AD_HOC" -eq 1 ]]; then
  PW_ARGS+=(--ad-hoc)
fi
if [[ -n "$END" ]]; then
  PW_ARGS+=(--end "$END")
fi

if [[ ${#PW_ARGS[@]} -eq 0 ]]; then
  eval "$("$PYTHON" "$SCRIPT_DIR/period_window.py")"
else
  eval "$("$PYTHON" "$SCRIPT_DIR/period_window.py" "${PW_ARGS[@]}")"
fi

if [[ -z "${START:-}" || -z "${OUT_DIR:-}" ]]; then
  echo "期間の決定に失敗しました" >&2
  exit 1
fi

echo "役割:     ${ROLE}"
echo "窓:       ${START} 〜 ${WINDOW_END}"
echo "取得終了: ${END}"
echo "出力先:   ${OUT_DIR}"

if [[ -d "$OUT_DIR" ]]; then
  echo "警告: 既存フォルダを上書き更新します: ${OUT_DIR}" >&2
fi

CMD=("$PYTHON" analyze_content_seo.py --start "$START" --end "$END" --output-dir "$OUT_DIR")

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: ${CMD[*]}"
  exit 0
fi

mkdir -p "$OUT_DIR"
"${CMD[@]}"

FETCHED_AT="$(date +%Y-%m-%dT%H:%M:%S%z)"
"$PYTHON" - "$OUT_DIR" "$ROLE" "$START" "$WINDOW_END" "$END" "$FETCHED_AT" <<'PY'
import json
import sys
from pathlib import Path

out_dir, role, window_start, window_end, data_end, fetched_at = sys.argv[1:]
meta = {
    "role": role,
    "window_start": window_start,
    "window_end": window_end,
    "data_end": data_end,
    "fetched_at": fetched_at,
}
path = Path(out_dir) / "meta.json"
path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"meta: {path}")
PY

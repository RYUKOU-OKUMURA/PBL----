#!/usr/bin/env python3
"""CTR改善3記事（965/612/976）のベースライン vs 再測定期間を比較する。"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

TARGET_IDS = ("965", "612", "976")
DEFAULT_BASELINE = Path("Analytics/periodic/2026-07-23_2026-07-29/ga4_wp_gsc_analysis.csv")


def load_targets(csv_path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            post_id = row.get("post_id", "")
            if post_id in TARGET_IDS:
                rows[post_id] = row
    return rows


def as_int(value: str | None) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def ctr(clicks: int, impressions: int) -> float:
    if impressions <= 0:
        return 0.0
    return clicks / impressions * 100.0


def delta(current: int, baseline: int) -> str:
    diff = current - baseline
    if diff > 0:
        return f"+{diff}"
    return str(diff)


def delta_pct(current: float, baseline: float) -> str:
    diff = current - baseline
    if diff > 0:
        return f"+{diff:.2f}pt"
    return f"{diff:.2f}pt"


def summarize_period(csv_path: Path) -> tuple[dict[str, dict[str, str]], int, int, int]:
    targets = load_targets(csv_path)
    total_pv = total_sessions = total_engaged = 0
    with csv_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            total_pv += as_int(row.get("screenPageViews"))
            total_sessions += as_int(row.get("sessions"))
            total_engaged += as_int(row.get("engagedSessions"))
    return targets, total_pv, total_sessions, total_engaged


def build_report(
    baseline_csv: Path,
    measure_csv: Path,
    measure_start: str,
    measure_end: str,
) -> str:
    baseline_rows, base_pv, base_sess, base_eng = summarize_period(baseline_csv)
    measure_rows, meas_pv, meas_sess, meas_eng = summarize_period(measure_csv)

    lines = [
        "# CTR改善 再測定レポート",
        "",
        f"- ベースライン: `{baseline_csv.parent.name}`",
        f"- 再測定期間: `{measure_start}` 〜 `{measure_end}` (`{measure_csv.parent.name}`)",
        "",
        "## サイト全体（GA4）",
        "",
        "| 指標 | ベースライン | 再測定 | 差分 |",
        "|------|-------------|--------|------|",
        f"| PV | {base_pv} | {meas_pv} | {delta(meas_pv, base_pv)} |",
        f"| セッション | {base_sess} | {meas_sess} | {delta(meas_sess, base_sess)} |",
        f"| エンゲージセッション | {base_eng} | {meas_eng} | {delta(meas_eng, base_eng)} |",
        "",
        "## 対象記事（965 / 612 / 976）",
        "",
        "| ID | PV | セッション | GSCクリック | GSC表示 | CTR | ベースラインCTR | CTR差 |",
        "|----|----|-----------|------------|---------|-----|----------------|-------|",
    ]

    for post_id in TARGET_IDS:
        base = baseline_rows.get(post_id, {})
        meas = measure_rows.get(post_id, {})
        base_clicks = as_int(base.get("gsc_clicks"))
        base_imps = as_int(base.get("gsc_impressions"))
        meas_clicks = as_int(meas.get("gsc_clicks"))
        meas_imps = as_int(meas.get("gsc_impressions"))
        base_ctr = ctr(base_clicks, base_imps)
        meas_ctr = ctr(meas_clicks, meas_imps)
        lines.append(
            "| {id} | {pv} | {sess} | {clk} | {imp} | {ctr:.2f}% | {bctr:.2f}% | {dctr} |".format(
                id=post_id,
                pv=as_int(meas.get("screenPageViews")),
                sess=as_int(meas.get("sessions")),
                clk=meas_clicks,
                imp=meas_imps,
                ctr=meas_ctr,
                bctr=base_ctr,
                dctr=delta_pct(meas_ctr, base_ctr),
            )
        )

    lines.extend(
        [
            "",
            "## メモ",
            "",
            "- GSCは2〜3日遅延あり。8/14実行時は `--end 2026-08-13` 想定。",
            "- ベースライン詳細: `HPブログ記事/workspace/ctr-refresh-20260730/rollout_summary.md`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="CTR改善のベースライン比較レポートを生成")
    parser.add_argument(
        "--baseline-csv",
        type=Path,
        default=DEFAULT_BASELINE,
        help="ベースラインCSV（デフォルト: 2026-07-23_2026-07-29）",
    )
    parser.add_argument("--measure-csv", type=Path, required=True, help="再測定期間CSV")
    parser.add_argument("--measure-start", required=True, help="再測定開始日 YYYY-MM-DD")
    parser.add_argument("--measure-end", required=True, help="再測定終了日 YYYY-MM-DD")
    parser.add_argument(
        "--output",
        type=Path,
        help="Markdown出力先（省略時は measure CSV と同じフォルダ）",
    )
    args = parser.parse_args()

    if not args.baseline_csv.is_file():
        raise SystemExit(f"ベースラインCSVが見つかりません: {args.baseline_csv}")
    if not args.measure_csv.is_file():
        raise SystemExit(f"再測定CSVが見つかりません: {args.measure_csv}")

    report = build_report(
        args.baseline_csv,
        args.measure_csv,
        args.measure_start,
        args.measure_end,
    )
    output = args.output or (args.measure_csv.parent / "ctr_remeasure_report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n保存: {output}")


if __name__ == "__main__":
    main()

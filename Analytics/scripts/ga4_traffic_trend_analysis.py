#!/usr/bin/env python3
"""
GA4 日次トラフィックを取得し、期間比較で急増を定量化する（一時分析用）。
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

try:
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )
except ImportError as e:
    print("必要: pip install google-analytics-data google-auth python-dotenv", file=sys.stderr)
    raise SystemExit(1) from e


def _parse_ga_date(s: str) -> date:
    # GA4 returns YYYYMMDD
    return datetime.strptime(s, "%Y%m%d").date()


def fetch_daily(
    client: BetaAnalyticsDataClient,
    property_path: str,
    start: date,
    end: date,
) -> list[dict]:
    req = RunReportRequest(
        property=property_path,
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="totalUsers"),
        ],
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows or []:
        d = _parse_ga_date(row.dimension_values[0].value)
        mv = row.metric_values
        rows.append(
            {
                "date": d,
                "sessions": int(float(mv[0].value)),
                "screenPageViews": int(float(mv[1].value)),
                "totalUsers": int(float(mv[2].value)),
            }
        )
    rows.sort(key=lambda x: x["date"])
    return rows


def fetch_channel_sessions(
    client: BetaAnalyticsDataClient,
    property_path: str,
    start: date,
    end: date,
) -> dict[str, int]:
    req = RunReportRequest(
        property=property_path,
        dimensions=[Dimension(name="sessionDefaultChannelGrouping")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
    )
    resp = client.run_report(req)
    out: dict[str, int] = defaultdict(int)
    for row in resp.rows or []:
        ch = row.dimension_values[0].value or "(not set)"
        out[ch] += int(float(row.metric_values[0].value))
    return dict(out)


def sum_range(rows: list[dict], start: date, end: date) -> dict:
    s_sess = s_pv = s_u = 0
    for r in rows:
        if start <= r["date"] <= end:
            s_sess += r["sessions"]
            s_pv += r["screenPageViews"]
            s_u += r["totalUsers"]
    return {"sessions": s_sess, "screenPageViews": s_pv, "totalUsers": s_u, "days": (end - start).days + 1}


def pct_change(new: float, old: float) -> float | None:
    if old == 0:
        return None
    return (new - old) / old * 100.0


def main() -> None:
    prop_id = os.getenv("GA4_PROPERTY_ID", "").strip()
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not prop_id or not creds_path:
        print("GA4_PROPERTY_ID / GOOGLE_APPLICATION_CREDENTIALS が必要です。", file=sys.stderr)
        raise SystemExit(2)
    if not Path(creds_path).exists():
        print(f"認証ファイルなし: {creds_path}", file=sys.stderr)
        raise SystemExit(2)

    end = date.today()
    start = end - timedelta(days=59)
    creds = service_account.Credentials.from_service_account_file(creds_path)
    client = BetaAnalyticsDataClient(credentials=creds)
    prop = f"properties/{prop_id}"

    daily = fetch_daily(client, prop, start, end)
    if not daily:
        print("日次データが取得できませんでした。")
        raise SystemExit(3)

    # 比較ウィンドウ（今日含む直近14日 vs その直前14日）
    last14_end = end
    last14_start = end - timedelta(days=13)
    prev14_end = last14_start - timedelta(days=1)
    prev14_start = prev14_end - timedelta(days=13)

    a = sum_range(daily, last14_start, last14_end)
    b = sum_range(daily, prev14_start, prev14_end)

    # 直近7 vs 前7
    last7_start = end - timedelta(days=6)
    prev7_end = last7_start - timedelta(days=1)
    prev7_start = prev7_end - timedelta(days=6)

    a7 = sum_range(daily, last7_start, end)
    b7 = sum_range(daily, prev7_start, prev7_end)

    # 日次ピーク（直近60日内）
    peak = max(daily, key=lambda x: x["sessions"])
    low = min(daily, key=lambda x: x["sessions"])
    recent_avg = a["sessions"] / 14
    prev_avg = b["sessions"] / 14

    ch_last = fetch_channel_sessions(client, prop, last14_start, last14_end)
    ch_prev = fetch_channel_sessions(client, prop, prev14_start, prev14_end)

    # 出力
    print("=== GA4 トラフィック急増の純粋な数値分析 ===\n")
    print(f"取得期間: {start} 〜 {end}（{len(daily)}日分）\n")

    print("【直近14日 vs その前14日】")
    print(f"  直近14日: {last14_start} 〜 {last14_end}")
    print(f"    セッション: {a['sessions']:,}  /  PV: {a['screenPageViews']:,}  / ユーザー: {a['totalUsers']:,}")
    print(f"    日次平均セッション: {recent_avg:.1f}")
    print(f"  前期14日: {prev14_start} 〜 {prev14_end}")
    print(f"    セッション: {b['sessions']:,}  /  PV: {b['screenPageViews']:,}  / ユーザー: {b['totalUsers']:,}")
    print(f"    日次平均セッション: {prev_avg:.1f}")

    ps = pct_change(a["sessions"], b["sessions"])
    ppv = pct_change(a["screenPageViews"], b["screenPageViews"])
    pu = pct_change(a["totalUsers"], b["totalUsers"])
    print("\n  → 変化率（直近14日 vs 前期14日）")
    print(f"    セッション: {ps:+.1f}%" if ps is not None else "    セッション: N/A")
    print(f"    PV:         {ppv:+.1f}%" if ppv is not None else "    PV: N/A")
    print(f"    ユーザー:   {pu:+.1f}%" if pu is not None else "    ユーザー: N/A")

    p7s = pct_change(a7["sessions"], b7["sessions"])
    print("\n【直近7日 vs その前7日】")
    print(f"  直近7日セッション: {a7['sessions']:,}  / 前期7日: {b7['sessions']:,}")
    if p7s is not None:
        print(f"  → セッション変化率: {p7s:+.1f}%")

    print("\n【60日以内の日次ピーク】")
    print(f"  最大セッション日: {peak['date']}  … {peak['sessions']:,} セッション")
    print(f"  最小セッション日: {low['date']}  … {low['sessions']:,} セッション")

    print("\n【チャネル別セッション（直近14日）】")
    for ch, sess in sorted(ch_last.items(), key=lambda x: -x[1])[:8]:
        prev_s = ch_prev.get(ch, 0)
        chg = pct_change(sess, prev_s)
        extra = f"  (前期比 {chg:+.1f}%)" if chg is not None and prev_s else ""
        print(f"  {ch}: {sess:,}{extra}")

    print("\n【直近14日の日次セッション（末尾）】")
    tail = [r for r in daily if r["date"] >= last14_start - timedelta(days=3)]
    for r in tail[-18:]:
        print(f"  {r['date']}: sessions={r['sessions']:,}  pv={r['screenPageViews']:,}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""カレンダー半月（1–14日 / 15–末日）の期間を決める。"""

from __future__ import annotations

import argparse
import calendar
import json
from datetime import date, datetime, timedelta
from typing import Tuple

Half = Tuple[date, date]


def parse_iso(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def calendar_half(d: date) -> Half:
    last = last_day(d.year, d.month)
    if d.day <= 14:
        return date(d.year, d.month, 1), date(d.year, d.month, 14)
    return date(d.year, d.month, 15), date(d.year, d.month, last)


def previous_half(d: date) -> Half:
    start, _end = calendar_half(d)
    if start.day == 1:
        if start.month == 1:
            year, month = start.year - 1, 12
        else:
            year, month = start.year, start.month - 1
        last = last_day(year, month)
        return date(year, month, 15), date(year, month, last)
    return date(start.year, start.month, 1), date(start.year, start.month, 14)


def latest_completed(today: date) -> Half:
    """今日を含む半月は未完了（GSC遅延含む）とみなし、直前の半月を返す。"""
    return previous_half(today)


def current_half(today: date) -> Half:
    return calendar_half(today)


def rolling_14(end: date) -> Half:
    return end - timedelta(days=13), end


def is_exact_calendar_half(start: str, end: str) -> bool:
    try:
        s = parse_iso(start)
        e = parse_iso(end)
    except ValueError:
        return False
    hs, he = calendar_half(s)
    return s == hs and e == he


def resolve(
    today: date,
    *,
    current: bool = False,
    ad_hoc: bool = False,
    end: str | None = None,
) -> dict:
    if ad_hoc:
        data_end = parse_iso(end) if end else today
        start, window_end = rolling_14(data_end)
        return {
            "role": "ad-hoc",
            "window_start": start.isoformat(),
            "window_end": window_end.isoformat(),
            "data_end": data_end.isoformat(),
            "out_dir": f"Analytics/periodic/ad-hoc/{start.isoformat()}_{window_end.isoformat()}",
        }

    if end:
        anchor = parse_iso(end)
        start, window_end = calendar_half(anchor)
        data_end = min(anchor, window_end, today)
        role = "current" if data_end < window_end else "completed"
        return {
            "role": role,
            "window_start": start.isoformat(),
            "window_end": window_end.isoformat(),
            "data_end": data_end.isoformat(),
            "out_dir": f"Analytics/periodic/{start.isoformat()}_{window_end.isoformat()}",
        }

    if current:
        start, window_end = current_half(today)
        data_end = min(today, window_end)
        return {
            "role": "current",
            "window_start": start.isoformat(),
            "window_end": window_end.isoformat(),
            "data_end": data_end.isoformat(),
            "out_dir": f"Analytics/periodic/{start.isoformat()}_{window_end.isoformat()}",
        }

    start, window_end = latest_completed(today)
    return {
        "role": "completed",
        "window_start": start.isoformat(),
        "window_end": window_end.isoformat(),
        "data_end": window_end.isoformat(),
        "out_dir": f"Analytics/periodic/{start.isoformat()}_{window_end.isoformat()}",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="periodic 取得期間をカレンダー半月で決める")
    parser.add_argument("--current", action="store_true", help="進行中の半月")
    parser.add_argument("--ad-hoc", action="store_true", help="直近14日を ad-hoc/ へ")
    parser.add_argument("--end", help="終了日 YYYY-MM-DD（その日を含む半月、または ad-hoc の終了日）")
    parser.add_argument("--today", help="基準日（テスト用）")
    parser.add_argument("--json", action="store_true", help="JSON で出力")
    args = parser.parse_args()
    today = parse_iso(args.today) if args.today else date.today()
    info = resolve(today, current=args.current, ad_hoc=args.ad_hoc, end=args.end)
    if args.json:
        print(json.dumps(info, ensure_ascii=False))
        return
    print(f"START={info['window_start']}")
    print(f"END={info['data_end']}")
    print(f"WINDOW_END={info['window_end']}")
    print(f"OUT_DIR={info['out_dir']}")
    print(f"ROLE={info['role']}")


if __name__ == "__main__":
    main()

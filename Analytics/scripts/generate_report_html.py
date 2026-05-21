#!/usr/bin/env python3
"""
periodic フォルダの CSV から index.html を生成する。
横断ダッシュボード（Analytics/index.html）も生成可能。
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
ANALYTICS = ROOT / "Analytics"
PERIODIC = ANALYTICS / "periodic"
PROJECTS = ANALYTICS / "projects"
SITE_NAME = "フィジカルバランスラボ整体院"
PERIOD_DIR_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})$")

PROJECT_README: dict[str, str] = {
    "2026-03_tv-redcode": "README_analysis.md",
    "2026-03_search-barrier": "README_search_barrier.md",
}

PROJECT_DESCRIPTIONS: dict[str, str] = {
    "2026-03_tv-redcode": "TV放映に伴うアクセス急増の深掘り",
    "2026-03_search-barrier": "検索が伸びにくかった要因の整理",
}

load_dotenv(ROOT / ".env")

try:
    import markdown2
except ImportError:
    markdown2 = None

try:
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
except ImportError:
    service_account = None
    BetaAnalyticsDataClient = None


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _parse_ga_date(s: str) -> date:
    return datetime.strptime(s, "%Y%m%d").date()


def pct_change(new: float, old: float) -> float | None:
    if old == 0:
        return None
    return (new - old) / old * 100.0


def clean_title(raw: str) -> str:
    return html.unescape(raw or "").strip()


def load_main_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_queries_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def summarize_main_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total_pv = total_sess = total_eng = total_gsc_clicks = total_gsc_imp = 0
    posts: list[dict[str, Any]] = []

    for row in rows:
        pv = int(float(row.get("screenPageViews") or 0))
        sess = int(float(row.get("sessions") or 0))
        eng = int(float(row.get("engagedSessions") or 0))
        gsc_c = int(float(row.get("gsc_clicks") or 0))
        gsc_i = int(float(row.get("gsc_impressions") or 0))
        total_pv += pv
        total_sess += sess
        total_eng += eng
        total_gsc_clicks += gsc_c
        total_gsc_imp += gsc_i

        title = clean_title(row.get("title", ""))
        if title and row.get("post_id"):
            posts.append(
                {
                    "post_id": row.get("post_id", ""),
                    "title": title,
                    "pv": pv,
                    "sessions": sess,
                    "gsc_clicks": gsc_c,
                    "link": row.get("link", ""),
                }
            )

    posts.sort(key=lambda x: x["pv"], reverse=True)
    ctr = (total_gsc_clicks / total_gsc_imp * 100) if total_gsc_imp else 0.0
    return {
        "total_pv": total_pv,
        "total_sessions": total_sess,
        "total_engaged": total_eng,
        "gsc_clicks": total_gsc_clicks,
        "gsc_impressions": total_gsc_imp,
        "gsc_ctr": ctr,
        "top_posts": posts[:10],
    }


def summarize_queries(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, float]] = defaultdict(
        lambda: {"clicks": 0, "impressions": 0, "position_sum": 0.0, "count": 0}
    )
    for row in rows:
        q = (row.get("query") or "").strip()
        if not q:
            continue
        agg[q]["clicks"] += int(float(row.get("clicks") or 0))
        agg[q]["impressions"] += int(float(row.get("impressions") or 0))
        agg[q]["position_sum"] += float(row.get("position") or 0)
        agg[q]["count"] += 1

    out: list[dict[str, Any]] = []
    for q, d in agg.items():
        count = int(d["count"]) or 1
        out.append(
            {
                "query": q,
                "clicks": int(d["clicks"]),
                "impressions": int(d["impressions"]),
                "position": d["position_sum"] / count,
            }
        )
    out.sort(key=lambda x: (-x["clicks"], -x["impressions"]))
    return out[:10]


def ga4_client() -> tuple[Any, str] | tuple[None, None]:
    if service_account is None or BetaAnalyticsDataClient is None:
        return None, None
    prop_id = os.getenv("GA4_PROPERTY_ID", "").strip()
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not prop_id or not creds_path or not Path(creds_path).exists():
        return None, None
    creds = service_account.Credentials.from_service_account_file(creds_path)
    return BetaAnalyticsDataClient(credentials=creds), f"properties/{prop_id}"


def fetch_daily_sessions(client: Any, prop: str, start: date, end: date) -> list[dict[str, Any]]:
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, RunReportRequest

    req = RunReportRequest(
        property=prop,
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="screenPageViews"),
            Metric(name="totalUsers"),
        ],
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
    )
    resp = client.run_report(req)
    rows: list[dict[str, Any]] = []
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


def sum_range(rows: list[dict[str, Any]], start: date, end: date) -> dict[str, int]:
    s_sess = s_pv = s_u = 0
    for r in rows:
        d = r["date"]
        if start <= d <= end:
            s_sess += int(r["sessions"])
            s_pv += int(r["screenPageViews"])
            s_u += int(r["totalUsers"])
    return {"sessions": s_sess, "screenPageViews": s_pv, "totalUsers": s_u}


def fetch_ga4_context(start: date, end: date) -> dict[str, Any]:
    client, prop = ga4_client()
    if not client or not prop:
        return {"available": False}

    period_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days - 1)
    fetch_start = min(prev_start, start)
    daily = fetch_daily_sessions(client, prop, fetch_start, end)
    if not daily:
        return {"available": False}

    current = sum_range(daily, start, end)
    previous = sum_range(daily, prev_start, prev_end)
    in_period = [r for r in daily if start <= r["date"] <= end]

    return {
        "available": True,
        "daily": in_period,
        "prev_start": prev_start,
        "prev_end": prev_end,
        "session_change": pct_change(current["sessions"], previous["sessions"]),
        "pv_change": pct_change(current["screenPageViews"], previous["screenPageViews"]),
        "user_change": pct_change(current["totalUsers"], previous["totalUsers"]),
        "ga_sessions": current["sessions"],
        "ga_pv": current["screenPageViews"],
        "ga_users": current["totalUsers"],
    }


def parse_period_dir(name: str) -> tuple[date, date] | None:
    m = PERIOD_DIR_RE.match(name)
    if not m:
        return None
    return _parse_date(m.group(1)), _parse_date(m.group(2))


def discover_periodic_dirs() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not PERIODIC.exists():
        return items
    for path in sorted(PERIODIC.iterdir()):
        if not path.is_dir():
            continue
        parsed = parse_period_dir(path.name)
        if not parsed:
            continue
        start, end = parsed
        main_csv = path / "ga4_wp_gsc_analysis.csv"
        if not main_csv.exists():
            continue
        summary = summarize_main_rows(load_main_csv(main_csv))
        items.append(
            {
                "dir": path,
                "name": path.name,
                "start": start,
                "end": end,
                "summary": summary,
                "has_html": (path / "index.html").exists(),
                "has_summary_md": (path / "summary.md").exists(),
            }
        )
    return items


def enrich_periods(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for i, p in enumerate(periods):
        if i == 0:
            p["prev_session_change"] = None
            p["prev_gsc_change"] = None
        else:
            prev_s = periods[i - 1]["summary"]
            curr_s = p["summary"]
            p["prev_session_change"] = pct_change(
                curr_s["total_sessions"], prev_s["total_sessions"]
            )
            p["prev_gsc_change"] = pct_change(
                curr_s["gsc_clicks"], prev_s["gsc_clicks"]
            )
    return periods


def compute_cumulative_top_posts(periods: list[dict[str, Any]]) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"post_id": "", "title": "", "total_pv": 0, "top10_count": 0, "link": ""}
    )
    for p in periods:
        rows = load_main_csv(p["dir"] / "ga4_wp_gsc_analysis.csv")
        top10_ids = {str(x["post_id"]) for x in p["summary"]["top_posts"]}
        for row in rows:
            pid = str(row.get("post_id") or "")
            title = clean_title(row.get("title", ""))
            if not pid or not title:
                continue
            pv = int(float(row.get("screenPageViews") or 0))
            agg[pid]["post_id"] = pid
            agg[pid]["title"] = title
            agg[pid]["total_pv"] += pv
            agg[pid]["link"] = row.get("link", "")
        for pid in top10_ids:
            if pid in agg:
                agg[pid]["top10_count"] += 1
    result = sorted(agg.values(), key=lambda x: x["total_pv"], reverse=True)
    return result[:10]


def generate_trend_notes(
    periods: list[dict[str, Any]],
    cumulative_top: list[dict[str, Any]],
) -> list[str]:
    notes: list[str] = []
    if len(periods) >= 2:
        latest = periods[-1]
        ch = latest.get("prev_session_change")
        if ch is not None:
            notes.append(
                f"最新期（{latest['start']}〜{latest['end']}）のセッションは前期比 {fmt_pct(ch)}。"
            )
    if cumulative_top:
        top = cumulative_top[0]
        title = top["title"]
        if len(title) > 55:
            title = title[:55] + "…"
        notes.append(
            f"累積PV1位: {title}（{fmt_num(top['total_pv'])} PV、TOP10登場 {top['top10_count']} 期）。"
        )
    if len(periods) >= 2:
        best: dict[str, Any] | None = None
        best_change: float | None = None
        for p in periods[1:]:
            ch = p.get("prev_gsc_change")
            if ch is not None and (best_change is None or ch > best_change):
                best_change = ch
                best = p
        if best is not None and best_change is not None:
            notes.append(
                f"GSCクリックの前期比増加が最大: {best['start']}〜{best['end']}（{fmt_pct(best_change)}）。"
            )
    if len(periods) >= 1:
        notes.append(f"登録 periodic 期間数: {len(periods)}。")
    return notes[:4]


def discover_project_dirs() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if not PROJECTS.exists():
        return items
    for path in sorted(PROJECTS.iterdir()):
        if not path.is_dir():
            continue
        name = path.name
        readme_name = PROJECT_README.get(name)
        if not readme_name:
            continue
        readme = path / readme_name
        if not readme.exists():
            continue
        items.append(
            {
                "dir": path,
                "name": name,
                "description": PROJECT_DESCRIPTIONS.get(name, name),
                "readme": readme_name,
                "has_html": (path / "index.html").exists(),
            }
        )
    return items


def fmt_pct_cell(v: float | None) -> str:
    if v is None:
        return "—"
    cls = "negative" if v < 0 else ""
    return f'<span class="{cls}">{fmt_pct(v)}</span>'


def fmt_pct(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:+.1f}%"


def fmt_num(n: int | float) -> str:
    if isinstance(n, float):
        if n == int(n):
            n = int(n)
        else:
            return f"{n:,.1f}"
    return f"{int(n):,}"


def base_css() -> str:
    return """
    :root { color-scheme: light; }
    * { box-sizing: border-box; }
    body {
      margin: 0; padding: 24px 16px 48px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f6f8; color: #1f2937; line-height: 1.6;
    }
    .container { max-width: 1080px; margin: 0 auto; }
    h1 { font-size: 1.6rem; margin: 0 0 8px; }
    h2 { font-size: 1.15rem; margin: 32px 0 12px; border-left: 4px solid #2563eb; padding-left: 10px; }
    .meta { color: #6b7280; font-size: 0.92rem; margin-bottom: 24px; }
    .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
    .card {
      background: #fff; border-radius: 10px; padding: 14px 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,.08);
    }
    .card .label { font-size: 0.78rem; color: #6b7280; margin-bottom: 4px; }
    .card .value { font-size: 1.35rem; font-weight: 700; }
    .card .sub { font-size: 0.78rem; color: #059669; margin-top: 4px; }
    .card .sub.negative { color: #dc2626; }
    table {
      width: 100%; border-collapse: collapse; background: #fff;
      border-radius: 10px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08);
    }
    th, td { padding: 10px 12px; text-align: left; border-bottom: 1px solid #e5e7eb; font-size: 0.92rem; }
    th { background: #eff6ff; font-weight: 600; }
    tr:last-child td { border-bottom: none; }
    .chart-wrap {
      background: #fff; border-radius: 10px; padding: 16px;
      box-shadow: 0 1px 3px rgba(0,0,0,.08);
    }
    .footer { margin-top: 32px; color: #6b7280; font-size: 0.85rem; }
    .footer a { color: #2563eb; }
    .nav { margin-bottom: 16px; }
    .nav a { color: #2563eb; text-decoration: none; }
    .badge {
      display: inline-block; background: #dbeafe; color: #1d4ed8;
      font-size: 0.75rem; padding: 2px 8px; border-radius: 999px; margin-left: 8px;
    }
    .notes {
      background: #fff; border-radius: 10px; padding: 16px 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 24px;
    }
    .notes ul { margin: 0; padding-left: 1.2rem; }
    .notes li { margin: 6px 0; }
    .negative { color: #dc2626; }
    .content {
      background: #fff; border-radius: 10px; padding: 16px 20px;
      box-shadow: 0 1px 3px rgba(0,0,0,.08); margin-bottom: 24px;
    }
    .content h1, .content h2, .content h3 { margin-top: 1.2em; }
    .content table { width: 100%; border-collapse: collapse; margin: 12px 0; }
    .content th, .content td { border: 1px solid #e5e7eb; padding: 6px 8px; font-size: 0.88rem; }
    .content th { background: #f9fafb; }
    """


def render_period_html(
    report_dir: Path,
    start: date,
    end: date,
    main_summary: dict[str, Any],
    top_queries: list[dict[str, Any]],
    ga4: dict[str, Any],
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    has_summary_md = (report_dir / "summary.md").exists()

    change_cards = ""
    if ga4.get("available"):
        for label, key, change_key in [
            ("GA4 セッション", "ga_sessions", "session_change"),
            ("GA4 PV", "ga_pv", "pv_change"),
            ("GA4 ユーザー", "ga_users", "user_change"),
        ]:
            ch = ga4.get(change_key)
            cls = "sub" if (ch is None or ch >= 0) else "sub negative"
            change_cards += f"""
            <div class="card">
              <div class="label">{html.escape(label)}（サイト全体）</div>
              <div class="value">{fmt_num(ga4.get(key, 0))}</div>
              <div class="{cls}">前期比 {fmt_pct(ch)}</div>
            </div>"""

    posts_rows = ""
    for i, p in enumerate(main_summary["top_posts"], 1):
        title = html.escape(p["title"])
        link = p.get("link") or ""
        title_cell = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">{title}</a>' if link else title
        posts_rows += f"""
        <tr>
          <td>{i}</td>
          <td>{title_cell}</td>
          <td>{fmt_num(p["pv"])}</td>
          <td>{fmt_num(p["sessions"])}</td>
          <td>{fmt_num(p["gsc_clicks"])}</td>
        </tr>"""

    query_rows = ""
    for i, q in enumerate(top_queries, 1):
        query_rows += f"""
        <tr>
          <td>{i}</td>
          <td>{html.escape(q["query"])}</td>
          <td>{fmt_num(q["clicks"])}</td>
          <td>{fmt_num(q["impressions"])}</td>
          <td>{q["position"]:.1f}</td>
        </tr>"""

    chart_block = ""
    if ga4.get("available") and ga4.get("daily"):
        labels = [r["date"].isoformat() for r in ga4["daily"]]
        sessions = [r["sessions"] for r in ga4["daily"]]
        chart_block = f"""
        <h2>日次セッション</h2>
        <div class="chart-wrap"><canvas id="dailyChart" height="100"></canvas></div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
        <script>
        new Chart(document.getElementById('dailyChart'), {{
          type: 'line',
          data: {{
            labels: {json.dumps(labels, ensure_ascii=False)},
            datasets: [{{
              label: 'セッション',
              data: {json.dumps(sessions)},
              borderColor: '#2563eb',
              backgroundColor: 'rgba(37,99,235,0.12)',
              fill: true,
              tension: 0.25,
            }}]
          }},
          options: {{
            responsive: true,
            plugins: {{ legend: {{ display: false }} }},
            scales: {{ y: {{ beginAtZero: true }} }}
          }}
        }});
        </script>"""

    footer_links = [
        '<a href="ga4_wp_gsc_analysis.csv">ga4_wp_gsc_analysis.csv</a>',
        '<a href="ga4_wp_gsc_analysis_queries.csv">ga4_wp_gsc_analysis_queries.csv</a>',
    ]
    if has_summary_md:
        footer_links.append('<a href="summary.md">summary.md</a>')

    prev_note = ""
    if ga4.get("available"):
        prev_note = (
            f"前期比は GA4 サイト全体の {ga4['prev_start']} 〜 {ga4['prev_end']} と比較。"
        )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(SITE_NAME)} アクセスレポート ({start} 〜 {end})</title>
  <style>{base_css()}</style>
</head>
<body>
  <div class="container">
    <div class="nav"><a href="../../index.html">← Analytics ダッシュボード</a></div>
    <h1>{html.escape(SITE_NAME)} HP アクセスレポート</h1>
    <p class="meta">集計期間: {start} 〜 {end} ／ 生成: {generated}</p>

    <h2>サマリー</h2>
    <div class="cards">
      <div class="card">
        <div class="label">ページビュー（記事行合計）</div>
        <div class="value">{fmt_num(main_summary["total_pv"])}</div>
      </div>
      <div class="card">
        <div class="label">セッション（記事行合計）</div>
        <div class="value">{fmt_num(main_summary["total_sessions"])}</div>
      </div>
      <div class="card">
        <div class="label">エンゲージドセッション</div>
        <div class="value">{fmt_num(main_summary["total_engaged"])}</div>
      </div>
      <div class="card">
        <div class="label">GSC クリック</div>
        <div class="value">{fmt_num(main_summary["gsc_clicks"])}</div>
      </div>
      <div class="card">
        <div class="label">GSC インプレッション</div>
        <div class="value">{fmt_num(main_summary["gsc_impressions"])}</div>
      </div>
      <div class="card">
        <div class="label">GSC CTR</div>
        <div class="value">{main_summary["gsc_ctr"]:.2f}%</div>
      </div>
      {change_cards}
    </div>
    {f'<p class="meta">{html.escape(prev_note)}</p>' if prev_note else ''}

    {chart_block}

    <h2>記事 TOP10</h2>
    <table>
      <thead><tr><th>#</th><th>タイトル</th><th>PV</th><th>セッション</th><th>GSCクリック</th></tr></thead>
      <tbody>{posts_rows or '<tr><td colspan="5">データなし</td></tr>'}</tbody>
    </table>

    <h2>検索クエリ TOP10</h2>
    <table>
      <thead><tr><th>#</th><th>クエリ</th><th>クリック</th><th>インプレ</th><th>平均順位</th></tr></thead>
      <tbody>{query_rows or '<tr><td colspan="5">データなし</td></tr>'}</tbody>
    </table>

    <div class="footer">
      <p>データソース: GA4 / Google Search Console / WordPress</p>
      <p>CSV: {' / '.join(footer_links)}</p>
    </div>
  </div>
</body>
</html>
"""


def render_index_html(
    periods: list[dict[str, Any]],
    projects: list[dict[str, Any]],
    cumulative_top: list[dict[str, Any]],
    trend_notes: list[str],
) -> str:
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    latest = periods[-1] if periods else None

    rows = ""
    for p in periods:
        s = p["summary"]
        link = f"periodic/{p['name']}/index.html"
        rows += f"""
        <tr>
          <td><a href="{html.escape(link)}">{p['start']} 〜 {p['end']}</a></td>
          <td>{fmt_num(s['total_pv'])}</td>
          <td>{fmt_num(s['total_sessions'])}</td>
          <td>{fmt_num(s['gsc_clicks'])}</td>
          <td>{s['gsc_ctr']:.2f}%</td>
          <td>{fmt_pct_cell(p.get('prev_session_change'))}</td>
          <td>{fmt_pct_cell(p.get('prev_gsc_change'))}</td>
        </tr>"""

    chart_block = ""
    if len(periods) >= 2:
        labels = [f"{p['start']}" for p in periods]
        sessions = [p["summary"]["total_sessions"] for p in periods]
        pvs = [p["summary"]["total_pv"] for p in periods]
        gsc_clicks = [p["summary"]["gsc_clicks"] for p in periods]
        chart_block = f"""
        <h2>periodic 推移（記事行合計）</h2>
        <div class="chart-wrap"><canvas id="trendChart" height="120"></canvas></div>
        <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
        <script>
        new Chart(document.getElementById('trendChart'), {{
          type: 'line',
          data: {{
            labels: {json.dumps(labels, ensure_ascii=False)},
            datasets: [
              {{
                label: 'セッション',
                data: {json.dumps(sessions)},
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37,99,235,0.08)',
                tension: 0.25,
              }},
              {{
                label: 'PV',
                data: {json.dumps(pvs)},
                borderColor: '#059669',
                backgroundColor: 'rgba(5,150,105,0.08)',
                tension: 0.25,
              }},
              {{
                label: 'GSCクリック',
                data: {json.dumps(gsc_clicks)},
                borderColor: '#d97706',
                backgroundColor: 'rgba(217,119,6,0.08)',
                tension: 0.25,
              }},
            ]
          }},
          options: {{
            responsive: true,
            interaction: {{ mode: 'index', intersect: false }},
            scales: {{ y: {{ beginAtZero: true }} }}
          }}
        }});
        </script>"""

    notes_block = ""
    if trend_notes:
        items = "".join(f"<li>{html.escape(n)}</li>" for n in trend_notes)
        notes_block = f"""
        <h2>動向メモ</h2>
        <div class="notes"><ul>{items}</ul></div>"""

    cumulative_rows = ""
    for i, p in enumerate(cumulative_top, 1):
        title = html.escape(p["title"][:70] + ("…" if len(p["title"]) > 70 else ""))
        cumulative_rows += f"""
        <tr>
          <td>{i}</td>
          <td>{title}</td>
          <td>{fmt_num(p['total_pv'])}</td>
          <td>{p['top10_count']}</td>
        </tr>"""

    cumulative_block = ""
    if cumulative_top:
        cumulative_block = f"""
        <h2>記事の顔ぶれ（累積 PV TOP10）</h2>
        <table>
          <thead><tr><th>#</th><th>タイトル</th><th>累積PV</th><th>TOP10登場期数</th></tr></thead>
          <tbody>{cumulative_rows}</tbody>
        </table>"""

    project_rows = ""
    for proj in projects:
        name = proj["name"]
        readme_link = (
            f'<a href="projects/{html.escape(name)}/{html.escape(proj["readme"])}">README</a>'
        )
        extras = [readme_link]
        for xlsx in sorted(proj["dir"].glob("*.xlsx")):
            extras.append(
                f'<a href="projects/{html.escape(name)}/{html.escape(xlsx.name)}">xlsx</a>'
            )
        project_rows += f"""
        <tr>
          <td><a href="projects/{html.escape(name)}/index.html">{html.escape(name)}</a></td>
          <td>{html.escape(proj['description'])}</td>
          <td>{' / '.join(extras)}</td>
        </tr>"""

    projects_block = ""
    if project_rows:
        projects_block = f"""
        <h2>特派分析（projects）</h2>
        <table>
          <thead><tr><th>プロジェクト</th><th>概要</th><th>資料</th></tr></thead>
          <tbody>{project_rows}</tbody>
        </table>"""

    latest_block = ""
    if latest:
        latest_block = f"""
        <p><a href="periodic/{latest['name']}/index.html">最新レポート ({latest['start']} 〜 {latest['end']}) を開く</a></p>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(SITE_NAME)} Analytics ダッシュボード</title>
  <style>{base_css()}</style>
</head>
<body>
  <div class="container">
    <h1>{html.escape(SITE_NAME)} Analytics</h1>
    <p class="meta">定期レポート・動向分析 ／ 生成: {generated}</p>
    {latest_block}
    {notes_block}
    {chart_block}
    {cumulative_block}
    <h2>periodic レポート一覧</h2>
    <table>
      <thead>
        <tr>
          <th>期間</th><th>PV</th><th>セッション</th><th>GSCクリック</th><th>CTR</th>
          <th>前期比セッション</th><th>前期比GSC</th>
        </tr>
      </thead>
      <tbody>{rows or '<tr><td colspan="7">periodic データなし</td></tr>'}</tbody>
    </table>
    {projects_block}
    <div class="footer">
      <p>CSV が正データ。HTML は <code>generate_report_html.py</code> から再生成できます。</p>
      <p>定期取得: <code>bash Analytics/scripts/run_periodic.sh</code></p>
      <p><a href="README.md">README</a> / <a href="整理方針.md">整理方針</a></p>
    </div>
  </div>
</body>
</html>
"""


def md_to_html(text: str) -> str:
    if markdown2 is None:
        return f"<pre>{html.escape(text)}</pre>"
    return markdown2.markdown(text, extras=["tables", "fenced-code-blocks"])


def _project_extra_charts(name: str, project_dir: Path) -> tuple[str, str]:
    """Return (chart_html, extra_tables_html)."""
    charts = ""
    tables = ""

    if name == "2026-03_tv-redcode":
        hourly_path = project_dir / "ga4_hourly_sessions.csv"
        if hourly_path.exists():
            rows = load_main_csv(hourly_path)
            for r in rows:
                r["sessions"] = int(float(r.get("sessions") or 0))
            top = sorted(rows, key=lambda x: x["sessions"], reverse=True)[:15]
            labels = []
            for r in top:
                dt = r.get("datetime_parsed", "")
                if "T" in dt:
                    labels.append(dt.replace("T", " ")[:16])
                else:
                    labels.append(str(r.get("dateHour_raw", "")))
            data = [r["sessions"] for r in top]
            charts += f"""
            <h2>時間帯別セッション TOP15</h2>
            <div class="chart-wrap"><canvas id="hourlyChart" height="120"></canvas></div>
            <script>
            new Chart(document.getElementById('hourlyChart'), {{
              type: 'bar',
              data: {{
                labels: {json.dumps(labels, ensure_ascii=False)},
                datasets: [{{ label: 'セッション', data: {json.dumps(data)}, backgroundColor: '#2563eb' }}]
              }},
              options: {{ responsive: true, plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
            }});
            </script>"""

        gsc_path = project_dir / "gsc_queries_brand_contains_レッド.csv"
        if gsc_path.exists():
            qrows = [r for r in load_main_csv(gsc_path) if r.get("period") == "post"]
            qrows.sort(key=lambda r: int(float(r.get("clicks") or 0)), reverse=True)
            tr = ""
            for i, r in enumerate(qrows[:15], 1):
                tr += f"""<tr><td>{i}</td><td>{html.escape(r.get('query',''))}</td>
                <td>{fmt_num(int(float(r.get('clicks') or 0)))}</td>
                <td>{fmt_num(int(float(r.get('impressions') or 0)))}</td></tr>"""
            tables += f"""
            <h2>「レッド」含むクエリ（放映後）</h2>
            <table><thead><tr><th>#</th><th>クエリ</th><th>クリック</th><th>インプレ</th></tr></thead>
            <tbody>{tr}</tbody></table>"""

    elif name == "2026-03_search-barrier":
        monthly_path = project_dir / "gsc_monthly_site.csv"
        if monthly_path.exists():
            mrows = load_main_csv(monthly_path)
            labels = [r.get("month", "") for r in mrows]
            clicks = [int(float(r.get("clicks") or 0)) for r in mrows]
            imps = [int(float(r.get("impressions") or 0)) for r in mrows]
            charts += f"""
            <h2>月次 GSC 推移</h2>
            <div class="chart-wrap"><canvas id="monthlyChart" height="120"></canvas></div>
            <script>
            new Chart(document.getElementById('monthlyChart'), {{
              type: 'line',
              data: {{
                labels: {json.dumps(labels, ensure_ascii=False)},
                datasets: [
                  {{ label: 'クリック', data: {json.dumps(clicks)}, borderColor: '#2563eb', tension: 0.2 }},
                  {{ label: 'インプレッション', data: {json.dumps(imps)}, borderColor: '#059669', tension: 0.2 }},
                ]
              }},
              options: {{ responsive: true, scales: {{ y: {{ beginAtZero: true }} }} }}
            }});
            </script>"""

    return charts, tables


def render_project_html(project_dir: Path, name: str) -> str:
    readme_name = PROJECT_README.get(name, "README.md")
    readme_path = project_dir / readme_name
    if not readme_path.exists():
        raise FileNotFoundError(f"README が見つかりません: {readme_path}")

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = PROJECT_DESCRIPTIONS.get(name, name)
    body_md = readme_path.read_text(encoding="utf-8")
    body_html = md_to_html(body_md)
    chart_html, table_html = _project_extra_charts(name, project_dir)
    if chart_html:
        chart_html = (
            '<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>\n'
            + chart_html
        )

    file_links = [f'<a href="{html.escape(readme_name)}">{html.escape(readme_name)}</a>']
    for csv in sorted(project_dir.glob("*.csv")):
        file_links.append(f'<a href="{html.escape(csv.name)}">{html.escape(csv.name)}</a>')
    for xlsx in sorted(project_dir.glob("*.xlsx")):
        file_links.append(f'<a href="{html.escape(xlsx.name)}">{html.escape(xlsx.name)}</a>')

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} — {html.escape(SITE_NAME)}</title>
  <style>{base_css()}</style>
</head>
<body>
  <div class="container">
    <div class="nav"><a href="../../index.html">← Analytics ダッシュボード</a></div>
    <h1>{html.escape(title)}</h1>
    <p class="meta">projects/{html.escape(name)} ／ 生成: {generated}</p>
    {chart_html}
    {table_html}
    <div class="content">{body_html}</div>
    <div class="footer">
      <p>関連ファイル: {' / '.join(file_links)}</p>
    </div>
  </div>
</body>
</html>
"""


def generate_project_report(project_dir: Path) -> Path:
    name = project_dir.name
    if name not in PROJECT_README:
        raise ValueError(f"未対応のプロジェクト: {name}")
    out = project_dir / "index.html"
    out.write_text(render_project_html(project_dir, name), encoding="utf-8")
    return out


def generate_all_projects() -> list[Path]:
    outputs: list[Path] = []
    for item in discover_project_dirs():
        outputs.append(generate_project_report(item["dir"]))
    return outputs


def generate_period_report(report_dir: Path, start: date, end: date) -> Path:
    main_csv = report_dir / "ga4_wp_gsc_analysis.csv"
    query_csv = report_dir / "ga4_wp_gsc_analysis_queries.csv"
    if not main_csv.exists():
        raise FileNotFoundError(f"CSV が見つかりません: {main_csv}")

    main_summary = summarize_main_rows(load_main_csv(main_csv))
    top_queries = summarize_queries(load_queries_csv(query_csv))
    ga4 = fetch_ga4_context(start, end)
    html_text = render_period_html(report_dir, start, end, main_summary, top_queries, ga4)
    out = report_dir / "index.html"
    out.write_text(html_text, encoding="utf-8")
    return out


def generate_index() -> Path:
    periods = enrich_periods(discover_periodic_dirs())
    cumulative_top = compute_cumulative_top_posts(periods)
    trend_notes = generate_trend_notes(periods, cumulative_top)
    projects = discover_project_dirs()
    out = ANALYTICS / "index.html"
    out.write_text(
        render_index_html(periods, projects, cumulative_top, trend_notes),
        encoding="utf-8",
    )
    return out


def generate_all_periodic() -> list[Path]:
    outputs: list[Path] = []
    for item in discover_periodic_dirs():
        outputs.append(generate_period_report(item["dir"], item["start"], item["end"]))
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description="Analytics CSV から HTML レポートを生成")
    parser.add_argument("--dir", type=Path, help="periodic フォルダパス")
    parser.add_argument("--start", help="集計開始日 YYYY-MM-DD")
    parser.add_argument("--end", help="集計終了日 YYYY-MM-DD")
    parser.add_argument("--index", action="store_true", help="Analytics/index.html を生成")
    parser.add_argument("--all-periodic", action="store_true", help="periodic 配下を一括生成")
    parser.add_argument("--project", type=Path, help="projects フォルダパス")
    parser.add_argument("--all-projects", action="store_true", help="projects 配下を一括 HTML 化")
    args = parser.parse_args()

    if args.all_projects:
        paths = generate_all_projects()
        for p in paths:
            print(f"生成: {p}")
        return

    if args.project:
        project_dir = args.project if args.project.is_absolute() else ROOT / args.project
        out = generate_project_report(project_dir)
        print(f"生成: {out}")
        return

    if args.all_periodic:
        paths = generate_all_periodic()
        for p in paths:
            print(f"生成: {p}")
        idx = generate_index()
        print(f"生成: {idx}")
        return

    if args.index:
        idx = generate_index()
        print(f"生成: {idx}")
        return

    if not args.dir:
        parser.error("--dir が必要です（--index または --all-periodic を使う場合は不要）")

    report_dir = args.dir if args.dir.is_absolute() else ROOT / args.dir
    if args.start and args.end:
        start, end = _parse_date(args.start), _parse_date(args.end)
    else:
        parsed = parse_period_dir(report_dir.name)
        if not parsed:
            parser.error("期間は --start/--end か、フォルダ名 YYYY-MM-DD_YYYY-MM-DD で指定してください")
        start, end = parsed

    out = generate_period_report(report_dir, start, end)
    print(f"生成: {out}")


if __name__ == "__main__":
    main()

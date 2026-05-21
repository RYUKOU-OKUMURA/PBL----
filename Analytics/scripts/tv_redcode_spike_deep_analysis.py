#!/usr/bin/env python3
"""
TV放映（RedCode紹介）に伴うアクセス急増の深掘り分析。

GA4: 時間帯・ランディングページ・流入元/メディア・デバイス
GSC: 放映前後のクエリ・クリック・インプレッション比較、ブランド系クエリ
"""
from __future__ import annotations

import csv
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

try:
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        OrderBy,
        RunReportRequest,
    )
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print("必要: pip install google-analytics-data google-api-python-client google-auth", file=sys.stderr)
    raise SystemExit(1) from e


def _ga_client():
    prop_id = os.getenv("GA4_PROPERTY_ID", "").strip()
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    if not prop_id or not creds_path or not Path(creds_path).exists():
        print("GA4_PROPERTY_ID / GOOGLE_APPLICATION_CREDENTIALS を確認してください。", file=sys.stderr)
        raise SystemExit(2)
    creds = service_account.Credentials.from_service_account_file(creds_path)
    return BetaAnalyticsDataClient(credentials=creds), f"properties/{prop_id}"


def _gsc_service():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    site = os.getenv("GSC_SITE_URL", "").strip()
    if not site or not creds_path:
        raise RuntimeError("GSC_SITE_URL / credentials")
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    return build("searchconsole", "v1", credentials=creds), site


def run_ga4(
    client: BetaAnalyticsDataClient,
    prop: str,
    dimensions: list[str],
    metrics: list[str],
    start: date,
    end: date,
    limit: int = 100000,
    order_desc_metric: str | None = None,
) -> list[dict]:
    mets = [Metric(name=m) for m in metrics]
    dims = [Dimension(name=d) for d in dimensions]
    req = RunReportRequest(
        property=prop,
        dimensions=dims,
        metrics=mets,
        date_ranges=[DateRange(start_date=start.isoformat(), end_date=end.isoformat())],
        limit=limit,
    )
    if order_desc_metric:
        req.order_bys = [
            OrderBy(
                metric=OrderBy.MetricOrderBy(metric_name=order_desc_metric),
                desc=True,
            )
        ]
    resp = client.run_report(req)
    rows = []
    for row in resp.rows or []:
        dvals = [dv.value for dv in row.dimension_values]
        mvals = [float(mv.value) for mv in row.metric_values]
        rows.append({"dims": dvals, "metrics": mvals})
    return rows


def parse_date_hour(s: str) -> datetime:
    """GA4 dateHour: YYYYMMDDHH (プロパティのレポート用タイムゾーン)"""
    return datetime.strptime(s, "%Y%m%d%H")


def main() -> None:
    out_dir = ROOT / "Analytics" / "projects" / f"{date.today().strftime('%Y-%m')}_tv-redcode"
    out_dir.mkdir(parents=True, exist_ok=True)

    client, prop = _ga_client()

    # 分析ウィンドウ
    spike_start, spike_end = date(2026, 3, 17), date(2026, 3, 20)
    control_start, control_end = date(2026, 3, 10), date(2026, 3, 16)
    hourly_start, hourly_end = date(2026, 3, 15), date(2026, 3, 21)

    lines: list[str] = []
    lines.append("# TV放映に伴うアクセス急増 — データ深掘り\n")
    lines.append("※ GA4の `dateHour` は**プロパティのレポート用タイムゾーン**（多くの場合 JST）です。\n")

    # --- 1) 時間帯別セッション（放映日前後）---
    hourly_rows = run_ga4(
        client,
        prop,
        ["dateHour"],
        ["sessions", "screenPageViews", "totalUsers"],
        hourly_start,
        hourly_end,
    )
    hourly_path = out_dir / "ga4_hourly_sessions.csv"
    with open(hourly_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dateHour_raw", "datetime_parsed", "sessions", "screenPageViews", "totalUsers"])
        for r in sorted(hourly_rows, key=lambda x: x["dims"][0]):
            dh = r["dims"][0]
            try:
                dt = parse_date_hour(dh)
            except ValueError:
                dt = None
            w.writerow([dh, dt.isoformat() if dt else "", *r["metrics"]])
    lines.append("## 1. 時間帯別（放映日前後）\n")
    lines.append(f"- 出力: `{hourly_path.relative_to(ROOT)}`\n")

    # ピーク時間帯トップ15
    top_h = sorted(hourly_rows, key=lambda x: -x["metrics"][0])[:15]
    lines.append("### セッションが多かった時間帯 TOP15\n")
    lines.append("| dateHour | 解析時刻 | セッション | PV | ユーザー |")
    lines.append("|----------|----------|------------|-----|----------|")
    for r in top_h:
        dh = r["dims"][0]
        try:
            dt = parse_date_hour(dh)
            tstr = dt.strftime("%Y-%m-%d %H:00")
        except ValueError:
            tstr = "?"
        ses, pv, u = r["metrics"]
        lines.append(f"| {dh} | {tstr} | {int(ses):,} | {int(pv):,} | {int(u):,} |")
    lines.append("")

    # 日別に「何時が一番だったか」
    by_day: dict[str, list] = defaultdict(list)
    for r in hourly_rows:
        dh = r["dims"][0]
        if len(dh) >= 8:
            day = dh[:8]
            by_day[day].append(r)
    lines.append("### 日別のピーク時間帯\n")
    for day in sorted(by_day.keys()):
        best = max(by_day[day], key=lambda x: x["metrics"][0])
        dh = best["dims"][0]
        try:
            dt = parse_date_hour(dh)
            tstr = dt.strftime("%H:00")
        except ValueError:
            tstr = "?"
        lines.append(
            f"- `{day}`: 最大 **{int(best['metrics'][0]):,}** セッション（{tstr} 台）"
        )
    lines.append("")

    # --- 2) ランディングページ TOP（スパイク期 vs コントロール期）---
    def landing_top(start: date, end: date, label: str) -> Path:
        rows = run_ga4(
            client,
            prop,
            ["landingPage"],
            ["sessions", "newUsers", "engagedSessions", "averageSessionDuration"],
            start,
            end,
            limit=500,
            order_desc_metric="sessions",
        )
        path = out_dir / f"ga4_landing_pages_{label}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["landingPage", "sessions", "newUsers", "engagedSessions", "avgSessionDuration_sec"])
            for r in rows:
                lp = r["dims"][0]
                ses, nu, eng, avgd = r["metrics"]
                w.writerow([lp, int(ses), int(nu), int(eng), round(avgd, 2)])
        return path

    lp_spike = landing_top(spike_start, spike_end, "spike_0317_0320")
    lp_ctrl = landing_top(control_start, control_end, "control_0310_0316")
    lines.append("## 2. ランディングページ\n")
    lines.append(f"- スパイク期（3/17–3/20）: `{lp_spike.relative_to(ROOT)}`\n")
    lines.append(f"- 比較用 通常週（3/10–3/16）: `{lp_ctrl.relative_to(ROOT)}`\n")

    # スパイク期TOP10を表に
    spike_lp_rows = run_ga4(
        client,
        prop,
        ["landingPage"],
        ["sessions", "newUsers", "engagedSessions"],
        spike_start,
        spike_end,
        limit=15,
        order_desc_metric="sessions",
    )
    lines.append("### スパイク期（3/17–3/20）ランディング TOP15\n")
    lines.append("| landingPage | セッション | 新規ユーザー | エンゲージドSS |")
    lines.append("|-------------|------------|--------------|----------------|")
    for r in spike_lp_rows:
        lp = r["dims"][0][:80] + ("…" if len(r["dims"][0]) > 80 else "")
        ses, nu, eng = r["metrics"]
        lines.append(f"| {lp} | {int(ses):,} | {int(nu):,} | {int(eng):,} |")
    lines.append("")

    # --- 3) 流入ソース / メディア ---
    def source_medium(start: date, end: date, label: str) -> Path:
        rows = run_ga4(
            client,
            prop,
            ["sessionSource", "sessionMedium"],
            ["sessions", "engagedSessions"],
            start,
            end,
            limit=200,
            order_desc_metric="sessions",
        )
        path = out_dir / f"ga4_source_medium_{label}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["sessionSource", "sessionMedium", "sessions", "engagedSessions"])
            for r in rows:
                src, med = r["dims"][0], r["dims"][1]
                ses, eng = r["metrics"]
                w.writerow([src, med, int(ses), int(eng)])
        return path

    sm_spike = source_medium(spike_start, spike_end, "spike")
    sm_ctrl = source_medium(control_start, control_end, "control")
    lines.append("## 3. 流入ソース × メディア\n")
    lines.append(f"- スパイク期: `{sm_spike.relative_to(ROOT)}`\n")
    lines.append(f"- 通常週: `{sm_ctrl.relative_to(ROOT)}`\n")

    sm_spike_rows = run_ga4(
        client,
        prop,
        ["sessionSource", "sessionMedium"],
        ["sessions"],
        spike_start,
        spike_end,
        limit=20,
        order_desc_metric="sessions",
    )
    lines.append("### スパイク期 TOP20（source / medium）\n")
    lines.append("| source | medium | セッション |")
    lines.append("|--------|--------|------------|")
    for r in sm_spike_rows:
        src, med = r["dims"][0], r["dims"][1]
        lines.append(f"| {src} | {med} | {int(r['metrics'][0]):,} |")
    lines.append("")

    # --- 4) デバイス ---
    def devices(start: date, end: date, label: str) -> Path:
        rows = run_ga4(
            client,
            prop,
            ["deviceCategory"],
            ["sessions", "screenPageViews", "engagedSessions"],
            start,
            end,
            order_desc_metric="sessions",
        )
        path = out_dir / f"ga4_device_{label}.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["deviceCategory", "sessions", "screenPageViews", "engagedSessions"])
            for r in rows:
                dev = r["dims"][0]
                ses, pv, eng = r["metrics"]
                w.writerow([dev, int(ses), int(pv), int(eng)])
        return path

    dev_spike = devices(spike_start, spike_end, "spike")
    dev_ctrl = devices(control_start, control_end, "control")
    lines.append("## 4. デバイスカテゴリ\n")
    lines.append(f"- スパイク期: `{dev_spike.relative_to(ROOT)}`\n")
    lines.append(f"- 通常週: `{dev_ctrl.relative_to(ROOT)}`\n")

    # 構成比
    d_spike = run_ga4(
        client, prop, ["deviceCategory"], ["sessions"], spike_start, spike_end
    )
    total_ses = sum(r["metrics"][0] for r in d_spike) or 1
    lines.append("### スパイク期のデバイス構成比（セッション）\n")
    for r in sorted(d_spike, key=lambda x: -x["metrics"][0]):
        pct = r["metrics"][0] / total_ses * 100
        lines.append(f"- **{r['dims'][0]}**: {int(r['metrics'][0]):,}（{pct:.1f}%）")
    lines.append("")

    # --- 5) Search Console: 期間比較 + ブランドクエリ ---
    gsc_lines: list[str] = []
    try:
        gsc, site = _gsc_service()
    except RuntimeError:
        gsc, site = None, ""

    if gsc:
        def gsc_query(
            start: str,
            end: str,
            dims: list[str],
            row_limit: int = 500,
            dim_filter: dict | None = None,
        ) -> list:
            body: dict = {
                "startDate": start,
                "endDate": end,
                "dimensions": dims,
                "rowLimit": row_limit,
            }
            if dim_filter:
                body["dimensionFilterGroups"] = [dim_filter]
            return (
                gsc.searchanalytics()
                .query(siteUrl=site, body=body)
                .execute()
                .get("rows", [])
            )

        # 全体サマリ（日別は別リクエスト）
        pre = ("2026-02-22", "2026-03-07")
        post = ("2026-03-08", "2026-03-21")
        for label, (s, e) in [("放映前2週", pre), ("放映後2週", post)]:
            rows = gsc_query(s, e, ["query"], 1000)
            clicks = sum(x.get("clicks", 0) for x in rows)
            imps = sum(x.get("impressions", 0) for x in rows)
            gsc_lines.append(f"- **{label}**（{s}〜{e}）: クエリ行数 {len(rows)}, クリック合計 {clicks:,}, インプレッション合計 {imps:,}")

        # ブランド系（クエリに「レッド」含む）— API filter
        filt = {
            "filters": [
                {
                    "dimension": "query",
                    "operator": "contains",
                    "expression": "レッド",
                }
            ]
        }
        brand_pre = gsc_query(pre[0], pre[1], ["query"], 500, filt)
        brand_post = gsc_query(post[0], post[1], ["query"], 500, filt)
        bp_clicks_pre = sum(x.get("clicks", 0) for x in brand_pre)
        bp_imps_pre = sum(x.get("impressions", 0) for x in brand_pre)
        bp_clicks_post = sum(x.get("clicks", 0) for x in brand_post)
        bp_imps_post = sum(x.get("impressions", 0) for x in brand_post)

        gsc_path = out_dir / "gsc_queries_brand_contains_レッド.csv"
        with open(gsc_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["period", "query", "clicks", "impressions", "ctr", "position"])
            for x in brand_post:
                keys = x.get("keys", [])
                q = keys[0] if keys else ""
                w.writerow(
                    [
                        "post",
                        q,
                        x.get("clicks", 0),
                        x.get("impressions", 0),
                        x.get("ctr", 0),
                        x.get("position", 0),
                    ]
                )

        lines.append("## 5. Google Search Console（検索）\n")
        for gl in gsc_lines:
            lines.append(gl + "\n")
        lines.append("")
        lines.append("### 「レッド」を含むクエリ（放映前 vs 後）\n")
        lines.append(
            f"- 放映前: クリック **{bp_clicks_pre:,}**, インプレ **{bp_imps_pre:,}**（該当クエリ行 {len(brand_pre)}）"
        )
        lines.append(
            f"- 放映後: クリック **{bp_clicks_post:,}**, インプレ **{bp_imps_post:,}**（該当クエリ行 {len(brand_post)}）"
        )
        if bp_clicks_pre > 0:
            lines.append(
                f"- クリックの変化率: **{(bp_clicks_post - bp_clicks_pre) / bp_clicks_pre * 100:+.1f}%**"
            )
        lines.append(f"- 詳細CSV（放映後）: `{gsc_path.relative_to(ROOT)}`\n")

        # 放映後トップクエリ全体 TOP25
        top_q = gsc_query(post[0], post[1], ["query"], 25)
        lines.append("### 放映後2週の検索クエリ TOP25（クリック順）\n")
        lines.append("| クエリ | クリック | インプレ | 掲載順位 |")
        lines.append("|--------|----------|----------|----------|")
        for x in top_q[:25]:
            keys = x.get("keys", [])
            q = (keys[0] if keys else "")[:40]
            lines.append(
                f"| {q} | {x.get('clicks', 0)} | {x.get('impressions', 0)} | {x.get('position', 0):.1f} |"
            )
        lines.append("")
    else:
        lines.append("## 5. Search Console\n- スキップ（設定なし）\n")

    # --- 6) 解釈メモ（データに基づく）---
    lines.append("## 6. データから読み取れること（仮説ではなく観測）\n")
    lines.append(
        "- **時間帯**: 上記 `dateHour` のピークが、番組の放送時間帯と重なるかを対照できます。"
    )
    lines.append(
        "- **Direct比率**: 以前の分析どおりスパイク時はDirectが大きい場合、TV視聴後にURLを直接開いた・アプリ内ブラウザ・計測上Directになる経路が混ざりやすい、という説明と整合しやすいです。"
    )
    lines.append(
        "- **ランディング**: トップが `/` なら「院名・ブランドでサイトに来た」、特定記事なら「そのテーマで検索・シェアされた」などの読み分けができます。"
    )
    lines.append(
        "- **GSC**: 「レッド」を含むクエリのクリック・インプレが増えていれば、**検索でのブランド想起**も同時に起きている証拠になります。"
    )

    report_path = out_dir / "README_analysis.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"完了: {report_path}")
    print("\n" + "\n".join(lines))


if __name__ == "__main__":
    main()

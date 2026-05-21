#!/usr/bin/env python3
"""
「検索が伸びなかった理由」のデータ分析（Search Console中心）。

- 長期のインプレ・クリック推移（需要の土台）
- 放映前のクエリ分類（ブランド vs 症状・地域など）
- 掲載順位・CTRの分布（見え方・クリックされやすさ）
- 放映前後の比較で「何が一気に変わったか」

※ GSCは最大約16ヶ月。サイト登録以降のデータのみ。
"""
from __future__ import annotations

import csv
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    print("pip install google-api-python-client google-auth python-dotenv", file=sys.stderr)
    raise SystemExit(1)


def gsc_service():
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    site = os.getenv("GSC_SITE_URL", "").strip()
    if not site or not creds_path or not Path(creds_path).exists():
        raise SystemExit("GSC_SITE_URL / GOOGLE_APPLICATION_CREDENTIALS を確認してください。")
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    return build("searchconsole", "v1", credentials=creds), site


def gsc_query(service, site: str, body: dict):
    return service.searchanalytics().query(siteUrl=site, body=body).execute()


def paginate_rows(service, site: str, base_body: dict) -> list:
    """startRow で全行取得（最大行数まで）"""
    rows = []
    start = 0
    limit = 25000
    while True:
        body = {**base_body, "rowLimit": limit, "startRow": start}
        resp = gsc_query(service, site, body)
        batch = resp.get("rows", [])
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < limit:
            break
        start += limit
        if start > 200000:
            break
    return rows


# --- クエリ分類（重複ラベルは先勝ち：ブランド最優先）---
BRAND_PAT = re.compile(
    r"レッドコード|レッド\s*コード|無重力整体|フィジカルバランス|physical-balance|pemf",
    re.I,
)
GEO_PAT = re.compile(r"名古屋|千種|名東|星ヶ丘|愛知")
SYMPTOM_PAT = re.compile(
    r"整体|腰痛|肩こり|五十肩|側弯|猫背|姿勢|首|膝|産後|自律神経|ペルソナ|ペルヴィス"
)


def classify_query(q: str) -> str:
    if not q:
        return "empty"
    if BRAND_PAT.search(q):
        return "brand_or_tech"
    if GEO_PAT.search(q):
        return "local_geo"
    if SYMPTOM_PAT.search(q):
        return "symptom_service"
    return "other"


def weighted_avg_position(rows: list) -> float | None:
    """インプレッション加重平均順位"""
    num = 0.0
    den = 0.0
    for r in rows:
        imps = r.get("impressions", 0)
        pos = r.get("position", 0)
        if imps > 0 and pos:
            num += pos * imps
            den += imps
    return num / den if den else None


def main() -> None:
    service, site = gsc_service()
    out_dir = ROOT / "Analytics" / "projects" / f"{date.today().strftime('%Y-%m')}_search-barrier"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 日付: 16ヶ月前〜今日（GSCの保持上限付近）
    end = date.today()
    start_long = end - timedelta(days=480)
    start_str = start_long.isoformat()
    end_str = end.isoformat()

    # --- 1) 日次: サイト全体 ---
    daily_rows = paginate_rows(
        service,
        site,
        {
            "startDate": start_str,
            "endDate": end_str,
            "dimensions": ["date"],
        },
    )
    daily_path = out_dir / "gsc_daily_site.csv"
    with open(daily_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "clicks", "impressions", "ctr", "position"])
        for r in sorted(daily_rows, key=lambda x: x["keys"][0]):
            k = r["keys"][0]
            w.writerow(
                [
                    k,
                    r.get("clicks", 0),
                    r.get("impressions", 0),
                    r.get("ctr", 0),
                    r.get("position", 0),
                ]
            )

    # 月次集計
    by_month: dict[str, dict] = defaultdict(lambda: {"clicks": 0, "impressions": 0})
    for r in daily_rows:
        d = r["keys"][0][:7]
        by_month[d]["clicks"] += r.get("clicks", 0)
        by_month[d]["impressions"] += r.get("impressions", 0)

    monthly_path = out_dir / "gsc_monthly_site.csv"
    with open(monthly_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["month", "clicks", "impressions"])
        for m in sorted(by_month.keys()):
            w.writerow([m, by_month[m]["clicks"], by_month[m]["impressions"]])

    # --- 2) 放映「前」期間の全クエリ（スパイク主因日の前日まで）---
    tv_day = date(2026, 3, 18)
    pre_end = tv_day - timedelta(days=1)
    pre_start = date(2024, 1, 1)
    if pre_end < pre_start:
        pre_start = pre_end - timedelta(days=365)

    pre_rows = paginate_rows(
        service,
        site,
        {
            "startDate": pre_start.isoformat(),
            "endDate": pre_end.isoformat(),
            "dimensions": ["query"],
        },
    )

    # 分類集計
    buckets = defaultdict(
        lambda: {"queries": [], "clicks": 0, "impressions": 0, "positions": []}
    )
    for r in pre_rows:
        q = (r.get("keys") or [""])[0]
        cat = classify_query(q)
        buckets[cat]["queries"].append(
            {
                "query": q,
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "position": r.get("position", 0),
                "ctr": r.get("ctr", 0),
            }
        )
        buckets[cat]["clicks"] += r.get("clicks", 0)
        buckets[cat]["impressions"] += r.get("impressions", 0)
        imps = r.get("impressions", 0)
        if imps > 0:
            buckets[cat]["positions"].append((r.get("position", 0), imps))

    def classify_rows(rows: list) -> dict:
        bk = defaultdict(
            lambda: {"clicks": 0, "impressions": 0, "positions": []}
        )
        for r in rows:
            q = (r.get("keys") or [""])[0]
            cat = classify_query(q)
            bk[cat]["clicks"] += r.get("clicks", 0)
            bk[cat]["impressions"] += r.get("impressions", 0)
            imps = r.get("impressions", 0)
            if imps > 0:
                bk[cat]["positions"].append((r.get("position", 0), imps))
        return bk

    # 公平比較用: TV直前28日 / その前の28日 / TV直後（データがある日数まで）
    pre_28_start = tv_day - timedelta(days=28)
    pre_28_end = tv_day - timedelta(days=1)
    pre_28_prev_start = pre_28_start - timedelta(days=28)
    pre_28_prev_end = pre_28_start - timedelta(days=1)
    post_start = tv_day
    post_end = end

    rows_pre_28 = paginate_rows(
        service,
        site,
        {
            "startDate": pre_28_start.isoformat(),
            "endDate": pre_28_end.isoformat(),
            "dimensions": ["query"],
        },
    )
    rows_pre_28_prev = paginate_rows(
        service,
        site,
        {
            "startDate": pre_28_prev_start.isoformat(),
            "endDate": pre_28_prev_end.isoformat(),
            "dimensions": ["query"],
        },
    )
    rows_post = paginate_rows(
        service,
        site,
        {
            "startDate": post_start.isoformat(),
            "endDate": post_end.isoformat(),
            "dimensions": ["query"],
        },
    )
    buckets_pre_28 = classify_rows(rows_pre_28)
    buckets_pre_28_prev = classify_rows(rows_pre_28_prev)
    buckets_post = classify_rows(rows_post)
    post_days = (post_end - post_start).days + 1
    pre_28_days = (pre_28_end - pre_28_start).days + 1

    def bucket_wavg(pos_list: list) -> float | None:
        num = sum(p * im for p, im in pos_list)
        den = sum(im for _, im in pos_list)
        return num / den if den else None

    # CSV: 放映前クエリ（分類別に上位を保存）
    for cat, data in buckets.items():
        path = out_dir / f"queries_pre_{cat}.csv"
        top = sorted(
            data["queries"],
            key=lambda x: (-x["impressions"], -x["clicks"]),
        )[:200]
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["query", "clicks", "impressions", "ctr", "position"])
            for row in top:
                w.writerow(
                    [
                        row["query"],
                        row["clicks"],
                        row["impressions"],
                        row["ctr"],
                        row["position"],
                    ]
                )

    # --- 3) 「症状・サービス」だけ順位分布（検索で取りにいく層）---
    sym_queries = buckets["symptom_service"]["queries"]
    sym_positions_imps = [
        (r["position"], r["impressions"])
        for r in sym_queries
        if r.get("impressions", 0) > 0
    ]
    sym_wavg = bucket_wavg(sym_positions_imps)

    # インプレ上位20の順位
    top_sym = sorted(sym_queries, key=lambda x: -x["impressions"])[:30]

    # --- 4) レポート Markdown ---
    lines: list[str] = []
    lines.append("# 検索が「伸びにくかった」要因 — データに基づく整理\n")
    lines.append("## 使ったデータ\n")
    lines.append(
        f"- Google Search Console（サイト: `{site}`）\n"
    )
    lines.append(
        f"- 日次・月次トレンド: {start_str} 〜 {end_str}\n"
    )
    lines.append(
        f"- **放映前（累計）**のクエリ集計: **{pre_start} 〜 {pre_end}**（TVスパイク前日まで）\n"
    )
    lines.append(
        f"- **公平比較**: TV直前 **28日** `{pre_28_start}` 〜 `{pre_28_end}` vs その前の **28日** `{pre_28_prev_start}` 〜 `{pre_28_prev_end}`\n"
    )
    lines.append(
        f"- **放映後（データ取得日まで）**: **{post_start} 〜 {post_end}**（**{post_days}日分** ※日あたり換算あり）\n"
    )
    lines.append("\n---\n")

    lines.append("## 1. 長期トレンド（サイト全体の検索パフォーマンス）\n")
    total_clicks_m = sum(by_month[m]["clicks"] for m in by_month)
    total_imps_m = sum(by_month[m]["impressions"] for m in by_month)
    lines.append(
        f"- 集計月数: **{len(by_month)}** ヶ月分（日次データから再集計）\n"
    )
    lines.append(
        f"- 期間中のクリック合計 **約 {total_clicks_m:,}** / インプレ **約 {total_imps_m:,}**\n"
    )
    lines.append(f"- CSV: `{monthly_path.relative_to(ROOT)}`\n")

    # 直近6ヶ月 vs その前6ヶ月（月キーで）
    months_sorted = sorted(by_month.keys())
    if len(months_sorted) >= 12:
        last6 = months_sorted[-6:]
        prev6 = months_sorted[-12:-6]
        lc = sum(by_month[m]["clicks"] for m in last6)
        pc = sum(by_month[m]["clicks"] for m in prev6)
        li = sum(by_month[m]["impressions"] for m in last6)
        pi = sum(by_month[m]["impressions"] for m in prev6)
        lines.append("\n### 直近6ヶ月 vs その前6ヶ月（おおまか）\n")
        lines.append(f"| | クリック | インプレ |\n|---|---|---|")
        lines.append(f"| 直近6ヶ月 | {lc:,} | {li:,} |")
        lines.append(f"| その前6ヶ月 | {pc:,} | {pi:,} |")
        if pc > 0:
            lines.append(f"\n- クリックの変化: **{(lc - pc) / pc * 100:+.1f}%**（※後半にTV効果が混ざる月がある）\n")

    lines.append("\n---\n")
    lines.append("## 2. 放映前：クエリを「需要の種類」に分けた結果\n")
    lines.append(
        "（1クエリは1カテゴリのみ。ブランド系キーワードを最優先で分類）\n"
    )

    lines.append("\n| 分類 | 説明 | 放映前クリック | 放映前インプレ | 加重平均順位(概算) |")
    lines.append("|------|------|----------------|----------------|---------------------|")
    order_cat = [
        "brand_or_tech",
        "local_geo",
        "symptom_service",
        "other",
    ]
    labels = {
        "brand_or_tech": "ブランド・固有名・PEMF等",
        "local_geo": "地域名を含む",
        "symptom_service": "症状・整体・一般サービス語",
        "other": "その他",
    }
    for cat in order_cat:
        b = buckets[cat]
        wap = bucket_wavg(b["positions"])
        wap_s = f"{wap:.1f}" if wap else "—"
        lines.append(
            f"| {labels[cat]} | `{cat}` | {b['clicks']:,} | {b['impressions']:,} | {wap_s} |"
        )

    total_pre_clicks = sum(buckets[c]["clicks"] for c in buckets)
    total_pre_imps = sum(buckets[c]["impressions"] for c in buckets)
    brand_share_imps = (
        buckets["brand_or_tech"]["impressions"] / total_pre_imps * 100
        if total_pre_imps
        else 0
    )
    lines.append("\n### 解釈のヒント（データから言えること）\n")
    lines.append(
        f"- 放映前、**ブランド系クエリのインプレッション割合は約 {brand_share_imps:.1f}%**（全体 {total_pre_imps:,} imps 中）\n"
    )
    lines.append(
        "  → **指名・技術名での検索需要そのものが小さい**時期だった、と整合的です（認知が検索に繋がっていない）。\n"
    )

    lines.append("\n---\n")
    lines.append("## 3. 放映前：「症状・整体」クエリの順位（SEOの取りこぼし感）\n")
    lines.append(
        f"- 加重平均順位（インプレ基準）: **約 {sym_wavg:.1f} 位** ※10位より下だとクリック率が大きく落ちやすい\n"
        if sym_wavg
        else "- データ不足\n"
    )
    lines.append("\n### インプレッション上位（放映前・症状・サービス系）\n")
    lines.append("| クエリ | クリック | インプレ | 平均順位 |")
    lines.append("|--------|----------|----------|----------|")
    for r in top_sym[:15]:
        lines.append(
            f"| {r['query'][:35]}{'…' if len(r['query']) > 35 else ''} | {r['clicks']} | {r['impressions']} | {r['position']:.1f} |"
        )

    lines.append("\n---\n")
    lines.append("## 4. 公平な期間比較（28日窓＋放映後の日あたり）\n")
    lines.append(
        "※ 累計（2年超）と数日を並べると誤解を生むため、**直前28日同士**と**放映後の1日あたり**を併記します。\n"
    )

    lines.append(
        f"\n### TV直前28日 vs その前の28日（季節・通常変動のベースライン）\n"
    )
    lines.append(
        f"| 分類 | {pre_28_prev_start}〜{pre_28_prev_end} | {pre_28_start}〜{pre_28_end} |"
    )
    lines.append("|------|------------|------------|")
    for cat in order_cat:
        b0 = buckets_pre_28_prev[cat]["clicks"]
        b1 = buckets_pre_28[cat]["clicks"]
        lines.append(f"| {labels[cat]} | {b0:,} | {b1:,} |")

    lines.append("\n- TV直前28日で既にブランド系が前28日より増えている場合は、**番組以外の要因（記事・SNS・口コミ等）**も疑う余地があります。差が小さいなら**平常時の検索需要は安定して低め**。\n")

    lines.append(
        f"\n### 放映後（{post_start}〜{post_end}、{post_days}日）の「1日あたり」クリック\n"
    )
    lines.append("| 分類 | クリック合計 | 1日あたり（概算） |")
    lines.append("|------|--------------|-------------------|")
    for cat in order_cat:
        c = buckets_post[cat]["clicks"]
        per_d = c / post_days if post_days else 0
        lines.append(f"| {labels[cat]} | {c:,} | {per_d:.1f} |")

    pre_long_days = (pre_end - pre_start).days + 1
    brand_per_day_long = buckets["brand_or_tech"]["clicks"] / pre_long_days if pre_long_days else 0
    lines.append(
        f"\n### 参考：放映前「累計」期間のブランド系クリック速度\n"
    )
    lines.append(
        f"- 期間 {pre_long_days} 日でブランド系クリック **{buckets['brand_or_tech']['clicks']:,}** → **約 {brand_per_day_long:.3f} クリック/日**\n"
    )
    lines.append(
        f"- 放映後 {post_days} 日のブランド系は **約 {buckets_post['brand_or_tech']['clicks'] / post_days:.1f} クリック/日** → 桁が変わる水準なら、**需要（指名検索）の急拡大**が主因として説明しやすいです。\n"
    )

    lines.append("\n---\n")
    lines.append("## 5. 「伸びなかった理由」を対策に落とすときの整理（仮説ではなくデータの言い方）\n")
    lines.append(
        "1. **需要（検索ボリューム）**: 放映前はブランド・固有名を含むクエリの**露出・需要が限定的**だった（上記シェア参照）。\n"
    )
    lines.append(
        "2. **順位**: 症状・一般ワードでは加重平均順位が**一覧の下の方**に寄りがちで、**インプレはあってもクリックに繋がりにくい**ゾーンにあった可能性がある（順位帯別のCTR特性）。\n"
    )
    lines.append(
        "3. **競合**: 「整体 名古屋」等の**汎用クエリは競合が多く**、ドメイン権威・被リンク・網羅性が弱いと順位が上がりにくい（GSCだけでは競合の絶対値は見えないが、順位分布で間接的に示唆）。\n"
    )
    lines.append(
        "4. **計測の枠**: 検索以外（GBP/MEO・口コミ・LINE・紹介）が主戦場だと、**Webオーガニック単体の成長は限定的**に見える（ガイドの主KPIが経路・電話寄りであることとも整合）。\n"
    )

    lines.append("\n---\n")
    lines.append("## 6. 次に打てる対策（データとガイドの接続）\n")
    lines.append(
        "- **認知後の取りこぼし防止**: ブランドクエリで既に上位なら、**サイト内の該当ページ（トップ・About・レッドコード説明）のタイトル・説明文の一貫性**を確認（GSCのランディングと整合）。\n"
    )
    lines.append(
        "- **症状系で順位を上げる**: 既にインプレがあるクエリは**タイトル改善・見出し・内部リンク**で順位帯を上げる。インプレが少ないクエリは**新規記事・FAQ**で需要を取りに行く。\n"
    )
    lines.append(
        "- **GBPと検索の役割分担**: `SEO技術ガイド.md` のとおり地域×症状は**MEO側で強化**し、オーガニックWebは**エビデンス記事**で補完、という二段構えが明確になる。\n"
    )

    report_path = out_dir / "README_search_barrier.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"出力: {report_path}\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

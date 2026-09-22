#!/usr/bin/env python3
"""
GA4 × WordPress × Search Console 統合分析スクリプト

記事内容とアクセス数の相関、キーワードSEO効果を測定する。
- GA4: ページ別PV・セッション
- WordPress: 記事メタデータ（タイトル・タグ・スラッグ）
- Search Console: 検索クエリ・インプレッション・クリック

URL構造: https://physical-balance-lab.com/1714/ （パス = 投稿ID）
"""

import argparse
import csv
import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

_SCRIPTS_DIR = Path(__file__).resolve().parent / "Analytics" / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
try:
    from period_window import is_exact_calendar_half
except ImportError:
    is_exact_calendar_half = None  # type: ignore[assignment]

# オプショナルインポート（未インストール時は該当機能をスキップ）
try:
    from google.oauth2 import service_account
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    service_account = None

try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange,
        Dimension,
        Metric,
        RunReportRequest,
    )
    GA4_AVAILABLE = True
except ImportError:
    GA4_AVAILABLE = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GSC_AVAILABLE = True
except ImportError:
    GSC_AVAILABLE = False

# WordPress 取得は requests のみで実装（post_to_wp への依存を避ける）
try:
    import requests
    from requests.auth import HTTPBasicAuth
    WP_AVAILABLE = True
except ImportError:
    WP_AVAILABLE = False
    requests = None

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


# =============================================================================
# 設定読み込み（オプショナルキー対応）
# =============================================================================

def load_analysis_config() -> Dict[str, Any]:
    """
    分析用の設定を読み込む。WP/GA4/GSC はそれぞれオプショナル。
    """
    load_dotenv()
    config = {}

    # WordPress（post_to_wp の load_config を使う場合は必須チェックしない）
    for key in ["WP_URL", "WP_USER", "WP_APP_PASSWORD"]:
        v = os.getenv(key)
        config[key] = v.strip() if v else None
    if config.get("WP_URL"):
        config["WP_URL"] = config["WP_URL"].rstrip("/")

    # GA4
    config["GA4_PROPERTY_ID"] = os.getenv("GA4_PROPERTY_ID", "").strip()
    config["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", ""
    ).strip()

    # Search Console（GA4と同じサービスアカウントを利用可能）
    config["GSC_SITE_URL"] = os.getenv("GSC_SITE_URL", "").strip()
    if not config["GSC_SITE_URL"] and config.get("WP_URL"):
        # WP_URL からデフォルト設定（例: https://physical-balance-lab.com）
        config["GSC_SITE_URL"] = config["WP_URL"].replace("/wp", "").rstrip("/")

    return config


# =============================================================================
# WordPress 記事取得
# =============================================================================

def fetch_wp_posts_inline(
    config: Dict[str, Any],
    per_page: int = 100,
    status: str = "publish",
) -> List[Dict[str, Any]]:
    """WordPress REST API から投稿一覧を取得。"""
    endpoint = f"{config['WP_URL']}/wp-json/wp/v2/posts"
    fields = ["id", "title", "slug", "link", "date", "modified", "tags", "categories", "excerpt"]
    all_posts = []
    page = 1

    while True:
        params = {
            "status": status,
            "per_page": per_page,
            "page": page,
            "_fields": ",".join(fields),
        }
        try:
            response = requests.get(
                endpoint,
                params=params,
                auth=HTTPBasicAuth(config["WP_USER"], config["WP_APP_PASSWORD"]),
                timeout=30,
            )
        except Exception as e:
            logger.error(f"WordPress 取得エラー: {e}")
            break

        if response.status_code != 200:
            logger.warning(f"WordPress API エラー [{response.status_code}]")
            break

        posts = response.json()
        if not posts:
            break
        all_posts.extend(posts)
        if len(posts) < per_page:
            break
        page += 1

    logger.info(f"WordPress から {len(all_posts)} 件の投稿を取得しました")
    return all_posts


def get_wp_posts(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """WordPress から公開記事一覧を取得。"""
    if not WP_AVAILABLE:
        logger.warning("requests が未インストールです。pip install requests")
        return []

    wp_keys = ["WP_URL", "WP_USER", "WP_APP_PASSWORD"]
    if not all(config.get(k) for k in wp_keys):
        logger.warning("WordPress 設定が不足しています。WP_URL, WP_USER, WP_APP_PASSWORD を .env に設定してください。")
        return []

    return fetch_wp_posts_inline(config, per_page=100, status="publish")


# =============================================================================
# GA4 データ取得
# =============================================================================

def _extract_path_id(path: str) -> Optional[str]:
    """
    GA4 pagePath または URL パスから投稿IDを抽出。
    https://physical-balance-lab.com/1714/ → 1714
    /1714/ または /1714 → 1714
    """
    path = (path or "").strip().rstrip("/")
    if not path:
        return None
    parts = [p for p in path.split("/") if p]
    if not parts:
        return None
    last = parts[-1]
    if last.isdigit():
        return last
    return None


def fetch_ga4_page_report(
    config: Dict[str, Any],
    start_date: str,
    end_date: str,
) -> List[Dict[str, Any]]:
    """
    GA4 からページ別の screenPageViews, sessions を取得。
    """
    if not GA4_AVAILABLE or not OAUTH_AVAILABLE or service_account is None:
        logger.warning("google-analytics-data と google-auth が未インストールです。pip install google-analytics-data google-auth")
        return []

    prop_id = config.get("GA4_PROPERTY_ID")
    creds_path = config.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not prop_id or not creds_path:
        logger.warning("GA4_PROPERTY_ID または GOOGLE_APPLICATION_CREDENTIALS が未設定です。")
        return []

    if not Path(creds_path).exists():
        logger.warning(f"認証ファイルが見つかりません: {creds_path}")
        return []

    try:
        credentials = service_account.Credentials.from_service_account_file(creds_path)
        client = BetaAnalyticsDataClient(credentials=credentials)
        property_id = f"properties/{prop_id}"

        request = RunReportRequest(
            property=property_id,
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="sessions"),
                Metric(name="averageSessionDuration"),
                Metric(name="engagedSessions"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        response = client.run_report(request)

        rows = []
        for row in response.rows:
            path = row.dimension_values[0].value if row.dimension_values else ""
            metrics = row.metric_values
            rows.append({
                "pagePath": path,
                "path_id": _extract_path_id(path),
                "screenPageViews": int(metrics[0].value) if len(metrics) > 0 else 0,
                "sessions": int(metrics[1].value) if len(metrics) > 1 else 0,
                "averageSessionDuration": float(metrics[2].value) if len(metrics) > 2 else 0,
                "engagedSessions": int(metrics[3].value) if len(metrics) > 3 else 0,
            })
        logger.info(f"GA4 から {len(rows)} 件のページデータを取得しました")
        return rows
    except Exception as e:
        logger.error(f"GA4 取得エラー: {e}")
        return []


# =============================================================================
# Search Console データ取得
# =============================================================================

def fetch_gsc_search_analytics(
    config: Dict[str, Any],
    start_date: str,
    end_date: str,
    dimensions: Optional[List[str]] = None,
    row_limit: int = 1000,
) -> List[Dict[str, Any]]:
    """
    Search Console から検索分析データを取得。
    dimensions: ['query'], ['page'], または ['query', 'page']
    """
    if not GSC_AVAILABLE or not OAUTH_AVAILABLE or service_account is None:
        logger.warning("google-api-python-client と google-auth が未インストールです。pip install google-api-python-client google-auth")
        return []

    site_url = config.get("GSC_SITE_URL")
    creds_path = config.get("GOOGLE_APPLICATION_CREDENTIALS")
    if not site_url or not creds_path:
        logger.warning("GSC_SITE_URL または GOOGLE_APPLICATION_CREDENTIALS が未設定です。")
        return []

    if not Path(creds_path).exists():
        logger.warning(f"認証ファイルが見つかりません: {creds_path}")
        return []

    if dimensions is None:
        dimensions = ["query", "page"]

    try:
        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=credentials)

        request = {
            "startDate": start_date,
            "endDate": end_date,
            "rowLimit": row_limit,
        }
        if dimensions:
            request["dimensions"] = dimensions
        response = service.searchanalytics().query(siteUrl=site_url, body=request).execute()

        rows = []
        for row in response.get("rows", []):
            keys = row.get("keys", [])
            r = {
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": row.get("ctr", 0),
                "position": row.get("position", 0),
            }
            if dimensions and "query" in dimensions:
                idx = dimensions.index("query")
                r["query"] = keys[idx] if idx < len(keys) else ""
            if dimensions and "page" in dimensions:
                idx = dimensions.index("page")
                page_url = keys[idx] if idx < len(keys) else ""
                r["page"] = page_url
                r["path_id"] = _extract_path_id(urlparse(page_url).path)
            rows.append(r)
        logger.info(f"Search Console から {len(rows)} 件のデータを取得しました")
        return rows
    except HttpError as e:
        logger.error(f"Search Console API エラー: {e}")
        return []
    except Exception as e:
        logger.error(f"Search Console 取得エラー: {e}")
        return []


# =============================================================================
# マージ・出力
# =============================================================================

def merge_and_output(
    wp_posts: List[Dict[str, Any]],
    ga4_rows: List[Dict[str, Any]],
    gsc_rows: List[Dict[str, Any]],
    output_path: str,
    output_format: str = "csv",
) -> None:
    """
    WordPress / GA4 / GSC をマージして出力。
    URL構造: https://physical-balance-lab.com/1714/ → パスID で照合。
    """
    # WP を id でインデックス
    wp_by_id = {str(p["id"]): p for p in wp_posts}

    # GA4 を path_id で集約
    ga4_by_id: Dict[str, Dict] = {}
    for r in ga4_rows:
        pid = r.get("path_id")
        if not pid:
            continue
        if pid not in ga4_by_id:
            ga4_by_id[pid] = {
                "screenPageViews": 0,
                "sessions": 0,
                "averageSessionDuration": 0,
                "engagedSessions": 0,
            }
        ga4_by_id[pid]["screenPageViews"] += r.get("screenPageViews", 0)
        ga4_by_id[pid]["sessions"] += r.get("sessions", 0)
        ga4_by_id[pid]["averageSessionDuration"] = max(
            ga4_by_id[pid]["averageSessionDuration"],
            r.get("averageSessionDuration", 0),
        )
        ga4_by_id[pid]["engagedSessions"] += r.get("engagedSessions", 0)

    # GSC を path_id で集約（クエリは別扱い）
    gsc_by_page: Dict[str, List[Dict]] = {}
    gsc_agg_by_id: Dict[str, Dict] = {}
    for r in gsc_rows:
        pid = r.get("path_id")
        if not pid:
            continue
        if pid not in gsc_by_page:
            gsc_by_page[pid] = []
            gsc_agg_by_id[pid] = {"clicks": 0, "impressions": 0}
        gsc_by_page[pid].append(r)
        gsc_agg_by_id[pid]["clicks"] += r.get("clicks", 0)
        gsc_agg_by_id[pid]["impressions"] += r.get("impressions", 0)

    # マージ
    merged = []
    for pid, wp in wp_by_id.items():
        row = {
            "post_id": pid,
            "title": wp.get("title", {}).get("rendered", wp.get("title", "")),
            "slug": wp.get("slug", ""),
            "link": wp.get("link", ""),
            "date": wp.get("date", ""),
            "screenPageViews": ga4_by_id.get(pid, {}).get("screenPageViews", 0),
            "sessions": ga4_by_id.get(pid, {}).get("sessions", 0),
            "engagedSessions": ga4_by_id.get(pid, {}).get("engagedSessions", 0),
            "gsc_clicks": gsc_agg_by_id.get(pid, {}).get("clicks", 0),
            "gsc_impressions": gsc_agg_by_id.get(pid, {}).get("impressions", 0),
        }
        merged.append(row)

    # GA4 にあって WP にないページも追加
    for pid in ga4_by_id:
        if pid not in wp_by_id:
            merged.append({
                "post_id": pid,
                "title": "",
                "slug": "",
                "link": "",
                "date": "",
                "screenPageViews": ga4_by_id[pid]["screenPageViews"],
                "sessions": ga4_by_id[pid]["sessions"],
                "engagedSessions": ga4_by_id[pid]["engagedSessions"],
                "gsc_clicks": gsc_agg_by_id.get(pid, {}).get("clicks", 0),
                "gsc_impressions": gsc_agg_by_id.get(pid, {}).get("impressions", 0),
            })

    # ソート（PV降順）
    merged.sort(key=lambda x: x.get("screenPageViews", 0), reverse=True)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "json":
        with open(out, "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON 出力: {out}")
    else:
        if not merged:
            logger.warning("出力データがありません")
            return
        with open(out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=merged[0].keys())
            w.writeheader()
            w.writerows(merged)
        logger.info(f"CSV 出力: {out}")

    # GSC クエリ別データを別ファイルで出力（オプション）
    if gsc_rows and "query" in (gsc_rows[0] if gsc_rows else {}):
        query_out = out.parent / f"{out.stem}_queries.csv"
        with open(query_out, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["query", "page", "path_id", "clicks", "impressions", "ctr", "position"])
            w.writeheader()
            for r in gsc_rows:
                w.writerow({
                    "query": r.get("query", ""),
                    "page": r.get("page", ""),
                    "path_id": r.get("path_id", ""),
                    "clicks": r.get("clicks", 0),
                    "impressions": r.get("impressions", 0),
                    "ctr": r.get("ctr", 0),
                    "position": r.get("position", 0),
                })
        logger.info(f"クエリ別 CSV 出力: {query_out}")


def write_gsc_aggregates(
    config: Dict[str, Any],
    start_date: str,
    end_date: str,
    output_dir: Path,
) -> None:
    """
    クエリ×ページ API では落ちるサイト全体・ページ単位の GSC を別ファイルに残す。
    """
    site_rows = fetch_gsc_search_analytics(config, start_date, end_date, dimensions=[])
    site_path = output_dir / "gsc_site.csv"
    with site_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["window_start", "window_end", "clicks", "impressions", "ctr", "position"],
        )
        w.writeheader()
        r = site_rows[0] if site_rows else {}
        w.writerow(
            {
                "window_start": start_date,
                "window_end": end_date,
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0),
                "position": r.get("position", 0),
            }
        )
    logger.info(f"GSC サイト合計 CSV 出力: {site_path}")

    page_rows = fetch_gsc_search_analytics(
        config, start_date, end_date, dimensions=["page"]
    )
    page_path = output_dir / "gsc_pages.csv"
    with page_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["page", "path_id", "clicks", "impressions", "ctr", "position"],
        )
        w.writeheader()
        for row in page_rows:
            w.writerow(
                {
                    "page": row.get("page", ""),
                    "path_id": row.get("path_id", ""),
                    "clicks": row.get("clicks", 0),
                    "impressions": row.get("impressions", 0),
                    "ctr": row.get("ctr", 0),
                    "position": row.get("position", 0),
                }
            )
    logger.info(f"GSC ページ別 CSV 出力: {page_path}")


def default_periodic_dir(start: str, end: str) -> Path:
    """カレンダー半月と一致するときだけ periodic 直下。それ以外は ad-hoc。"""
    if is_exact_calendar_half and is_exact_calendar_half(start, end):
        return Path("Analytics") / "periodic" / f"{start}_{end}"
    return Path("Analytics") / "periodic" / "ad-hoc" / f"{start}_{end}"


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="GA4 × WordPress × Search Console 統合分析"
    )
    parser.add_argument(
        "--start",
        default=(datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d"),
        help="集計開始日 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="集計終了日 (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="出力ファイルパス（--output-dir 未指定時のみ。未指定ならカレンダー半月は periodic、それ以外は ad-hoc）",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        help="出力先フォルダを指定（メインCSV・クエリCSVの両方をこのフォルダに保存）",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="CSV 出力後に index.html を生成する",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="出力形式",
    )
    parser.add_argument(
        "--wp-only",
        action="store_true",
        help="WordPress のみ取得（GA4/GSC はスキップ）",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細ログ",
    )
    args = parser.parse_args()

    output_dir: Optional[Path] = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
    elif args.output is None:
        output_dir = default_periodic_dir(args.start, args.end)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        ext = "json" if args.format == "json" else "csv"
        output_path = str(output_dir / f"ga4_wp_gsc_analysis.{ext}")
    else:
        output_path = args.output or "Analytics/ga4_wp_gsc_analysis.csv"

    setup_logging(verbose=args.verbose)
    config = load_analysis_config()

    wp_posts = get_wp_posts(config)
    ga4_rows = [] if args.wp_only else fetch_ga4_page_report(config, args.start, args.end)
    gsc_rows = [] if args.wp_only else fetch_gsc_search_analytics(config, args.start, args.end)

    merge_and_output(wp_posts, ga4_rows, gsc_rows, output_path, args.format)

    if output_dir is not None and not args.wp_only and args.format == "csv":
        write_gsc_aggregates(config, args.start, args.end, output_dir)

    if args.html and output_dir is not None:
        script = Path(__file__).resolve().parent / "Analytics" / "scripts" / "generate_report_html.py"
        cmd = [
            sys.executable,
            str(script),
            "--dir",
            str(output_dir),
            "--start",
            args.start,
            "--end",
            args.end,
        ]
        logger.info("HTML レポート生成: %s", " ".join(cmd))
        subprocess.run(cmd, check=True)
        index_script = script
        subprocess.run(
            [sys.executable, str(index_script), "--index"],
            check=True,
        )


if __name__ == "__main__":
    main()

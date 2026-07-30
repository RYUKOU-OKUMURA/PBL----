#!/usr/bin/env python3
"""Bulk refresh: internal links + 612 body rewrite for published posts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from requests.auth import HTTPBasicAuth

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from post_to_wp import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parent
LINK_MANIFEST = ROOT / "link_manifest.json"
BODY_612 = ROOT / "612_body_rewrite.html"
BACKUP_DIR = ROOT / "backups"
QA_DIR = ROOT / "qa_preview"
PLAN_PATH = ROOT / "rollout_plan.json"

LINE_MARKERS = (
    "<p>公式LINEから24時間受け付けてます！",
    '<div class="q_button_wrap">',
)


class RolloutError(RuntimeError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def wp_auth(config: dict[str, str]) -> HTTPBasicAuth:
    return HTTPBasicAuth(config["WP_USER"], config["WP_APP_PASSWORD"])


def fetch_post(config: dict[str, str], post_id: int) -> dict[str, Any]:
    response = requests.get(
        f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
        params={"context": "edit"},
        auth=wp_auth(config),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def render_related(links: list[dict[str, Any]]) -> str:
    items = []
    for link in links:
        pid = int(link["id"])
        title = link["title"]
        items.append(
            f'<li><a href="https://physical-balance-lab.com/{pid}/">{title}</a></li>'
        )
    return "<h2>関連記事</h2>\n<ul>\n" + "\n".join(items) + "\n</ul>\n"


def merge_links(existing: list[dict[str, Any]], new_links: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = {int(x["id"]) for x in existing}
    merged = list(existing)
    for link in new_links:
        pid = int(link["id"])
        if pid not in seen:
            merged.append(link)
            seen.add(pid)
    return merged


def parse_related_block(content: str) -> tuple[str | None, list[dict[str, Any]]]:
    match = re.search(r"<h2>\s*関連記事\s*</h2>\s*<ul>(.*?)</ul>", content, re.I | re.S)
    if not match:
        return None, []
    block = match.group(0)
    links = []
    for href, title in re.findall(
        r'<li><a href="https://physical-balance-lab.com/(\d+)/">(.*?)</a></li>',
        block,
        re.S,
    ):
        links.append({"id": int(href), "title": re.sub(r"\s+", " ", title).strip()})
    return block, links


def insert_before_line_cta(content: str, block: str) -> str:
    for marker in LINE_MARKERS:
        idx = content.find(marker)
        if idx != -1:
            return content[:idx] + block + "\n\n" + content[idx:]
    return content + "\n\n" + block


def apply_internal_links(content: str, spec: dict[str, Any]) -> str:
    links = spec["links"]
    mode = spec["mode"]
    if mode == "insert_related":
        if "関連記事" in content:
            old_block, existing = parse_related_block(content)
            if old_block:
                links = merge_links(existing, links)
                content = content.replace(old_block, render_related(links).strip())
                return content
        return insert_before_line_cta(content, render_related(links))
    if mode == "merge_related":
        old_block, existing = parse_related_block(content)
        merged = merge_links(existing, links)
        new_block = render_related(merged).strip()
        if old_block:
            return content.replace(old_block, new_block)
        return insert_before_line_cta(content, render_related(merged))
    raise RolloutError(f"Unknown link mode: {mode}")


def apply_612_rewrite(content: str, rewrite_html: str) -> str:
    marker = "<h2>そもそもなんで肩こり・首こりになるの？</h2>"
    idx = content.find(marker)
    if idx == -1:
        raise RolloutError("612: h2 marker not found")
    body = rewrite_html.strip()
    for cut in LINE_MARKERS:
        pos = body.find(cut)
        if pos != -1:
            body = body[:pos].rstrip()
            break
    tail_markers = list(LINE_MARKERS)
    tail_idx = len(content)
    for tm in tail_markers:
        pos = content.find(tm, idx)
        if pos != -1:
            tail_idx = min(tail_idx, pos)
    footer = content[tail_idx:]
    return content[:idx] + body + "\n\n" + footer


def expected_content(post_id: int, raw: str, link_manifest: dict[str, Any]) -> str:
    updated = raw
    key = str(post_id)
    if key in link_manifest.get("posts", {}):
        updated = apply_internal_links(updated, link_manifest["posts"][key])
    if post_id == 612:
        updated = apply_612_rewrite(updated, BODY_612.read_text(encoding="utf-8"))
        updated = updated.replace(
            "愛知、名古屋で脊柱側弯症治療なら『レッドコード整体』",
            "愛知・名古屋で首や肩の不調でお困りの方は、お気軽にご相談ください",
        )
    return updated


def backup_post(post_id: int, post: dict[str, Any]) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": post_id,
        "title": post["title"]["raw"],
        "excerpt": post.get("excerpt", {}).get("raw", ""),
        "content_raw": post["content"]["raw"],
        "status": post["status"],
        "slug": post["slug"],
    }
    write_json(BACKUP_DIR / f"{post_id}.json", payload)


def command_plan(config: dict[str, str]) -> None:
    link_manifest = read_json(LINK_MANIFEST)
    post_ids = sorted({int(k) for k in link_manifest["posts"]} | {612})
    plan = {"posts": {}, "qa_files": {}}
    for post_id in post_ids:
        post = fetch_post(config, post_id)
        backup_post(post_id, post)
        raw = post["content"]["raw"]
        expected = expected_content(post_id, raw, link_manifest)
        plan["posts"][str(post_id)] = {
            "baseline_sha256": sha256_text(raw),
            "expected_sha256": sha256_text(expected),
            "status": post["status"],
        }
        QA_DIR.mkdir(parents=True, exist_ok=True)
        qa_path = QA_DIR / f"{post_id}_qa.md"
        qa_path.write_text(
            f"# Post {post_id}\n\n## Content\n\n{expected}\n",
            encoding="utf-8",
        )
        plan["qa_files"][str(post_id)] = str(qa_path)
        print(f"PLANNED post={post_id} qa={qa_path}")
    write_json(PLAN_PATH, plan)
    print(f"PLAN={PLAN_PATH}")


def command_apply(config: dict[str, str]) -> None:
    link_manifest = read_json(LINK_MANIFEST)
    plan = read_json(PLAN_PATH)
    post_ids = sorted({int(k) for k in plan["posts"]})
    touched: list[int] = []
    try:
        for post_id in post_ids:
            backup = read_json(BACKUP_DIR / f"{post_id}.json")
            current = fetch_post(config, post_id)
            if sha256_text(current["content"]["raw"]) != plan["posts"][str(post_id)]["baseline_sha256"]:
                raise RolloutError(f"post {post_id}: baseline changed since plan")
            expected = expected_content(post_id, backup["content_raw"], link_manifest)
            if sha256_text(expected) != plan["posts"][str(post_id)]["expected_sha256"]:
                raise RolloutError(f"post {post_id}: expected hash mismatch")
            response = requests.post(
                f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                json={"content": expected},
                auth=wp_auth(config),
                timeout=60,
            )
            response.raise_for_status()
            updated = fetch_post(config, post_id)
            if sha256_text(updated["content"]["raw"]) != sha256_text(expected):
                raise RolloutError(f"post {post_id}: apply verification failed")
            touched.append(post_id)
            print(f"UPDATED post={post_id}")
        command_verify(config)
    except Exception:
        for post_id in reversed(touched):
            backup = read_json(BACKUP_DIR / f"{post_id}.json")
            requests.post(
                f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                json={"content": backup["content_raw"]},
                auth=wp_auth(config),
                timeout=60,
            ).raise_for_status()
            print(f"ROLLED_BACK post={post_id}", file=sys.stderr)
        raise


def command_verify(config: dict[str, str]) -> None:
    link_manifest = read_json(LINK_MANIFEST)
    plan = read_json(PLAN_PATH)
    for post_id, meta in plan["posts"].items():
        pid = int(post_id)
        backup = read_json(BACKUP_DIR / f"{pid}.json")
        expected = expected_content(pid, backup["content_raw"], link_manifest)
        current = fetch_post(config, pid)
        if current["status"] != meta["status"]:
            raise RolloutError(f"post {pid}: status changed")
        if sha256_text(current["content"]["raw"]) != sha256_text(expected):
            raise RolloutError(f"post {pid}: content mismatch")
        public = requests.get(current["link"], timeout=45)
        if public.status_code != 200:
            raise RolloutError(f"post {pid}: public HTTP {public.status_code}")
        print(f"VERIFIED post={pid}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "apply", "verify"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    try:
        if args.command == "plan":
            command_plan(config)
        elif args.command == "apply":
            command_apply(config)
        else:
            command_verify(config)
    except (RolloutError, requests.RequestException, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

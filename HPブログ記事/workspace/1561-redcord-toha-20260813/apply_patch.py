#!/usr/bin/env python3
"""Safely patch published post 1561 (title / excerpt / content only)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from post_to_wp import (  # noqa: E402
    convert_markdown_to_html,
    move_jsonld_to_end,
    parse_front_matter,
    remove_heading_matching_title,
    strip_non_article_markdown_sections,
)
from wp_fixed_elements import publication_html_errors, publication_tag_errors  # noqa: E402

MANIFEST_PATH = ROOT / "change_manifest.json"
PLAN_PATH = ROOT / "rollout_plan.json"
PREVIEW_DIR = ROOT / "qa_preview"
SOURCE_MD = (
    PROJECT_ROOT
    / "HPブログ記事"
    / "投稿前"
    / "レッドコード整体とは？赤いロープで体を支える施術の考え方.md"
)
POST_IDS = (1561,)


class PatchError(RuntimeError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_config() -> dict[str, str]:
    config = {
        "WP_URL": (os.getenv("WP_URL") or "").strip().rstrip("/"),
        "WP_USER": (os.getenv("WP_USER") or "").strip(),
        "WP_APP_PASSWORD": (os.getenv("WP_APP_PASSWORD") or "").strip(),
    }
    missing = [k for k, v in config.items() if not v]
    if missing:
        raise PatchError(f"Missing env: {', '.join(missing)}")
    return config


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


def backup_path(post_id: int) -> Path:
    return ROOT / f"backup_{post_id}.json"


def compact_post(post: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(post["id"]),
        "status": post["status"],
        "slug": post["slug"],
        "link": post.get("link", ""),
        "title": post["title"]["raw"],
        "excerpt": post.get("excerpt", {}).get("raw", ""),
        "content_raw": post["content"]["raw"],
        "date": post.get("date"),
        "date_gmt": post.get("date_gmt"),
        "modified": post.get("modified"),
        "modified_gmt": post.get("modified_gmt"),
        "tags": post.get("tags", []),
        "categories": post.get("categories", []),
        "featured_media": post.get("featured_media"),
    }


def load_backup(post_id: int) -> dict[str, Any]:
    path = backup_path(post_id)
    if not path.exists():
        raise PatchError(f"Missing backup: {path}")
    return read_json(path)


def build_html_from_markdown(path: Path) -> tuple[str, str, str]:
    metadata, body = parse_front_matter(path.read_text(encoding="utf-8"))
    title = str(metadata.get("title") or "").strip()
    excerpt = str(metadata.get("excerpt") or "").strip()
    if not title:
        raise PatchError("front matter title is missing")
    tag_errors = publication_tag_errors(metadata.get("tags"))
    if tag_errors:
        raise PatchError("; ".join(tag_errors))
    body = remove_heading_matching_title(body, title)
    body = strip_non_article_markdown_sections(body)
    html = move_jsonld_to_end(convert_markdown_to_html(body))
    html_errors = publication_html_errors(html)
    if html_errors:
        raise PatchError("; ".join(html_errors))
    return title, excerpt, html


def expected_post(post_id: int, backup: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
    spec = manifest["posts"][str(post_id)]
    return {
        "title": spec["title"],
        "excerpt": spec["excerpt"],
        "content": spec["content"],
    }


def assert_matches_baseline(current: dict[str, Any], backup: dict[str, Any]) -> None:
    post_id = int(current["id"])
    if current["status"] != backup["status"]:
        raise PatchError(f"post {post_id}: status changed")
    if current["slug"] != backup["slug"]:
        raise PatchError(f"post {post_id}: slug changed")
    if current.get("date") != backup.get("date"):
        raise PatchError(f"post {post_id}: publish date changed")
    if sha256_text(current["content"]["raw"]) != sha256_text(backup["content_raw"]):
        raise PatchError(f"post {post_id}: content changed since backup")
    if current["title"]["raw"] != backup["title"]:
        raise PatchError(f"post {post_id}: title changed since backup")


def write_qa_preview(post_id: int, backup: dict[str, Any], expected: dict[str, str]) -> Path:
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    path = PREVIEW_DIR / f"{post_id}_qa.md"
    body = (
        f"# Post ID {post_id}\n\n"
        f"- status: {backup['status']}\n"
        f"- slug unchanged: True\n"
        f"- date unchanged: True\n"
        f"- title changed: {expected['title'] != backup['title']}\n"
        f"- excerpt changed: {expected['excerpt'] != backup.get('excerpt', '')}\n"
        f"- content changed: {expected['content'] != backup['content_raw']}\n"
        f"- excerpt chars: {len(expected['excerpt'])}\n\n"
        f"## Title (new)\n{expected['title']}\n\n"
        f"## Title (old)\n{backup['title']}\n\n"
        f"## Excerpt (new)\n{expected['excerpt']}\n\n"
        f"## Excerpt (old)\n{backup.get('excerpt', '')}\n"
    )
    path.write_text(body, encoding="utf-8")
    (PREVIEW_DIR / f"{post_id}_content.html").write_text(expected["content"], encoding="utf-8")
    return path


def command_backup(config: dict[str, str]) -> None:
    for post_id in POST_IDS:
        path = backup_path(post_id)
        if path.exists():
            print(f"BACKUP_EXISTS post={post_id} path={path} (not overwritten)")
            continue
        post = fetch_post(config, post_id)
        compact = compact_post(post)
        write_json(path, compact)
        print(
            f"BACKUP post={post_id} status={compact['status']} "
            f"date={compact['date']} excerpt_len={len(compact['excerpt'])} path={path}"
        )


def command_plan(_config: dict[str, str]) -> None:
    title, excerpt, html = build_html_from_markdown(SOURCE_MD)
    manifest = {
        "posts": {
            "1561": {
                "title": title,
                "excerpt": excerpt,
                "content": html,
            }
        }
    }
    write_json(MANIFEST_PATH, manifest)
    plan: dict[str, Any] = {"posts": {}, "qa_files": {}}
    for post_id in POST_IDS:
        backup = load_backup(post_id)
        expected = expected_post(post_id, backup, manifest)
        if backup["status"] != "publish":
            raise PatchError(f"post {post_id}: expected publish, got {backup['status']}")
        plan["posts"][str(post_id)] = {
            "baseline_content_sha256": sha256_text(backup["content_raw"]),
            "expected_content_sha256": sha256_text(expected["content"]),
            "title": expected["title"],
            "excerpt": expected["excerpt"],
            "status": backup["status"],
            "slug": backup["slug"],
            "date": backup.get("date"),
            "link": backup.get("link"),
        }
        qa_path = write_qa_preview(post_id, backup, expected)
        plan["qa_files"][str(post_id)] = str(qa_path)
        print(
            f"PLANNED post={post_id} title_changed="
            f"{expected['title'] != backup['title']} "
            f"excerpt_changed={expected['excerpt'] != backup.get('excerpt', '')} "
            f"content_changed={expected['content'] != backup['content_raw']} qa={qa_path}"
        )
    write_json(PLAN_PATH, plan)
    print(f"PLAN={PLAN_PATH}")
    print(f"MANIFEST={MANIFEST_PATH}")


def rollback_posts(config: dict[str, str], touched: list[int]) -> None:
    for post_id in reversed(touched):
        backup = load_backup(post_id)
        response = requests.post(
            f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
            json={
                "title": backup["title"],
                "excerpt": backup.get("excerpt", ""),
                "content": backup["content_raw"],
            },
            auth=wp_auth(config),
            timeout=60,
        )
        response.raise_for_status()
        restored = fetch_post(config, post_id)
        if sha256_text(restored["content"]["raw"]) != sha256_text(backup["content_raw"]):
            raise PatchError(f"Rollback verification failed for post {post_id}")
        if restored["status"] != backup["status"]:
            raise PatchError(f"Rollback status mismatch for post {post_id}")
        if restored.get("date") != backup.get("date"):
            raise PatchError(f"Rollback date mismatch for post {post_id}")
        if restored["slug"] != backup["slug"]:
            raise PatchError(f"Rollback slug mismatch for post {post_id}")
        print(f"ROLLED_BACK post={post_id}")


def command_apply(config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    plan = read_json(PLAN_PATH)
    touched: list[int] = []
    try:
        for post_id in POST_IDS:
            backup = load_backup(post_id)
            current = fetch_post(config, post_id)
            assert_matches_baseline(current, backup)
            if sha256_text(current["content"]["raw"]) != plan["posts"][str(post_id)]["baseline_content_sha256"]:
                raise PatchError(f"post {post_id}: baseline hash mismatch with plan")
            expected = expected_post(post_id, backup, manifest)
            payload = {
                "title": expected["title"],
                "excerpt": expected["excerpt"],
                "content": expected["content"],
            }
            response = requests.post(
                f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                json=payload,
                auth=wp_auth(config),
                timeout=60,
            )
            response.raise_for_status()
            updated = fetch_post(config, post_id)
            if updated["status"] != backup["status"]:
                raise PatchError(f"post {post_id}: status changed after update")
            if updated["slug"] != backup["slug"]:
                raise PatchError(f"post {post_id}: slug changed after update")
            if updated.get("date") != backup.get("date"):
                raise PatchError(f"post {post_id}: publish date changed after update")
            if sha256_text(updated["content"]["raw"]) != sha256_text(expected["content"]):
                raise PatchError(f"post {post_id}: content not applied correctly")
            if updated["title"]["raw"] != expected["title"]:
                raise PatchError(f"post {post_id}: title not applied correctly")
            if updated["excerpt"]["raw"].strip() != expected["excerpt"].strip():
                raise PatchError(
                    f"post {post_id}: excerpt not applied correctly "
                    f"got={updated['excerpt']['raw']!r}"
                )
            touched.append(post_id)
            print(f"UPDATED post={post_id}")
        command_verify(config)
    except Exception:
        if touched:
            rollback_posts(config, touched)
        raise


def command_verify(config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    for post_id in POST_IDS:
        backup = load_backup(post_id)
        expected = expected_post(post_id, backup, manifest)
        current = fetch_post(config, post_id)
        if current["status"] != backup["status"]:
            raise PatchError(f"post {post_id}: status changed")
        if current["slug"] != backup["slug"]:
            raise PatchError(f"post {post_id}: slug changed")
        if current.get("date") != backup.get("date"):
            raise PatchError(f"post {post_id}: publish date changed")
        if sha256_text(current["content"]["raw"]) != sha256_text(expected["content"]):
            raise PatchError(f"post {post_id}: content mismatch")
        if current["title"]["raw"] != expected["title"]:
            raise PatchError(f"post {post_id}: title mismatch")
        if updated_excerpt_mismatch(current, expected):
            raise PatchError(f"post {post_id}: excerpt mismatch")
        headline = extract_headline(expected["content"])
        if headline != expected["title"]:
            raise PatchError(
                f"post {post_id}: title!=headline title={expected['title']!r} headline={headline!r}"
            )
        public = requests.get(current["link"], timeout=45)
        if public.status_code != 200:
            raise PatchError(f"post {post_id}: public HTTP {public.status_code}")
        print(
            f"VERIFIED post={post_id} status={current['status']} "
            f"date={current.get('date')} slug={current['slug']} "
            f"public=200 title=headline={expected['title']}"
        )


def updated_excerpt_mismatch(current: dict[str, Any], expected: dict[str, str]) -> bool:
    return current["excerpt"]["raw"].strip() != expected["excerpt"].strip()


def extract_headline(html: str) -> str:
    marker = '"headline": "'
    start = html.find(marker)
    if start < 0:
        raise PatchError("JSON-LD headline not found")
    start += len(marker)
    end = html.find('"', start)
    if end < 0:
        raise PatchError("JSON-LD headline not terminated")
    return html[start:end]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("backup", "plan", "apply", "verify"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config()
    try:
        if args.command == "backup":
            command_backup(config)
        elif args.command == "plan":
            command_plan(config)
        elif args.command == "apply":
            command_apply(config)
        else:
            command_verify(config)
    except (PatchError, requests.RequestException, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

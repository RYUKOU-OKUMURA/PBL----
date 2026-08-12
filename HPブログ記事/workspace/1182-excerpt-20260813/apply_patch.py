#!/usr/bin/env python3
"""Safely patch published post 1182 (excerpt only)."""

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
load_dotenv(PROJECT_ROOT / ".env")

MANIFEST_PATH = ROOT / "change_manifest.json"
PLAN_PATH = ROOT / "rollout_plan.json"
PREVIEW_DIR = ROOT / "qa_preview"
POST_IDS = (1182,)


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
        "modified": post.get("modified"),
    }


def load_backup(post_id: int) -> dict[str, Any]:
    path = backup_path(post_id)
    if not path.exists():
        raise PatchError(f"Missing backup: {path}")
    return read_json(path)


def expected_post(post_id: int, backup: dict[str, Any], manifest: dict[str, Any]) -> dict[str, str]:
    spec = manifest["posts"][str(post_id)]
    title = spec["title"] if spec.get("title") else backup["title"]
    excerpt = spec["excerpt"] if spec.get("excerpt") else backup.get("excerpt", "")
    return {
        "title": title,
        "excerpt": excerpt,
        "content": backup["content_raw"],
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
    excerpt_changed = expected["excerpt"] != backup.get("excerpt", "")
    content_changed = expected["content"] != backup["content_raw"]
    body = (
        f"# Post ID {post_id}\n\n"
        f"- status: {backup['status']}\n"
        f"- title unchanged: {expected['title'] == backup['title']}\n"
        f"- excerpt changed: {excerpt_changed}\n"
        f"- content changed: {content_changed}\n"
        f"- excerpt chars: {len(expected['excerpt'])}\n\n"
        f"## Title\n{expected['title']}\n\n"
        f"## Excerpt (new)\n{expected['excerpt']}\n\n"
        f"## Excerpt (old)\n{backup.get('excerpt', '')}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


def command_backup(config: dict[str, str]) -> None:
    for post_id in POST_IDS:
        post = fetch_post(config, post_id)
        compact = compact_post(post)
        path = backup_path(post_id)
        write_json(path, compact)
        print(
            f"BACKUP post={post_id} status={compact['status']} "
            f"date={compact['date']} excerpt_len={len(compact['excerpt'])} path={path}"
        )


def command_plan(_config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    plan: dict[str, Any] = {"posts": {}, "qa_files": {}}
    for post_id in POST_IDS:
        backup = load_backup(post_id)
        expected = expected_post(post_id, backup, manifest)
        if expected["title"] != backup["title"]:
            raise PatchError(f"post {post_id}: title change is not allowed")
        if expected["content"] != backup["content_raw"]:
            raise PatchError(f"post {post_id}: content change is not allowed")
        plan["posts"][str(post_id)] = {
            "baseline_content_sha256": sha256_text(backup["content_raw"]),
            "expected_content_sha256": sha256_text(expected["content"]),
            "title": expected["title"],
            "excerpt": expected["excerpt"],
            "status": backup["status"],
            "slug": backup["slug"],
            "date": backup.get("date"),
        }
        qa_path = write_qa_preview(post_id, backup, expected)
        plan["qa_files"][str(post_id)] = str(qa_path)
        print(
            f"PLANNED post={post_id} excerpt_changed="
            f"{expected['excerpt'] != backup.get('excerpt', '')} "
            f"content_changed=False qa={qa_path}"
        )
    write_json(PLAN_PATH, plan)
    print(f"PLAN={PLAN_PATH}")


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
        if current["excerpt"]["raw"].strip() != expected["excerpt"].strip():
            raise PatchError(f"post {post_id}: excerpt mismatch")
        public = requests.get(current["link"], timeout=45)
        if public.status_code != 200:
            raise PatchError(f"post {post_id}: public HTTP {public.status_code}")
        print(
            f"VERIFIED post={post_id} status={current['status']} "
            f"date={current.get('date')} public=200 title_unchanged=True"
        )


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

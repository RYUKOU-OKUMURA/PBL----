#!/usr/bin/env python3
"""Restore the canonical author intro line (脊柱側弯症専門の…) across WP posts.

Only the qualifier immediately before 「フィジカルバランスラボ整体院、」 in the
author block is changed. status / slug / date / title / excerpt stay untouched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[2]
load_dotenv(PROJECT_ROOT / ".env")

BACKUP_DIR = ROOT / "backups"
PLAN_PATH = ROOT / "rollout_plan.json"
CANONICAL_QUALIFIER = "脊柱側弯症専門の"
CLINIC = "フィジカルバランスラボ整体院、"

# qualifier + clinic name, anchored to a tag/line boundary, followed (within a
# short window) by the 院長 line that identifies the author block.
# The qualifier may not span a sentence boundary (！。、) or a tag, so greetings
# such as 「こんにちは！」 can never be swallowed into the replacement.
INTRO_RE = re.compile(
    r"(?<=[>！\n\s])([^<>\r\n！。、]{0,60}?)" + re.escape(CLINIC) + r"(?=(?:.|\r|\n){0,200}?院長の奥村龍晃)"
)

# Markers whose occurrence count must not change when only the qualifier is swapped.
STRUCTURE_MARKERS = ("こんにちは", "院長の奥村龍晃", "wp-image-361", "<p>", "</p>", "<br />")


class RestoreError(RuntimeError):
    pass


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def load_config() -> dict[str, str]:
    config = {
        "WP_URL": (os.getenv("WP_URL") or "").strip().rstrip("/"),
        "WP_USER": (os.getenv("WP_USER") or "").strip(),
        "WP_APP_PASSWORD": (os.getenv("WP_APP_PASSWORD") or "").strip(),
    }
    missing = [k for k, v in config.items() if not v]
    if missing:
        raise RestoreError(f"Missing env: {', '.join(missing)}")
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


def iter_all_posts(config: dict[str, str]):
    for status in ("publish", "future", "draft", "pending", "private"):
        page = 1
        while True:
            response = requests.get(
                f"{config['WP_URL']}/wp-json/wp/v2/posts",
                params={"status": status, "per_page": 100, "page": page, "context": "edit"},
                auth=wp_auth(config),
                timeout=60,
            )
            if response.status_code == 400:
                break
            response.raise_for_status()
            items = response.json()
            if not items:
                break
            yield from items
            if len(items) < 100:
                break
            page += 1


def transform(content: str) -> tuple[str, list[str]]:
    """Return (new_content, replaced_qualifiers). Raises when not exactly one hit."""
    matches = list(INTRO_RE.finditer(content))
    if len(matches) != 1:
        raise RestoreError(f"expected 1 author-intro match, found {len(matches)}")
    old = matches[0].group(1)
    updated = INTRO_RE.sub(CANONICAL_QUALIFIER + CLINIC, content, count=1)
    for marker in STRUCTURE_MARKERS:
        if updated.count(marker) != content.count(marker):
            raise RestoreError(f"structure marker {marker!r} count changed; refusing")
    expected_delta = len(CANONICAL_QUALIFIER + CLINIC) - len(old + CLINIC)
    if len(updated) - len(content) != expected_delta:
        raise RestoreError("more than the qualifier changed; refusing")
    return updated, [old]


def backup_path(post_id: int) -> Path:
    return BACKUP_DIR / f"{post_id}.json"


def date_is_pinned(status: str) -> bool:
    """WordPress re-stamps a draft's date on every save; every other status must keep it."""
    return status != "draft"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def command_plan(config: dict[str, str]) -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    plan: dict[str, Any] = {"posts": {}, "skipped": [], "already_ok": []}
    for post in iter_all_posts(config):
        post_id = int(post["id"])
        raw = post["content"]["raw"]
        if CLINIC not in raw or "院長の奥村龍晃" not in raw:
            plan["skipped"].append({"id": post_id, "status": post["status"],
                                    "title": post["title"]["raw"][:50],
                                    "reason": "no author intro block"})
            continue
        try:
            updated, replaced = transform(raw)
        except RestoreError as exc:
            plan["skipped"].append({"id": post_id, "status": post["status"],
                                    "title": post["title"]["raw"][:50], "reason": str(exc)})
            continue
        if updated == raw:
            plan["already_ok"].append({"id": post_id, "status": post["status"]})
            continue
        write_json(backup_path(post_id), {
            "id": post_id, "status": post["status"], "slug": post["slug"],
            "date": post.get("date"), "date_gmt": post.get("date_gmt"),
            "title": post["title"]["raw"], "content_raw": raw,
        })
        plan["posts"][str(post_id)] = {
            "status": post["status"], "title": post["title"]["raw"][:50],
            "old_qualifier": replaced[0],
            "baseline_content_sha256": sha256_text(raw),
            "expected_content_sha256": sha256_text(updated),
        }
        print(f"PLANNED post={post_id} status={post['status']} old={replaced[0]!r}")
    write_json(PLAN_PATH, plan)
    print(f"\nPLAN={PLAN_PATH}")
    print(f"TO_UPDATE={len(plan['posts'])} ALREADY_OK={len(plan['already_ok'])} SKIPPED={len(plan['skipped'])}")


def rollback(config: dict[str, str], touched: list[int]) -> None:
    for post_id in reversed(touched):
        backup = read_json(backup_path(post_id))
        response = requests.post(
            f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
            json={"content": backup["content_raw"]},
            auth=wp_auth(config), timeout=60,
        )
        response.raise_for_status()
        restored = fetch_post(config, post_id)
        if sha256_text(restored["content"]["raw"]) != sha256_text(backup["content_raw"]):
            raise RestoreError(f"Rollback verification failed for post {post_id}")
        print(f"ROLLED_BACK post={post_id}")


def command_apply(config: dict[str, str]) -> None:
    plan = read_json(PLAN_PATH)
    touched: list[int] = []
    try:
        for post_id_str, spec in plan["posts"].items():
            post_id = int(post_id_str)
            backup = read_json(backup_path(post_id))
            current = fetch_post(config, post_id)
            if current["status"] != backup["status"]:
                raise RestoreError(f"post {post_id}: status changed since plan")
            if current["slug"] != backup["slug"]:
                raise RestoreError(f"post {post_id}: slug changed since plan")
            if date_is_pinned(backup["status"]) and current.get("date") != backup.get("date"):
                raise RestoreError(f"post {post_id}: date changed since plan")
            if sha256_text(current["content"]["raw"]) != spec["baseline_content_sha256"]:
                raise RestoreError(f"post {post_id}: content changed since plan")
            updated_content, _ = transform(backup["content_raw"])
            if sha256_text(updated_content) != spec["expected_content_sha256"]:
                raise RestoreError(f"post {post_id}: transform no longer matches plan")
            response = requests.post(
                f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                json={"content": updated_content},
                auth=wp_auth(config), timeout=60,
            )
            response.raise_for_status()
            after = fetch_post(config, post_id)
            if after["status"] != backup["status"]:
                raise RestoreError(f"post {post_id}: status changed after update")
            if after["slug"] != backup["slug"]:
                raise RestoreError(f"post {post_id}: slug changed after update")
            if date_is_pinned(backup["status"]) and after.get("date") != backup.get("date"):
                raise RestoreError(f"post {post_id}: date changed after update")
            if after["title"]["raw"] != backup["title"]:
                raise RestoreError(f"post {post_id}: title changed after update")
            if sha256_text(after["content"]["raw"]) != spec["expected_content_sha256"]:
                raise RestoreError(f"post {post_id}: content not applied correctly")
            touched.append(post_id)
            print(f"UPDATED post={post_id} status={after['status']}")
    except Exception:
        if touched:
            print(f"\nFAILED after {len(touched)} updates -> rolling back", file=sys.stderr)
            rollback(config, touched)
        raise
    print(f"\nAPPLIED={len(touched)}")


def command_verify(config: dict[str, str]) -> None:
    plan = read_json(PLAN_PATH)
    bad = 0
    for post_id_str, spec in plan["posts"].items():
        post_id = int(post_id_str)
        backup = read_json(backup_path(post_id))
        current = fetch_post(config, post_id)
        problems = []
        if current["status"] != backup["status"]:
            problems.append("status")
        if current["slug"] != backup["slug"]:
            problems.append("slug")
        if date_is_pinned(backup["status"]) and current.get("date") != backup.get("date"):
            problems.append("date")
        if sha256_text(current["content"]["raw"]) != spec["expected_content_sha256"]:
            problems.append("content")
        if CANONICAL_QUALIFIER + CLINIC not in current["content"]["raw"]:
            problems.append("qualifier_missing")
        if problems:
            bad += 1
            print(f"NG post={post_id} {','.join(problems)}")
        else:
            print(f"VERIFIED post={post_id} status={current['status']}")
    if bad:
        raise RestoreError(f"{bad} posts failed verification")
    print(f"\nALL_VERIFIED={len(plan['posts'])}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "apply", "verify"))
    args = parser.parse_args()
    config = load_config()
    try:
        {"plan": command_plan, "apply": command_apply, "verify": command_verify}[args.command](config)
    except (RestoreError, requests.RequestException, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

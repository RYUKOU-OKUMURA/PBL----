#!/usr/bin/env python3
"""Apply a reviewed content-only patch to an already refreshed scheduled post.

The post's current edit-context payload is saved before writing. The update is
accepted only when applying the declared exact replacements produces the same
content as a fresh rebuild from the original rollout backup. Status, scheduled
dates, featured media, inserted media, and fixed-element validation must remain
unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import requests

import scheduled_image_refresh as scheduled


ROOT = Path(__file__).resolve().parent
LATE_PATCH_DIR = ROOT / "late_patches"


class LatePatchError(RuntimeError):
    """Raised when a content-only late patch cannot be applied safely."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def apply_exact_patches(content: str, patches: list[dict[str, str]]) -> str:
    result = content
    for index, patch in enumerate(patches, start=1):
        old = patch["old"]
        if result.count(old) != 1:
            raise LatePatchError(
                f"Late patch {index} must match current WordPress content exactly once"
            )
        result = result.replace(old, patch["new"], 1)
    return result


def expected_from_original(
    core: Any,
    post_id: int,
    original: dict[str, Any],
    media_by_key: dict[str, dict[str, Any]],
) -> str:
    manifest = read_json(core.MANIFEST_PATH)
    grouped = core.assets_by_post(manifest)
    return core.expected_post_content(original, grouped[post_id], media_by_key)


def assert_immutable_fields(
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    expected_content: str,
    core: Any,
) -> None:
    for field in ("status", "date", "date_gmt", "featured_media"):
        if after[field] != before[field]:
            raise LatePatchError(
                f"Immutable field changed for post {after['id']}: {field}"
            )
    if core.raw_content(after) != expected_content:
        raise LatePatchError("WordPress did not preserve the expected patched content")
    if core.publication_html_errors(expected_content) != core.publication_html_errors(
        core.raw_content(before)
    ):
        raise LatePatchError("Fixed-element validation changed after late patch")


def rollback(
    core: Any,
    config: dict[str, str],
    post_id: int,
    before: dict[str, Any],
    applied_content: str,
) -> None:
    current = core.fetch_post(config, post_id)
    if (
        core.raw_content(current) != applied_content
        or current["featured_media"] != before["featured_media"]
    ):
        raise LatePatchError(
            "Rollback refused because WordPress changed after the late-patch write"
        )
    response = requests.post(
        f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
        json={"content": core.raw_content(before)},
        auth=core.wp_auth(config),
        timeout=60,
    )
    response.raise_for_status()
    restored = core.fetch_post(config, post_id)
    assert_immutable_fields(
        before,
        restored,
        expected_content=core.raw_content(before),
        core=core,
    )


def apply(post_id: int) -> None:
    patch_path = LATE_PATCH_DIR / f"{post_id}.json"
    if not patch_path.exists():
        raise LatePatchError(f"Missing late patch declaration: {patch_path}")
    patches = read_json(patch_path)
    core, config = scheduled.prepare(post_id)
    post_root = ROOT / "posts" / str(post_id)
    original = read_json(post_root / "wp_backup" / f"{post_id}.json")
    state = read_json(post_root / "wp_rollout_state.json")
    media_by_key = state.get("media", {})
    expected = expected_from_original(core, post_id, original, media_by_key)
    before = core.fetch_post(config, post_id)

    if before["status"] != original["status"]:
        raise LatePatchError("Scheduled status differs from the original rollout backup")
    if before["date"] != original["date"] or before["date_gmt"] != original["date_gmt"]:
        raise LatePatchError("Scheduled date differs from the original rollout backup")
    if core.publication_html_errors(core.raw_content(before)) != core.publication_html_errors(
        core.raw_content(original)
    ):
        raise LatePatchError("Current fixed-element validation differs from the backup")

    candidate = apply_exact_patches(core.raw_content(before), patches)
    if candidate != expected:
        raise LatePatchError(
            "Late-patched current content differs from a fresh rebuild of the original backup"
        )

    backup_path = post_root / "wp_late_patch_backup" / f"{post_id}.json"
    if backup_path.exists():
        raise LatePatchError(f"Late-patch backup already exists: {backup_path}")
    write_json(backup_path, before)
    (post_root / "wp_preview").mkdir(parents=True, exist_ok=True)
    (post_root / "wp_preview" / f"{post_id}.html").write_text(
        expected, encoding="utf-8"
    )

    try:
        response = requests.post(
            f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
            json={"content": candidate},
            auth=core.wp_auth(config),
            timeout=60,
        )
        response.raise_for_status()
        after = core.fetch_post(config, post_id)
        assert_immutable_fields(
            before, after, expected_content=expected, core=core
        )
        core.command_verify(config)
    except Exception:
        rollback(core, config, post_id, before, candidate)
        raise

    print(
        f"LATE_PATCHED post={post_id} status={after['status']} "
        f"date={after['date']} date_gmt={after['date_gmt']} "
        f"featured_media={after['featured_media']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("post_id", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        apply(args.post_id)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Safely add article-specific images to five existing WordPress posts.

The command has three phases:

1. ``plan`` stores edit-context backups and builds local HTML previews only.
2. ``apply`` uploads media, checks the saved baseline again, and updates one post
   at a time with an optimistic-concurrency guard.
3. ``verify`` compares WordPress and the public pages with the expected result.

Only ``content`` and ``featured_media`` are sent when a post is updated.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from PIL import Image
from requests.auth import HTTPBasicAuth


PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from post_to_wp import load_config  # noqa: E402
from wp_fixed_elements import publication_html_errors  # noqa: E402


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "image_manifest.json"
FINAL_DIR = ROOT / "final"
BACKUP_DIR = ROOT / "wp_backup"
PREVIEW_DIR = ROOT / "wp_preview"
PLAN_PATH = ROOT / "wp_rollout_plan.json"
STATE_PATH = ROOT / "wp_rollout_state.json"
POST_IDS = (976, 965, 441, 1176, 1182)
H2_RE = re.compile(r"<h2\b[^>]*>(?P<inner>.*?)</h2>", re.I | re.S)


class RolloutError(RuntimeError):
    """Raised when a rollout safety condition is not met."""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def image_file_record(path: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        image_format = image.format
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "width": width,
        "height": height,
        "format": image_format,
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def wp_auth(config: dict[str, str]) -> HTTPBasicAuth:
    return HTTPBasicAuth(config["WP_USER"], config["WP_APP_PASSWORD"])


def api_get(config: dict[str, str], path: str, **params: Any) -> Any:
    response = requests.get(
        f"{config['WP_URL']}/wp-json/wp/v2/{path}",
        params=params,
        auth=wp_auth(config),
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def fetch_post(config: dict[str, str], post_id: int) -> dict[str, Any]:
    return api_get(config, f"posts/{post_id}", context="edit")


def raw_content(post: dict[str, Any]) -> str:
    raw = post.get("content", {}).get("raw")
    if not isinstance(raw, str):
        raise RolloutError(f"Post {post.get('id')} has no edit-context raw content")
    return raw


def normalized_heading(inner_html: str) -> str:
    text = BeautifulSoup(inner_html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def image_figure(media: dict[str, Any], asset: dict[str, Any]) -> str:
    media_id = int(media["id"])
    source_url = html.escape(str(media["url"]), quote=True)
    alt = html.escape(str(asset["alt"]), quote=True)
    width = int(media.get("width") or 1200)
    height = int(media.get("height") or (675 if asset["role"] == "featured" else 900))
    return (
        f'\n<!-- wp:image {{"id":{media_id},"sizeSlug":"full","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-full"><img src="{source_url}" '
        f'alt="{alt}" class="wp-image-{media_id}" width="{width}" height="{height}" /></figure>\n'
        "<!-- /wp:image -->\n"
    )


def insert_body_images(
    original: str,
    assets: list[dict[str, Any]],
    media_by_key: dict[str, dict[str, Any]],
) -> str:
    result = original
    for asset in assets:
        if asset["role"] != "body":
            continue
        media = media_by_key[asset["key"]]
        if str(media["url"]) in result:
            raise RolloutError(f"Image already exists in content: {asset['key']}")
        target = str(asset["insert_after_heading"])
        matches = [
            match
            for match in H2_RE.finditer(result)
            if normalized_heading(match.group("inner")) == target
        ]
        if len(matches) != 1:
            raise RolloutError(
                f"Heading match count for {asset['key']} / {target!r}: {len(matches)}"
            )
        match = matches[0]
        result = result[: match.end()] + image_figure(media, asset) + result[match.end() :]
    return result


def assets_by_post(manifest: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    grouped = {post_id: [] for post_id in POST_IDS}
    for asset in manifest["assets"]:
        grouped[int(asset["post_id"])].append(asset)
    if set(grouped) != set(POST_IDS) or sum(map(len, grouped.values())) != 16:
        raise RolloutError("Manifest must describe exactly 16 assets for the five target posts")
    for post_id, assets in grouped.items():
        if sum(asset["role"] == "featured" for asset in assets) != 1:
            raise RolloutError(f"Post {post_id} must have exactly one featured asset")
    return grouped


def placeholder_media(asset: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": 900000 + list_asset_keys().index(asset["key"]),
        "url": f"https://example.invalid/pbl/{asset['key']}.webp",
        "width": 1200,
        "height": 675 if asset["role"] == "featured" else 900,
    }


def list_asset_keys() -> list[str]:
    return [asset["key"] for asset in read_json(MANIFEST_PATH)["assets"]]


def baseline_record(post: dict[str, Any]) -> dict[str, Any]:
    content = raw_content(post)
    return {
        "id": int(post["id"]),
        "title": post["title"]["raw"],
        "status": post["status"],
        "date": post["date"],
        "date_gmt": post["date_gmt"],
        "modified": post["modified"],
        "modified_gmt": post["modified_gmt"],
        "featured_media": int(post["featured_media"]),
        "content_sha256": sha256_text(content),
        "content_img_count": len(re.findall(r"<img\b", content, re.I)),
        "fixed_element_errors": publication_html_errors(content),
        "link": post["link"],
    }


def assert_matches_baseline(post: dict[str, Any], baseline: dict[str, Any]) -> None:
    checks = {
        "status": post["status"],
        "date": post["date"],
        "date_gmt": post["date_gmt"],
        "modified": post["modified"],
        "modified_gmt": post["modified_gmt"],
        "featured_media": int(post["featured_media"]),
        "content_sha256": sha256_text(raw_content(post)),
    }
    expected = {key: baseline[key] for key in checks}
    if checks != expected:
        raise RolloutError(
            f"Post {post['id']} changed after planning; refusing to overwrite. "
            f"Expected {expected}, got {checks}"
        )


def command_plan(config: dict[str, str]) -> None:
    manifest = read_json(MANIFEST_PATH)
    grouped = assets_by_post(manifest)
    all_placeholder_media = {
        asset["key"]: placeholder_media(asset) for asset in manifest["assets"]
    }
    plan: dict[str, Any] = {
        "site_url": config["WP_URL"],
        "manifest_sha256": sha256_text(MANIFEST_PATH.read_text(encoding="utf-8")),
        "image_files": {},
        "posts": {},
    }
    for asset in manifest["assets"]:
        path = FINAL_DIR / f"{asset['key']}.webp"
        if not path.exists():
            raise RolloutError(f"Missing final image: {path}")
        record = image_file_record(path)
        expected_height = 675 if asset["role"] == "featured" else 900
        if (
            record["format"] != "WEBP"
            or record["width"] != 1200
            or record["height"] != expected_height
        ):
            raise RolloutError(f"Unexpected image format or dimensions for {asset['key']}")
        plan["image_files"][asset["key"]] = record
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)

    for post_id in POST_IDS:
        current = fetch_post(config, post_id)
        backup_path = BACKUP_DIR / f"{post_id}.json"
        if backup_path.exists():
            backup = read_json(backup_path)
            if baseline_record(backup) != baseline_record(current):
                raise RolloutError(
                    f"Existing backup for post {post_id} differs from WordPress; "
                    "move it aside only after confirming the change"
                )
        else:
            write_json(backup_path, current)
            backup = current

        baseline = baseline_record(backup)
        preview = insert_body_images(raw_content(backup), grouped[post_id], all_placeholder_media)
        if publication_html_errors(preview) != baseline["fixed_element_errors"]:
            raise RolloutError(f"Fixed-element validation changed in preview for post {post_id}")
        expected_body = sum(asset["role"] == "body" for asset in grouped[post_id])
        preview_img_count = len(re.findall(r"<img\b", preview, re.I))
        if preview_img_count != baseline["content_img_count"] + expected_body:
            raise RolloutError(f"Unexpected image count in preview for post {post_id}")
        (PREVIEW_DIR / f"{post_id}.html").write_text(preview, encoding="utf-8")
        plan["posts"][str(post_id)] = baseline
        print(
            f"PLAN post={post_id} body_images=+{expected_body} "
            f"existing_images={baseline['content_img_count']} "
            f"fixed_errors={len(baseline['fixed_element_errors'])}"
        )

    write_json(PLAN_PATH, plan)
    print(f"PLAN_SAVED={PLAN_PATH}")
    print(f"BACKUP_DIR={BACKUP_DIR}")
    print(f"PREVIEW_DIR={PREVIEW_DIR}")


def validate_plan(config: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    plan = read_json(PLAN_PATH)
    manifest = read_json(MANIFEST_PATH)
    if plan["site_url"] != config["WP_URL"]:
        raise RolloutError("Plan belongs to a different WordPress site")
    current_manifest_hash = sha256_text(MANIFEST_PATH.read_text(encoding="utf-8"))
    if plan["manifest_sha256"] != current_manifest_hash:
        raise RolloutError("Image manifest changed after planning")
    assets_by_post(manifest)
    expected_keys = {asset["key"] for asset in manifest["assets"]}
    if set(plan.get("image_files", {})) != expected_keys:
        raise RolloutError("Plan does not contain exactly the 16 expected image files")
    for key in expected_keys:
        path = FINAL_DIR / f"{key}.webp"
        if not path.exists() or image_file_record(path) != plan["image_files"][key]:
            raise RolloutError(f"Final image changed after planning: {key}")
    for post_id in POST_IDS:
        backup_path = BACKUP_DIR / f"{post_id}.json"
        if not backup_path.exists():
            raise RolloutError(f"Missing planned backup for post {post_id}")
        backup_record = baseline_record(read_json(backup_path))
        if backup_record != plan["posts"][str(post_id)]:
            raise RolloutError(f"Backup changed after planning for post {post_id}")
    return plan, manifest


def validate_media(config: dict[str, str], asset: dict[str, Any], media: dict[str, Any]) -> None:
    remote = api_get(config, f"media/{int(media['id'])}", context="edit")
    if remote.get("source_url") != media.get("url"):
        raise RolloutError(f"Media URL mismatch for {asset['key']}")
    if remote.get("alt_text") != asset["alt"]:
        raise RolloutError(f"Media alt mismatch for {asset['key']}")


def upload_asset(
    config: dict[str, str], asset: dict[str, Any], state: dict[str, Any]
) -> dict[str, Any]:
    key = asset["key"]
    existing = state.setdefault("media", {}).get(key)
    if existing:
        validate_media(config, asset, existing)
        return existing

    path = FINAL_DIR / f"{key}.webp"
    if not path.exists():
        raise RolloutError(f"Missing final image: {path}")
    upload_index = list_asset_keys().index(key) + 1
    headers = {
        "Content-Disposition": (
            f'attachment; filename="pbl-{int(asset["post_id"])}-'
            f'{upload_index:02d}-202607.webp"'
        ),
        "Content-Type": "image/webp",
    }
    response = requests.post(
        f"{config['WP_URL']}/wp-json/wp/v2/media",
        headers=headers,
        data=path.read_bytes(),
        auth=wp_auth(config),
        timeout=90,
    )
    if response.status_code != 201:
        raise RolloutError(
            f"Upload failed for {key}: HTTP {response.status_code} {response.text[:300]}"
        )
    uploaded = response.json()
    media_id = int(uploaded["id"])
    meta_response = requests.post(
        f"{config['WP_URL']}/wp-json/wp/v2/media/{media_id}",
        json={"alt_text": asset["alt"], "title": asset["alt"]},
        auth=wp_auth(config),
        timeout=45,
    )
    meta_response.raise_for_status()
    details = uploaded.get("media_details") or {}
    media = {
        "id": media_id,
        "url": uploaded["source_url"],
        "width": int(details.get("width") or 1200),
        "height": int(
            details.get("height") or (675 if asset["role"] == "featured" else 900)
        ),
    }
    state["media"][key] = media
    write_json(STATE_PATH, state)
    validate_media(config, asset, media)
    print(f"UPLOADED key={key} media_id={media_id}")
    return media


def expected_post_content(
    backup: dict[str, Any],
    assets: list[dict[str, Any]],
    media_by_key: dict[str, dict[str, Any]],
) -> str:
    return insert_body_images(raw_content(backup), assets, media_by_key)


def rollback_posts(
    config: dict[str, str],
    touched: list[tuple[int, str, int]],
    backups: dict[int, dict[str, Any]],
) -> None:
    failures: list[str] = []
    for post_id, applied_hash, applied_featured in reversed(touched):
        try:
            current = fetch_post(config, post_id)
            if (
                sha256_text(raw_content(current)) != applied_hash
                or int(current["featured_media"]) != applied_featured
            ):
                failures.append(
                    f"post {post_id}: content or featured image changed after rollout update"
                )
                print(f"ROLLBACK_SKIPPED {failures[-1]}", file=sys.stderr)
                continue
            backup = backups[post_id]
            response = requests.post(
                f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                json={
                    "content": raw_content(backup),
                    "featured_media": int(backup["featured_media"]),
                },
                auth=wp_auth(config),
                timeout=60,
            )
            response.raise_for_status()
            restored = fetch_post(config, post_id)
            if (
                raw_content(restored) != raw_content(backup)
                or int(restored["featured_media"]) != int(backup["featured_media"])
                or restored["status"] != backup["status"]
                or restored["date"] != backup["date"]
                or restored["date_gmt"] != backup["date_gmt"]
            ):
                raise RolloutError(f"verification failed for post {post_id}")
            print(f"ROLLED_BACK post={post_id}", file=sys.stderr)
        except Exception as exc:  # Continue restoring every other touched post.
            failures.append(f"post {post_id}: {exc}")
            print(f"ROLLBACK_FAILED post={post_id}: {exc}", file=sys.stderr)
    if failures:
        raise RolloutError("Rollback incomplete: " + "; ".join(failures))


def command_apply(config: dict[str, str]) -> None:
    plan, manifest = validate_plan(config)
    grouped = assets_by_post(manifest)
    backups = {post_id: read_json(BACKUP_DIR / f"{post_id}.json") for post_id in POST_IDS}

    for post_id in POST_IDS:
        assert_matches_baseline(fetch_post(config, post_id), plan["posts"][str(post_id)])

    state = read_json(STATE_PATH) if STATE_PATH.exists() else {"media": {}, "updated_posts": []}
    media_by_key: dict[str, dict[str, Any]] = {}
    for asset in manifest["assets"]:
        media_by_key[asset["key"]] = upload_asset(config, asset, state)

    # Uploading can take time, so check every post against the baseline once more.
    for post_id in POST_IDS:
        assert_matches_baseline(fetch_post(config, post_id), plan["posts"][str(post_id)])

    touched: list[tuple[int, str, int]] = []
    try:
        for post_id in POST_IDS:
            current = fetch_post(config, post_id)
            assert_matches_baseline(current, plan["posts"][str(post_id)])
            assets = grouped[post_id]
            expected = expected_post_content(backups[post_id], assets, media_by_key)
            featured = next(asset for asset in assets if asset["role"] == "featured")
            featured_id = int(media_by_key[featured["key"]]["id"])
            try:
                response = requests.post(
                    f"{config['WP_URL']}/wp-json/wp/v2/posts/{post_id}",
                    json={"content": expected, "featured_media": featured_id},
                    auth=wp_auth(config),
                    timeout=60,
                )
                response.raise_for_status()
            except requests.RequestException:
                # A timeout can occur after WordPress accepted the request.
                # Detect that case so the outer rollback can still restore it.
                after_error = fetch_post(config, post_id)
                if (
                    raw_content(after_error) == expected
                    and int(after_error["featured_media"]) == featured_id
                ):
                    touched.append((post_id, sha256_text(expected), featured_id))
                raise
            # Once WordPress has accepted the write, include this post in any
            # rollback even if the subsequent verification itself fails.
            applied_hash = sha256_text(expected)
            touched.append((post_id, applied_hash, featured_id))
            updated = fetch_post(config, post_id)
            if raw_content(updated) != expected or int(updated["featured_media"]) != featured_id:
                raise RolloutError(f"WordPress did not preserve expected update for post {post_id}")
            state["updated_posts"] = [item for item in state["updated_posts"] if item != post_id]
            state["updated_posts"].append(post_id)
            write_json(STATE_PATH, state)
            print(f"UPDATED post={post_id} featured_media={featured_id}")
        # Keep final state, media, rendered-content, and public-page checks in
        # the rollback scope. A failed end-to-end verification is not success.
        command_verify(config)
    except Exception:
        rollback_posts(config, touched, backups)
        raise


def command_verify(config: dict[str, str]) -> None:
    _, manifest = validate_plan(config)
    grouped = assets_by_post(manifest)
    state = read_json(STATE_PATH)
    media_by_key = state.get("media", {})
    if set(media_by_key) != set(list_asset_keys()):
        raise RolloutError("Media state does not contain exactly the 16 expected assets")

    for asset in manifest["assets"]:
        validate_media(config, asset, media_by_key[asset["key"]])

    for post_id in POST_IDS:
        backup = read_json(BACKUP_DIR / f"{post_id}.json")
        expected = expected_post_content(backup, grouped[post_id], media_by_key)
        current = fetch_post(config, post_id)
        featured = next(asset for asset in grouped[post_id] if asset["role"] == "featured")
        featured_id = int(media_by_key[featured["key"]]["id"])
        if current["status"] != backup["status"]:
            raise RolloutError(f"Status changed for post {post_id}")
        if current["date"] != backup["date"] or current["date_gmt"] != backup["date_gmt"]:
            raise RolloutError(f"Publication date changed for post {post_id}")
        if raw_content(current) != expected:
            raise RolloutError(f"Content mismatch for post {post_id}")
        if int(current["featured_media"]) != featured_id:
            raise RolloutError(f"Featured media mismatch for post {post_id}")
        if publication_html_errors(expected) != publication_html_errors(raw_content(backup)):
            raise RolloutError(f"Fixed-element validation changed for post {post_id}")

        rendered = current.get("content", {}).get("rendered", "")
        for asset in grouped[post_id]:
            if asset["role"] == "body":
                media = media_by_key[asset["key"]]
                if media["url"] not in rendered or html.escape(asset["alt"]) not in rendered:
                    raise RolloutError(f"Rendered body image missing for {asset['key']}")
        public = requests.get(current["link"], timeout=45)
        if public.status_code != 200:
            raise RolloutError(f"Public page HTTP {public.status_code} for post {post_id}")
        for asset in grouped[post_id]:
            if asset["role"] == "body" and media_by_key[asset["key"]]["url"] not in public.text:
                raise RolloutError(f"Public page body image missing for {asset['key']}")
        print(
            f"VERIFIED post={post_id} status={current['status']} "
            f"body_images=+{sum(a['role'] == 'body' for a in grouped[post_id])} "
            f"featured_media={featured_id} public_http=200"
        )


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

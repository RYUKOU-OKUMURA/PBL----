#!/usr/bin/env python3
"""Run the guarded WordPress image rollout for one scheduled post at a time."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[3]
MASTER_MANIFEST = ROOT / "image_manifest.json"
MASTER_FINAL_DIR = ROOT / "final"
CORE_PATH = (
    PROJECT_ROOT
    / "HPブログ記事"
    / "workspace"
    / "images"
    / "2026-07_top5-refresh"
    / "wp_image_refresh.py"
)


class ScheduledRefreshError(RuntimeError):
    """Raised when the per-post rollout cannot be prepared safely."""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def load_core() -> Any:
    spec = importlib.util.spec_from_file_location("pbl_wp_image_refresh_core", CORE_PATH)
    if spec is None or spec.loader is None:
        raise ScheduledRefreshError(f"Unable to load rollout core: {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def post_manifest(master: dict[str, Any], post_id: int) -> dict[str, Any]:
    assets = [asset for asset in master["assets"] if int(asset["post_id"]) == post_id]
    if len(assets) != 4:
        raise ScheduledRefreshError(
            f"Post {post_id} must have exactly four assets; found {len(assets)}"
        )
    roles = [asset["role"] for asset in assets]
    if roles.count("featured") != 1 or roles.count("body") != 3:
        raise ScheduledRefreshError(f"Post {post_id} must have one featured and three body assets")
    return {
        "style_reference": master["style_reference"],
        "common_style": master["common_style"],
        "assets": assets,
    }


def configure_core(core: Any, post_id: int, manifest_path: Path) -> None:
    post_root = ROOT / "posts" / str(post_id)
    core.ROOT = post_root
    core.MANIFEST_PATH = manifest_path
    core.FINAL_DIR = MASTER_FINAL_DIR
    core.BACKUP_DIR = post_root / "wp_backup"
    core.PREVIEW_DIR = post_root / "wp_preview"
    core.PLAN_PATH = post_root / "wp_rollout_plan.json"
    core.STATE_PATH = post_root / "wp_rollout_state.json"
    core.POST_IDS = (post_id,)


def prepare(post_id: int) -> tuple[Any, dict[str, str]]:
    if not MASTER_MANIFEST.exists():
        raise ScheduledRefreshError(f"Missing master manifest: {MASTER_MANIFEST}")
    master = read_json(MASTER_MANIFEST)
    subset = post_manifest(master, post_id)
    post_root = ROOT / "posts" / str(post_id)
    manifest_path = post_root / "image_manifest.json"
    if manifest_path.exists():
        existing = read_json(manifest_path)
        if existing != subset and (post_root / "wp_rollout_plan.json").exists():
            raise ScheduledRefreshError(
                f"Post {post_id} manifest changed after planning; review before replacing"
            )
    write_json(manifest_path, subset)
    for asset in subset["assets"]:
        image_path = MASTER_FINAL_DIR / f"{asset['key']}.webp"
        if not image_path.exists():
            raise ScheduledRefreshError(f"Missing final image: {image_path}")
    core = load_core()
    configure_core(core, post_id, manifest_path)
    return core, core.load_config()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "plan", "apply", "verify"))
    parser.add_argument("post_id", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        core, config = prepare(args.post_id)
        if args.command == "prepare":
            print(f"PREPARED post={args.post_id}")
        elif args.command == "plan":
            core.command_plan(config)
        elif args.command == "apply":
            core.command_apply(config)
        else:
            core.command_verify(config)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

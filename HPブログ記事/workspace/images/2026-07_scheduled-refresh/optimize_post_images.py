#!/usr/bin/env python3
"""Create final WebP files for one reviewed scheduled post."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
FINAL_DIR = ROOT / "final"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("post_id", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selection_path = ROOT / "posts" / str(args.post_id) / "selection.json"
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    if int(selection["post_id"]) != args.post_id:
        raise ValueError("Selection belongs to a different post")
    manifest = json.loads((ROOT / "image_manifest.json").read_text(encoding="utf-8"))
    assets = [asset for asset in manifest["assets"] if int(asset["post_id"]) == args.post_id]
    if len(assets) != 4:
        raise ValueError(f"Expected four assets for post {args.post_id}")
    selected = selection["selected_sources"]
    if set(selected) != {asset["key"] for asset in assets}:
        raise ValueError("Selection keys do not match the post manifest")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    for asset in assets:
        key = asset["key"]
        source = ROOT / selected[key]
        with Image.open(source) as original:
            image = original.convert("RGB")
        target = (1200, 675 if asset["role"] == "featured" else 900)
        source_ratio = image.width / image.height
        target_ratio = target[0] / target[1]
        if abs(source_ratio - target_ratio) > 0.02:
            raise ValueError(
                f"Unexpected aspect ratio for {key}: {image.width}x{image.height}"
            )
        image = image.resize(target, Image.Resampling.LANCZOS)
        output = FINAL_DIR / f"{key}.webp"
        image.save(output, "WEBP", quality=82, method=6)
        print(
            f"OPTIMIZED key={key} source={source.name} "
            f"size={target[0]}x{target[1]} bytes={output.stat().st_size}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

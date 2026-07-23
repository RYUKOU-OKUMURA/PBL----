#!/usr/bin/env python3
"""Validate per-group image specs and build the scheduled-post manifest."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parent
SPEC_DIR = ROOT / "specs"
EXPORT_DIR = (
    ROOT
    / "wp_export"
    / "wp-export-future-20260723-163548-915682"
)
OUTPUT = ROOT / "image_manifest.json"
POST_ORDER = (
    1822,
    1805,
    1801,
    1800,
    1798,
    2079,
    1774,
    1820,
    1824,
    1823,
    1796,
    1826,
    1825,
    1821,
    1815,
    1813,
    1799,
    1783,
    1782,
    1762,
)
ROLE_ORDER = {"featured": 0, "body": 1}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    assets: list[dict[str, Any]] = []
    for name in ("group_a.json", "group_b.json", "group_c.json"):
        payload = read_json(SPEC_DIR / name)
        if not isinstance(payload, list):
            raise ValueError(f"{name} must contain a JSON array")
        assets.extend(payload)

    if len(assets) != 80:
        raise ValueError(f"Expected 80 assets, found {len(assets)}")
    keys = [str(asset["key"]) for asset in assets]
    if len(set(keys)) != len(keys):
        raise ValueError("Asset keys must be unique")
    alts = [str(asset["alt"]) for asset in assets]
    if len(set(alts)) != len(alts):
        raise ValueError("Alt text must be unique across the scheduled image set")
    post_counts = Counter(int(asset["post_id"]) for asset in assets)
    if post_counts != Counter({post_id: 4 for post_id in POST_ORDER}):
        raise ValueError(f"Unexpected per-post asset counts: {post_counts}")

    for post_id in POST_ORDER:
        post_assets = [asset for asset in assets if int(asset["post_id"]) == post_id]
        roles = Counter(str(asset["role"]) for asset in post_assets)
        if roles != Counter({"body": 3, "featured": 1}):
            raise ValueError(f"Unexpected roles for post {post_id}: {roles}")
        html_path = EXPORT_DIR / f"{post_id}.html"
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        headings = [heading.get_text(" ", strip=True) for heading in soup.find_all("h2")]
        for asset in post_assets:
            expected_ratio = "16:9" if asset["role"] == "featured" else "4:3"
            if asset["target_ratio"] != expected_ratio:
                raise ValueError(f"Unexpected ratio for {asset['key']}")
            heading = asset.get("insert_after_heading")
            if asset["role"] == "featured":
                if heading is not None:
                    raise ValueError(f"Featured asset has insertion heading: {asset['key']}")
            elif headings.count(str(heading)) != 1:
                raise ValueError(
                    f"Heading match count for {asset['key']} / {heading!r}: "
                    f"{headings.count(str(heading))}"
                )
            if not str(asset["alt"]).strip():
                raise ValueError(f"Empty alt for {asset['key']}")
            prompt_lower = str(asset["prompt"]).lower()
            if not any(
                phrase in prompt_lower
                for phrase in (
                    "no text",
                    "text-free",
                    "no visible writing",
                    "no visible data, text",
                )
            ):
                raise ValueError(f"Prompt lacks a no-text constraint: {asset['key']}")

    assets.sort(
        key=lambda asset: (
            POST_ORDER.index(int(asset["post_id"])),
            ROLE_ORDER[str(asset["role"])],
            str(asset["key"]),
        )
    )
    manifest = {
        "style_reference": (
            "HPブログ記事/投稿前/images/"
            "adult-scoliosis-after-surgery-activity-restrictions-guide/hero.webp"
        ),
        "common_style": (
            "Soft Japanese healthcare editorial flat illustration matching the style "
            "reference only. Pale cream background, muted sage green, dusty blue, "
            "warm beige and soft peach. Clean simple shapes, thin muted outlines, "
            "almost no shadows, no texture, no gradients, no 3D rendering. Gentle, "
            "trustworthy, non-alarming mood. Japanese people where a person is shown. "
            "No text, letters, numbers, labels, logos, watermark, red pain glow, "
            "dramatic grimace, deformed anatomy, exaggerated medical findings, "
            "treatment guarantees, or before-and-after comparison."
        ),
        "post_order": list(POST_ORDER),
        "assets": assets,
    }
    OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"MANIFEST={OUTPUT}")
    print(f"POSTS={len(POST_ORDER)} ASSETS={len(assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

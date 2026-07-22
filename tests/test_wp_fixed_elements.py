from __future__ import annotations

import copy
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

import format_wp_drafts
from wp_fixed_elements import (
    CANONICAL_FOOTER,
    FixedElementsError,
    publication_html_errors,
    replace_footer,
)


LINE_BLOCK = """<div>
<p>公式LINEから24時間受け付けてます！<br />
お困りのことがありましたら、<br />
いつでもお問い合わせください(^^)/</p>
</div>
<div class="q_button_wrap"><a href="https://lin.ee/cZKMhZ6">公式LINE</a></div>"""


def publication_html(footer: str = CANONICAL_FOOTER) -> str:
    return f"""<p class="tldr">要約です。</p>
<img class="wp-image-361" src="profile.jpg" />
<nav class="toc"><ol><li>目次</li></ol></nav>
<h2>本文</h2><p>本文です。</p>
<div class="disclaimer">免責事項</div>
{LINE_BLOCK}
{footer}
<script type="application/ld+json">{{"@context":"https://schema.org"}}</script>"""


OLD_FOOTER = """<footer>
<p>公式LINEから24時間受け付けてます！<br />お問い合わせください。</p>
<p><img class="alignleft size-full wp-image-629" src="old.jpg" /></p>
<p>旧住所</p>
</footer>"""


class FixedElementsTests(unittest.TestCase):
    def test_canonical_publication_html_passes(self) -> None:
        self.assertEqual(publication_html_errors(publication_html()), [])

    def test_old_footer_is_replaced_without_touching_surrounding_bytes(self) -> None:
        original = publication_html(OLD_FOOTER)
        before, after = original.split(OLD_FOOTER)
        updated = replace_footer(original)
        self.assertEqual(updated, before + CANONICAL_FOOTER + after)
        self.assertEqual(publication_html_errors(updated), [])

    def test_canonical_footer_is_idempotent(self) -> None:
        original = publication_html()
        self.assertEqual(replace_footer(original), original)

    def test_missing_or_duplicate_footer_is_rejected(self) -> None:
        for html in (publication_html(""), publication_html(CANONICAL_FOOTER * 2)):
            with self.subTest(html=html[-80:]):
                with self.assertRaises(FixedElementsError):
                    replace_footer(html)

    def test_duplicate_line_invitation_is_reported(self) -> None:
        errors = publication_html_errors(publication_html(OLD_FOOTER))
        self.assertTrue(any(error.startswith("line_invitation:") for error in errors))

    def test_documented_footer_templates_match_the_code(self) -> None:
        paths = (
            Path(".Codex/skills/wp-fixed-elements/reference.md"),
            Path(".cursor/skills/wp-fixed-elements/reference.md"),
            Path("01_ガイドライン・プロンプト/ブログ記事執筆マスターガイド.md"),
        )
        for path in paths:
            matches = re.findall(r"<footer>.*?</footer>", path.read_text(), re.DOTALL)
            self.assertEqual(matches, [CANONICAL_FOOTER], str(path))

    def test_tracked_publication_ready_drafts_use_canonical_elements(self) -> None:
        raw_paths = subprocess.check_output(
            ["git", "ls-files", "-z", "--", "HPブログ記事/投稿前/*.md"]
        )
        checked = 0
        for raw_path in raw_paths.split(b"\0"):
            if not raw_path:
                continue
            path = Path(raw_path.decode())
            html = path.read_text()
            if "<footer" not in html:
                continue
            checked += 1
            self.assertEqual(publication_html_errors(html), [], str(path))
        self.assertGreater(checked, 0)

    def test_failed_current_post_is_included_in_rollback(self) -> None:
        original = {
            "id": 10,
            "status": "future",
            "date": "2026-08-01T13:00:00",
            "date_gmt": "2026-08-01T04:00:00",
            "title": {"raw": "テスト"},
            "content": {"raw": publication_html(OLD_FOOTER)},
        }
        state = copy.deepcopy(original)
        rollback_payloads: list[dict] = []

        def fake_fetch(_config: dict, _post_id: int) -> dict:
            return copy.deepcopy(state)

        def fake_post(_config: dict, _post_id: int, payload: dict) -> dict:
            if payload.get("content") != original["content"]["raw"]:
                state["content"]["raw"] = payload["content"]
                raise requests.Timeout("response lost after update")
            rollback_payloads.append(payload)
            state["content"]["raw"] = payload["content"]
            state["status"] = payload["status"]
            state["date"] = payload["date"]
            state["date_gmt"] = payload["date_gmt"]
            return copy.deepcopy(state)

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(format_wp_drafts, "selected_posts", return_value=[original]),
                patch.object(format_wp_drafts, "fetch_post", side_effect=fake_fetch),
                patch.object(format_wp_drafts, "api_post", side_effect=fake_post),
                patch.object(
                    format_wp_drafts,
                    "backup_posts",
                    return_value=Path(directory) / "backup.json",
                ),
            ):
                with self.assertRaises(requests.Timeout):
                    format_wp_drafts.command_fixed_elements(
                        {}, "future", {10}, True, Path(directory)
                    )

        self.assertEqual(state, original)
        self.assertEqual(len(rollback_payloads), 1)
        self.assertEqual(
            set(rollback_payloads[0]), {"content", "status", "date", "date_gmt"}
        )


if __name__ == "__main__":
    unittest.main()

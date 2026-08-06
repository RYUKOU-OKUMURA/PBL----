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
    ALLOWED_WP_TAGS,
    CANONICAL_FOOTER,
    FixedElementsError,
    publication_html_errors,
    publication_tag_errors,
    replace_footer,
    replace_line_invitation,
)


LINE_BLOCK = """<div>
<p>公式LINEへのメッセージ送信は24時間可能です。返信は営業時間内です。<br />
ご予約や当院の一般的なご案内についてお問い合わせいただけます。</p>
</div>
<div class="q_button_wrap"><a href="https://lin.ee/cZKMhZ6">公式LINE</a></div>"""


def publication_html(footer: str = CANONICAL_FOOTER) -> str:
    return f"""<p class="tldr">要約です。</p>
<img class="wp-image-361" src="profile.jpg" />
<p>この記事の執筆・監修：奥村龍晃（柔道整復師）</p>
<nav class="toc"><ol><li>目次</li></ol></nav>
<h2>本文</h2><p>本文です。</p>
<div class="disclaimer">本記事は一般情報です。症状が続く場合は医療機関にご相談ください。</div>
{LINE_BLOCK}
{footer}
<script type="application/ld+json">{{"@context":"https://schema.org"}}</script>"""


OLD_FOOTER = """<footer>
<p>公式LINEから24時間受け付けてます！<br />お問い合わせください。</p>
<p><img class="alignleft size-full wp-image-629" src="old.jpg" /></p>
<p>旧住所</p>
</footer>"""


class FixedElementsTests(unittest.TestCase):
    def test_schedule_tag_mismatch_rolls_back_to_exact_draft(self) -> None:
        original = {
            "id": 40,
            "status": "draft",
            "date": "2026-08-06T13:00:00",
            "date_gmt": "2026-08-06T04:00:00",
            "title": {"raw": "タグ復元テスト"},
            "content": {"raw": publication_html()},
            "excerpt": {"raw": "抜粋"},
            "categories": [7],
            "tags": [101],
            "featured_media": 500,
        }
        state = copy.deepcopy(original)
        plan = {
            "version": 2,
            "site_url": "https://example.com",
            "timezone": "Asia/Tokyo",
            "future_queue_snapshot": [],
            "items": [
                {
                    "id": 40,
                    "title": "タグ復元テスト",
                    "content_sha256": format_wp_drafts.content_hash(publication_html()),
                    "tags": [101],
                    "tag_names": ["腰痛"],
                    "status": "future",
                    "date": "2026-08-08T13:00:00",
                    "date_gmt": "2026-08-08T04:00:00",
                    "qa_approved": True,
                }
            ],
        }
        payloads: list[dict] = []

        def fake_fetch(_config: dict, _post_id: int) -> dict:
            return copy.deepcopy(state)

        def fake_post(_config: dict, _post_id: int, payload: dict) -> dict:
            payloads.append(copy.deepcopy(payload))
            if set(payload) == {"status", "date", "date_gmt", "tags"}:
                state.update(payload)
                state["tags"] = [999]
                return copy.deepcopy(state)
            state["title"] = {"raw": payload["title"]}
            state["content"] = {"raw": payload["content"]}
            state["excerpt"] = {"raw": payload["excerpt"]}
            for key in (
                "status",
                "date",
                "date_gmt",
                "categories",
                "tags",
                "featured_media",
            ):
                state[key] = copy.deepcopy(payload[key])
            return copy.deepcopy(state)

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(format_wp_drafts, "load_plan", return_value=plan),
                patch.object(
                    format_wp_drafts,
                    "wordpress_timezone",
                    return_value="Asia/Tokyo",
                ),
                patch.object(
                    format_wp_drafts,
                    "allowed_wp_tag_ids",
                    return_value={"腰痛": 101},
                ),
                patch.object(format_wp_drafts, "fetch_post", side_effect=fake_fetch),
                patch.object(format_wp_drafts, "fetch_future_posts", return_value=[]),
                patch.object(format_wp_drafts, "api_post", side_effect=fake_post),
                patch.object(format_wp_drafts, "require_publication_html"),
                patch.object(
                    format_wp_drafts,
                    "backup_posts",
                    return_value=Path(directory) / "backup.json",
                ),
            ):
                with self.assertRaises(format_wp_drafts.PipelineError):
                    format_wp_drafts.command_schedule_plan(
                        {"WP_URL": "https://example.com"},
                        Path(directory) / "plan.json",
                        True,
                        Path(directory),
                    )

        self.assertEqual(state, original)
        self.assertEqual(len(payloads), 2)
        self.assertEqual(payloads[0]["tags"], [101])
        self.assertEqual(payloads[1]["status"], "draft")
        self.assertEqual(payloads[1]["tags"], [101])

    def test_schedule_tag_gate_rejects_disallowed_or_changed_ids(self) -> None:
        allowed = {"腰痛": 101, "名古屋市": 102}
        post = {"tags": [102, 101]}
        self.assertEqual(
            format_wp_drafts.require_allowed_post_tags(
                post, allowed, "post 1", expected=[101, 102]
            ),
            [101, 102],
        )
        with self.assertRaises(format_wp_drafts.PipelineError):
            format_wp_drafts.require_allowed_post_tags(
                {"tags": [999]}, allowed, "post 1"
            )
        with self.assertRaises(format_wp_drafts.PipelineError):
            format_wp_drafts.require_allowed_post_tags(
                {"tags": [101]}, allowed, "post 1", expected=[101, 102]
            )

    def test_schedule_match_includes_exact_planned_tags(self) -> None:
        post = {
            "status": "future",
            "date": "2026-08-08T13:00:00",
            "date_gmt": "2026-08-08T04:00:00",
            "content": {"raw": "本文"},
            "tags": [101, 102],
        }
        item = {
            "status": "future",
            "date": "2026-08-08T13:00:00",
            "date_gmt": "2026-08-08T04:00:00",
            "content_sha256": format_wp_drafts.content_hash("本文"),
            "tags": [102, 101],
        }
        self.assertTrue(format_wp_drafts.schedule_matches(post, item))
        post["tags"] = [101]
        self.assertFalse(format_wp_drafts.schedule_matches(post, item))

    def test_fixed_tag_whitelist_matches_wordpress_tags(self) -> None:
        self.assertEqual(
            ALLOWED_WP_TAGS,
            (
                "股関節痛",
                "名古屋市",
                "フィジカルバランスラボ整体院",
                "整体",
                "名東区",
                "星ヶ丘",
                "千種区",
                "レッドコード整体",
                "坐骨神経痛",
                "肩こり",
                "脊柱側弯症",
                "脊柱管狭窄症",
                "腰椎椎間板ヘルニア",
                "腰痛",
                "五十肩",
                "ぎっくり腰",
                "ぶら下がり整体",
            ),
        )

    def test_tag_preflight_accepts_only_whitelisted_subset(self) -> None:
        self.assertEqual(publication_tag_errors(["名古屋市", "腰痛"]), [])
        self.assertEqual(publication_tag_errors("肩こり"), [])

    def test_tag_preflight_rejects_missing_duplicate_or_new_tags(self) -> None:
        self.assertTrue(publication_tag_errors(None))
        self.assertTrue(publication_tag_errors([]))
        self.assertTrue(publication_tag_errors(["腰痛", "腰痛"]))
        self.assertTrue(publication_tag_errors(["腰痛", "新しいタグ"]))

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

    def test_retired_line_sentence_is_removed(self) -> None:
        retired = "診断・治療方針などの医療上の判断は医療機関へご相談ください。"
        original = publication_html().replace(
            "ご予約や当院の一般的なご案内についてお問い合わせいただけます。",
            "ご予約や当院の一般的なご案内についてお問い合わせいただけます。"
            + retired,
        )
        updated = replace_line_invitation(original)
        self.assertNotIn(retired, updated)
        self.assertEqual(publication_html_errors(updated), [])

    def test_missing_or_duplicate_footer_is_rejected(self) -> None:
        for html in (publication_html(""), publication_html(CANONICAL_FOOTER * 2)):
            with self.subTest(html=html[-80:]):
                with self.assertRaises(FixedElementsError):
                    replace_footer(html)

    def test_duplicate_line_invitation_is_reported(self) -> None:
        errors = publication_html_errors(publication_html(OLD_FOOTER))
        self.assertTrue(any(error.startswith("line_invitation:") for error in errors))

    def test_legacy_fixed_copy_is_rejected(self) -> None:
        html = publication_html().replace(
            "この記事の執筆・監修：奥村龍晃（柔道整復師）",
            "この記事を監修している人：奥村龍晃（柔道整復師資格保有）",
        ).replace(
            "症状が続く場合は医療機関にご相談ください。",
            "2週間以上症状が続く場合は、専門家への受診をおすすめします。",
        )
        errors = publication_html_errors(html)
        self.assertTrue(any(error.startswith("author_copy:") for error in errors))
        self.assertTrue(any(error.startswith("disclaimer_copy:") for error in errors))

    def test_missing_line_invitation_block_is_reported(self) -> None:
        button_only = '<div class="q_button_wrap"><a href="#">公式LINE</a></div>'
        html = publication_html().replace(LINE_BLOCK, button_only)
        errors = publication_html_errors(html)
        self.assertTrue(
            any(error.startswith("line_invitation_block:") for error in errors)
        )

    def test_unrelated_paragraph_is_not_accepted_as_line_invitation(self) -> None:
        unrelated = (
            '<div><p>別の案内文です。</p></div>'
            '<div class="q_button_wrap"><a href="#">公式LINE</a></div>'
        )
        html = publication_html().replace(LINE_BLOCK, unrelated)
        errors = publication_html_errors(html)
        self.assertTrue(
            any(error.startswith("line_invitation_block:") for error in errors)
        )

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

    def test_export_creates_qa_html_and_manifest(self) -> None:
        post = {
            "id": 20,
            "status": "draft",
            "date": "2026-08-01T13:00:00",
            "date_gmt": "2026-08-01T04:00:00",
            "title": {"raw": "QAテスト"},
            "content": {"raw": publication_html()},
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(format_wp_drafts, "selected_posts", return_value=[post]):
                result = format_wp_drafts.command_export({}, "draft", {20}, root)
            self.assertEqual(result, 0)
            export_dirs = list(root.iterdir())
            self.assertEqual(len(export_dirs), 1)
            self.assertEqual((export_dirs[0] / "20.html").read_text(), publication_html())
            manifest = (export_dirs[0] / "manifest.json").read_text()
            self.assertIn('"id": 20', manifest)
            self.assertIn('"content_sha256"', manifest)

    def test_unschedule_dry_run_does_not_write(self) -> None:
        post = {
            "id": 25,
            "status": "future",
            "date": "2026-08-02T13:00:00",
            "date_gmt": "2026-08-02T04:00:00",
            "title": {"raw": "停止テスト"},
            "content": {"raw": publication_html()},
        }
        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.object(format_wp_drafts, "selected_posts", return_value=[post]),
                patch.object(format_wp_drafts, "api_post") as api_post_mock,
                patch.object(format_wp_drafts, "backup_posts") as backup_mock,
            ):
                result = format_wp_drafts.command_unschedule(
                    {}, {25}, False, Path(directory)
                )
        self.assertEqual(result, 0)
        api_post_mock.assert_not_called()
        backup_mock.assert_not_called()

    def test_unschedule_failure_rolls_back_attempted_post(self) -> None:
        original = {
            "id": 26,
            "status": "future",
            "date": "2026-08-04T13:00:00",
            "date_gmt": "2026-08-04T04:00:00",
            "title": {"raw": "停止復元テスト"},
            "content": {"raw": publication_html()},
        }
        state = copy.deepcopy(original)
        update_count = 0

        def fake_fetch(_config: dict, _post_id: int) -> dict:
            return copy.deepcopy(state)

        def fake_post(_config: dict, _post_id: int, payload: dict) -> dict:
            nonlocal update_count
            update_count += 1
            if payload == {"status": "draft"}:
                state["status"] = "draft"
                state["content"]["raw"] += "<!-- unexpected -->"
                state["title"]["raw"] = "意図しないタイトル変更"
                return copy.deepcopy(state)
            state["status"] = payload["status"]
            state["date"] = payload["date"]
            state["date_gmt"] = payload["date_gmt"]
            state["content"]["raw"] = payload["content"]
            state["title"]["raw"] = payload["title"]
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
                with self.assertRaises(format_wp_drafts.PipelineError):
                    format_wp_drafts.command_unschedule(
                        {}, {26}, True, Path(directory)
                    )

        self.assertEqual(state, original)
        self.assertEqual(update_count, 2)

    def test_final_batch_verification_failure_rolls_back(self) -> None:
        original = {
            "id": 30,
            "status": "future",
            "date": "2026-08-03T13:00:00",
            "date_gmt": "2026-08-03T04:00:00",
            "title": {"raw": "最終検証テスト"},
            "content": {"raw": publication_html(OLD_FOOTER)},
        }
        state = copy.deepcopy(original)
        fetch_count = 0
        rollback_payloads: list[dict] = []

        def fake_fetch(_config: dict, _post_id: int) -> dict:
            nonlocal fetch_count
            fetch_count += 1
            if fetch_count == 3:
                state["content"]["raw"] += "<!-- final verification mismatch -->"
            return copy.deepcopy(state)

        def fake_post(_config: dict, _post_id: int, payload: dict) -> dict:
            state["content"]["raw"] = payload["content"]
            if "status" in payload:
                rollback_payloads.append(payload)
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
                with self.assertRaises(format_wp_drafts.PipelineError):
                    format_wp_drafts.command_fixed_elements(
                        {}, "future", {30}, True, Path(directory)
                    )

        self.assertEqual(state, original)
        self.assertEqual(len(rollback_payloads), 1)


if __name__ == "__main__":
    unittest.main()

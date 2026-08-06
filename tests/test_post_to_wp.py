from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from post_to_wp import (
    resolve_tag_ids,
    strip_non_article_markdown_sections,
    verify_post_response_tags,
)


class PostToWordPressMarkdownTests(unittest.TestCase):
    def test_tag_resolution_fails_when_any_existing_tag_is_missing(self) -> None:
        with patch(
            "post_to_wp.get_tag_id", side_effect=[101, None]
        ):
            with self.assertRaisesRegex(RuntimeError, "未登録"):
                resolve_tag_ids({}, ["腰痛", "未登録"])

    def test_tag_resolution_rejects_duplicate_wordpress_ids(self) -> None:
        with patch("post_to_wp.get_tag_id", side_effect=[101, 101]):
            with self.assertRaisesRegex(RuntimeError, "同じWordPressタグID"):
                resolve_tag_ids({}, ["腰痛", "ぎっくり腰"])

    def test_post_response_must_persist_exact_tag_ids(self) -> None:
        response = Mock(status_code=201)
        response.json.return_value = {"tags": [101]}
        with self.assertRaises(SystemExit):
            verify_post_response_tags(response, [101, 102])

        response.json.return_value = {"tags": [102, 101]}
        verify_post_response_tags(response, [101, 102])

    def test_editorial_metadata_sections_are_removed(self) -> None:
        markdown = """# 記事タイトル

本文です。

## メタディスクリプション
検索結果用の説明です。

## サジェストキーワード
- 検索語
"""

        cleaned = strip_non_article_markdown_sections(markdown)

        self.assertIn("本文です。", cleaned)
        self.assertNotIn("メタディスクリプション", cleaned)
        self.assertNotIn("検索結果用の説明", cleaned)
        self.assertNotIn("サジェストキーワード", cleaned)
        self.assertNotIn("検索語", cleaned)

    def test_jsonld_after_editorial_metadata_is_preserved(self) -> None:
        markdown = """本文です。

## メタディスクリプション
検索結果用の説明です。

<script type="application/ld+json">
{"@context":"https://schema.org"}
</script>
"""

        cleaned = strip_non_article_markdown_sections(markdown)

        self.assertNotIn("検索結果用の説明", cleaned)
        self.assertIn('<script type="application/ld+json">', cleaned)
        self.assertIn('"@context":"https://schema.org"', cleaned)

    def test_regular_article_sections_are_unchanged(self) -> None:
        markdown = """## まとめ

メタディスクリプションの考え方を本文で説明します。
"""

        self.assertEqual(strip_non_article_markdown_sections(markdown), markdown)


if __name__ == '__main__':
    unittest.main()

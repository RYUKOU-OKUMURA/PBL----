from __future__ import annotations

import unittest

from post_to_wp import strip_non_article_markdown_sections


class PostToWordPressMarkdownTests(unittest.TestCase):
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

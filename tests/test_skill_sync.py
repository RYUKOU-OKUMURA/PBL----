import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED_SKILLS = ["seitai-blog-pasona", "medical-ad-compliance", "wp-fixed-elements"]


class SkillSyncTest(unittest.TestCase):
    def test_cursor_and_codex_copies_match(self):
        for name in SHARED_SKILLS:
            cursor_dir = ROOT / ".cursor/skills" / name
            for f in cursor_dir.glob("*.md"):
                codex = ROOT / ".Codex/skills" / name / f.name
                with self.subTest(file=str(f.relative_to(ROOT))):
                    self.assertEqual(f.read_text(), codex.read_text())

    def test_claude_commands_point_to_existing_skill(self):
        for cmd in (ROOT / ".claude/commands").glob("*_SKILL.md"):
            path = re.search(r"`([^`]+/SKILL\.md)`", cmd.read_text()).group(1)
            with self.subTest(command=cmd.name):
                self.assertTrue((ROOT / path).is_file())


if __name__ == "__main__":
    unittest.main()

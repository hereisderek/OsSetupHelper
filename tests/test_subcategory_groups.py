"""Unit tests for subcategory group expansion and property inheritance in orchestrator."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from orchestrator import _expand_subcategory_groups  # noqa: E402


class TestSubcategoryGroups(unittest.TestCase):
    def setUp(self):
        self.known_names = {
            "ai/opencode",
            "ai/skills/agent_skills",
            "ai/skills/ponytail",
            "ai/skills/taste_skill",
            "ai/others/aoci_code",
            "ai/others/symphony",
        }

    def test_syntax_1_dict_items_and_props(self):
        section = {
            "ai": {
                "enabled": True,
                "opencode": {"enabled": True, "add_to_dock": True},
                "skills": {
                    "enabled": True,
                    "symlink": True,
                    "symlink_src": "~/.config/agent/skills",
                    "symlink_dst": ["~/.claude/skills"],
                    "agent_skills": True,
                    "items": {
                        "ponytail": True,
                        "taste_skill": {"enabled": True, "custom_opt": "val"},
                    },
                },
                "others": {
                    "enabled": True,
                    "items": {
                        "aoci_code": True,
                        "symphony": True,
                    },
                },
            }
        }
        _expand_subcategory_groups(section, self.known_names)

        self.assertIn("ai/opencode", section)
        self.assertTrue(section["ai/opencode"]["enabled"])
        self.assertTrue(section["ai/opencode"]["add_to_dock"])

        self.assertIn("ai/skills/agent_skills", section)
        self.assertTrue(section["ai/skills/agent_skills"]["enabled"])
        self.assertTrue(section["ai/skills/agent_skills"]["symlink"])
        self.assertEqual(section["ai/skills/agent_skills"]["symlink_src"], "~/.config/agent/skills")

        self.assertIn("ai/skills/ponytail", section)
        self.assertTrue(section["ai/skills/ponytail"]["enabled"])
        self.assertTrue(section["ai/skills/ponytail"]["symlink"])

        self.assertIn("ai/skills/taste_skill", section)
        self.assertTrue(section["ai/skills/taste_skill"]["enabled"])
        self.assertEqual(section["ai/skills/taste_skill"]["custom_opt"], "val")
        self.assertTrue(section["ai/skills/taste_skill"]["symlink"])

        self.assertIn("ai/others/aoci_code", section)
        self.assertTrue(section["ai/others/aoci_code"]["enabled"])
        self.assertNotIn("symlink", section["ai/others/aoci_code"])

    def test_syntax_2_list_items(self):
        section = {
            "ai": {
                "enabled": True,
                "skills": {
                    "enabled": True,
                    "symlink": True,
                    "symlink_src": "~/.config/agent/skills",
                    "items": ["ponytail", "taste_skill"],
                },
                "others": {
                    "enabled": True,
                    "items": ["aoci_code", "symphony"],
                },
            }
        }
        _expand_subcategory_groups(section, self.known_names)

        self.assertIn("ai/skills/ponytail", section)
        self.assertTrue(section["ai/skills/ponytail"]["enabled"])
        self.assertTrue(section["ai/skills/ponytail"]["symlink"])
        self.assertEqual(section["ai/skills/ponytail"]["symlink_src"], "~/.config/agent/skills")

        self.assertIn("ai/skills/taste_skill", section)
        self.assertTrue(section["ai/skills/taste_skill"]["enabled"])

        self.assertIn("ai/others/aoci_code", section)
        self.assertTrue(section["ai/others/aoci_code"]["enabled"])
        self.assertIn("ai/others/symphony", section)
        self.assertTrue(section["ai/others/symphony"]["enabled"])

    def test_disabled_parent_cascades_down(self):
        section = {
            "ai": {
                "enabled": False,
                "skills": {
                    "enabled": True,
                    "items": ["ponytail"],
                },
            }
        }
        _expand_subcategory_groups(section, self.known_names)
        self.assertIn("ai/skills/ponytail", section)
        self.assertFalse(section["ai/skills/ponytail"]["enabled"])


if __name__ == "__main__":
    unittest.main()

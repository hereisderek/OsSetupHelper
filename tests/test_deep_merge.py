"""Run directly: python3 tests/test_deep_merge.py"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from orchestrator import deep_merge  # noqa: E402


class TestDeepMerge(unittest.TestCase):
    def test_dicts_merge_recursively(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        self.assertEqual(deep_merge(base, override), {"a": {"x": 1, "y": 3, "z": 4}})

    def test_lists_are_additive(self):
        base = {"pkgs": ["wget", "jq"]}
        override = {"pkgs": ["htop"]}
        self.assertEqual(deep_merge(base, override)["pkgs"], ["wget", "jq", "htop"])

    def test_string_blacklist_removes_item(self):
        base = {"pkgs": ["wget", "jq"]}
        override = {"pkgs": ["!wget"]}
        self.assertEqual(deep_merge(base, override)["pkgs"], ["jq"])

    def test_dict_blacklist_by_string_id(self):
        base = {"mas": [{"id": "123", "name": "AppName"}]}
        override = {"mas": [{"id": "!123"}]}
        self.assertEqual(deep_merge(base, override)["mas"], [])

    def test_dict_blacklist_by_int_id(self):
        base = {"mas": [{"id": 123, "name": "AppName"}]}
        override = {"mas": [{"id": "!123"}]}
        self.assertEqual(deep_merge(base, override)["mas"], [])

    def test_dict_blacklist_by_name(self):
        base = {"apps": [{"name": "chrome"}, {"name": "vscode"}]}
        override = {"apps": [{"name": "!chrome"}]}
        self.assertEqual(deep_merge(base, override)["apps"], [{"name": "vscode"}])

    def test_dict_blacklist_via_exclude_flag(self):
        base = {"apps": [{"id": 1, "name": "chrome"}]}
        override = {"apps": [{"id": 1, "exclude": True}]}
        self.assertEqual(deep_merge(base, override)["apps"], [])

    def test_dict_with_matching_id_updates_in_place(self):
        base = {"apps": [{"id": 1, "enabled": False}]}
        override = {"apps": [{"id": 1, "enabled": True}]}
        self.assertEqual(deep_merge(base, override)["apps"], [{"id": 1, "enabled": True}])

    def test_scalar_override_replaces(self):
        base = {"enabled": False}
        override = {"enabled": True}
        self.assertEqual(deep_merge(base, override), {"enabled": True})


if __name__ == "__main__":
    unittest.main()

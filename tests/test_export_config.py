import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import (
    DEFAULT_EXPORT_PATH,
    CONFIG_DIR,
    _write_config_export,
    build_full_config_export,
    parse_args,
)


class TestExportConfig(unittest.TestCase):
    def test_default_export_path_location(self):
        self.assertEqual(DEFAULT_EXPORT_PATH, CONFIG_DIR / "config.export.yaml")

    def test_parse_args_without_export(self):
        with patch("sys.argv", ["orchestrator.py"]):
            args = parse_args()
            self.assertIsNone(args.export_config)

    def test_parse_args_export_flag_default(self):
        with patch("sys.argv", ["orchestrator.py", "--export-config"]):
            args = parse_args()
            self.assertEqual(args.export_config, str(DEFAULT_EXPORT_PATH))

    def test_parse_args_export_flag_custom_path(self):
        with patch("sys.argv", ["orchestrator.py", "--export-config", "/tmp/my_export.yaml"]):
            args = parse_args()
            self.assertEqual(args.export_config, "/tmp/my_export.yaml")

    def test_write_config_export_custom_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "exported.yaml"
            cfg = {
                "meta": {"version": "1.0"},
                "execution": {},
                "selections": {
                    "apps": {"chrome": {"enabled": True}},
                    "cli": {},
                    "settings": {},
                },
            }
            written_path = _write_config_export(cfg, str(target))
            self.assertIsNotNone(written_path)
            self.assertTrue(target.exists())

            with open(target, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)

            self.assertTrue(loaded["selections"]["apps"]["chrome"]["enabled"])
            # All known roles should be present and default to enabled=False if not set
            for cat in ["apps", "cli", "settings"]:
                self.assertIn(cat, loaded["selections"])

    def test_write_config_export_default_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_default = Path(tmpdir) / "config.export.yaml"
            with patch("orchestrator.DEFAULT_EXPORT_PATH", custom_default):
                cfg = {
                    "meta": {"version": "1.0"},
                    "execution": {},
                    "selections": {"apps": {}, "cli": {}, "settings": {}},
                }
                written_path = _write_config_export(cfg, None)
                self.assertEqual(written_path, custom_default.resolve())
                self.assertTrue(custom_default.exists())


if __name__ == "__main__":
    unittest.main()

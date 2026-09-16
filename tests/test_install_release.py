import sys
import unittest
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _shared_tasks.installer.install_release import (
    parse_repo_url,
    score_asset,
    select_best_asset,
    check_installed,
)


class TestInstallRelease(unittest.TestCase):
    def test_parse_github_url_standard(self):
        parsed = parse_repo_url("https://github.com/clzoc/BattGUI")
        self.assertEqual(parsed["type"], "github")
        self.assertEqual(parsed["owner"], "clzoc")
        self.assertEqual(parsed["repo"], "BattGUI")
        self.assertEqual(parsed["tag"], "")

    def test_parse_github_url_with_releases_suffix(self):
        parsed = parse_repo_url("https://github.com/clzoc/BattGUI/releases")
        self.assertEqual(parsed["type"], "github")
        self.assertEqual(parsed["owner"], "clzoc")
        self.assertEqual(parsed["repo"], "BattGUI")

    def test_parse_github_url_with_tag(self):
        parsed = parse_repo_url("https://github.com/clzoc/BattGUI/releases/tag/v0.1.2")
        self.assertEqual(parsed["type"], "github")
        self.assertEqual(parsed["owner"], "clzoc")
        self.assertEqual(parsed["repo"], "BattGUI")
        self.assertEqual(parsed["tag"], "v0.1.2")

    def test_parse_gitlab_url(self):
        parsed = parse_repo_url("https://gitlab.com/group/subgroup/my-app")
        self.assertEqual(parsed["type"], "gitlab")
        self.assertEqual(parsed["project_path"], "group/subgroup/my-app")
        self.assertEqual(parsed["repo"], "my-app")

    def test_parse_direct_url(self):
        parsed = parse_repo_url("https://example.com/downloads/CustomApp.dmg")
        self.assertEqual(parsed["type"], "direct")
        self.assertEqual(parsed["repo"], "CustomApp.dmg")

    def test_score_asset_disqualifies_non_mac(self):
        self.assertLess(score_asset("app-linux-amd64.tar.gz", "Darwin", "arm64"), 0)
        self.assertLess(score_asset("app-setup.exe", "Darwin", "arm64"), 0)
        self.assertLess(score_asset("app-windows-x64.zip", "Darwin", "arm64"), 0)
        self.assertLess(score_asset("app_amd64.deb", "Darwin", "arm64"), 0)
        self.assertLess(score_asset("app.dmg.blockmap", "Darwin", "arm64"), 0)
        self.assertLess(score_asset("app.dmg.sha256", "Darwin", "arm64"), 0)

    def test_score_asset_arm64_preference(self):
        score_arm = score_asset("MyApp-1.0.0-mac-arm64.dmg", "Darwin", "arm64")
        score_intel = score_asset("MyApp-1.0.0-mac-x64.dmg", "Darwin", "arm64")
        score_univ = score_asset("MyApp-1.0.0-mac-universal.dmg", "Darwin", "arm64")

        self.assertGreater(score_arm, score_intel)
        self.assertGreater(score_arm, score_univ)
        self.assertGreater(score_univ, score_intel)

    def test_score_asset_intel_disqualifies_arm(self):
        score_arm = score_asset("MyApp-1.0.0-mac-arm64.dmg", "Darwin", "x86_64")
        score_intel = score_asset("MyApp-1.0.0-mac-x64.dmg", "Darwin", "x86_64")

        self.assertLess(score_arm, 0)
        self.assertGreater(score_intel, 0)

    def test_score_asset_extension_preference(self):
        score_dmg = score_asset("MyApp-mac.dmg", "Darwin", "arm64")
        score_zip = score_asset("MyApp-mac.zip", "Darwin", "arm64")
        score_tar = score_asset("MyApp-mac.tar.gz", "Darwin", "arm64")

        self.assertGreater(score_dmg, score_zip)
        self.assertGreater(score_zip, score_tar)

    def test_select_best_asset_multi_arch(self):
        assets = [
            {"name": "app-1.0.0-linux.tar.gz", "url": "https://example.com/linux"},
            {"name": "app-1.0.0-windows.zip", "url": "https://example.com/win"},
            {"name": "app-1.0.0-mac-x64.dmg", "url": "https://example.com/mac-x64"},
            {"name": "app-1.0.0-mac-arm64.dmg", "url": "https://example.com/mac-arm64"},
        ]
        best_arm = select_best_asset(assets, target_arch="arm64")
        self.assertIsNotNone(best_arm)
        self.assertEqual(best_arm["name"], "app-1.0.0-mac-arm64.dmg")

        best_intel = select_best_asset(assets, target_arch="x86_64")
        self.assertIsNotNone(best_intel)
        self.assertEqual(best_intel["name"], "app-1.0.0-mac-x64.dmg")

    def test_check_installed_with_temp_dir(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            self.assertFalse(check_installed(dir_path, "BattGUI", "BattGUI"))

            (dir_path / "BattGUI.app").mkdir()
            self.assertTrue(check_installed(dir_path, "BattGUI", "BattGUI"))


if __name__ == "__main__":
    unittest.main()

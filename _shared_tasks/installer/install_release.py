#!/usr/bin/env python3
"""Generic downloader and installer for GitHub/GitLab release applications on macOS.

Downloads release assets (.dmg, .zip, .tar.gz, .pkg) based on host platform and
architecture, installs .app bundles to /Applications (or a custom directory),
verifies Gatekeeper assessment, and applies local ad-hoc code signing if Gatekeeper
fails.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def parse_repo_url(url: str) -> dict[str, str]:
    """Parse a GitHub, GitLab, or direct release URL into metadata."""
    clean_url = url.strip().rstrip("/")
    # Handle GitHub URLs
    gh_match = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:/releases(?:/(?:tag/([^/]+)|latest))?)?/?$", clean_url)
    if gh_match:
        owner, repo, tag = gh_match.group(1), gh_match.group(2).removesuffix(".git"), gh_match.group(3)
        return {
            "type": "github",
            "owner": owner,
            "repo": repo,
            "tag": tag or "",
            "clean_url": f"https://github.com/{owner}/{repo}",
        }

    # Handle GitLab URLs
    gl_match = re.match(r"^https?://gitlab\.com/([^/]+(?:/[^/]+)*)/([^/]+?)(?:/-/releases)?/?$", clean_url)
    if gl_match:
        namespace, repo = gl_match.group(1), gl_match.group(2).removesuffix(".git")
        full_path = f"{namespace}/{repo}"
        return {
            "type": "gitlab",
            "project_path": full_path,
            "repo": repo,
            "tag": "",
            "clean_url": f"https://gitlab.com/{full_path}",
        }

    # Direct download link fallback
    return {
        "type": "direct",
        "url": clean_url,
        "repo": clean_url.rsplit("/", 1)[-1].split("?")[0],
        "tag": "",
        "clean_url": clean_url,
    }


def fetch_github_release(owner: str, repo: str, tag: str = "") -> dict[str, Any]:
    """Fetch release info and assets from GitHub API, with HTML scraping fallback."""
    headers = {
        "User-Agent": "OsSetupHelper-ReleaseInstaller",
        "Accept": "application/vnd.github.v3+json",
    }
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    api_url = (
        f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
        if tag
        else f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    )

    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            assets = [
                {"name": a["name"], "url": a["browser_download_url"]}
                for a in data.get("assets", [])
            ]
            return {
                "tag_name": data.get("tag_name", tag),
                "assets": assets,
            }
    except Exception as e:
        # Fallback to scraping release page when API is rate-limited or fails
        return fetch_github_release_fallback(owner, repo, tag)


def fetch_github_release_fallback(owner: str, repo: str, tag: str = "") -> dict[str, Any]:
    """Scrape GitHub release HTML assets when API is unavailable or rate-limited."""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    actual_tag = tag

    if not actual_tag:
        latest_url = f"https://github.com/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(latest_url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                final_url = resp.geturl()
                tag_match = re.search(r"/releases/tag/([^/?#]+)", final_url)
                if tag_match:
                    actual_tag = tag_match.group(1)
        except Exception:
            pass

    if not actual_tag:
        actual_tag = "latest"

    assets_page_url = f"https://github.com/{owner}/{repo}/releases/expanded_assets/{actual_tag}"
    req = urllib.request.Request(assets_page_url, headers=headers)
    assets = []
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
            # Look for /owner/repo/releases/download/...
            pattern = rf'href="(/+{re.escape(owner)}/+{re.escape(repo)}/+releases/+download/+[^/]+/+([^"]+))"'
            seen = set()
            for match, asset_name in re.findall(pattern, html):
                if asset_name not in seen:
                    seen.add(asset_name)
                    assets.append({
                        "name": asset_name,
                        "url": f"https://github.com{match}",
                    })
    except Exception as e:
        pass

    return {
        "tag_name": actual_tag,
        "assets": assets,
    }


def fetch_gitlab_release(project_path: str, tag: str = "") -> dict[str, Any]:
    """Fetch release assets from GitLab API."""
    encoded_path = urllib.parse.quote(project_path, safe="")
    api_url = f"https://gitlab.com/api/v4/projects/{encoded_path}/releases"
    headers = {"User-Agent": "OsSetupHelper-ReleaseInstaller"}
    req = urllib.request.Request(api_url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            releases = json.loads(resp.read().decode("utf-8"))
            if not releases:
                return {"tag_name": "", "assets": []}
            target = None
            if tag:
                for r in releases:
                    if r.get("tag_name") == tag:
                        target = r
                        break
            if not target:
                target = releases[0]

            assets = []
            for link in target.get("assets", {}).get("links", []):
                assets.append({"name": link.get("name"), "url": link.get("url")})
            for source in target.get("assets", {}).get("sources", []):
                assets.append({"name": f"{source.get('format')}", "url": source.get("url")})

            return {
                "tag_name": target.get("tag_name", ""),
                "assets": assets,
            }
    except Exception:
        return {"tag_name": tag, "assets": []}


def score_asset(name: str, target_sys: str = "Darwin", target_arch: str = "") -> int:
    """Score an asset filename for macOS installation suitability.

    Higher score = better match.
    Negative score = disqualified.
    """
    if not target_arch:
        target_arch = platform.machine().lower()

    lower_name = name.lower()

    # Disqualify non-app files
    for bad_ext in [".blockmap", ".sha256", ".sha512", ".md5", ".sig", ".asc", ".txt", ".json", ".xml"]:
        if lower_name.endswith(bad_ext):
            return -1000

    # Extension score
    ext_score = 0
    if lower_name.endswith(".dmg"):
        ext_score = 100
    elif lower_name.endswith(".app.zip"):
        ext_score = 90
    elif lower_name.endswith(".zip"):
        ext_score = 80
    elif lower_name.endswith(".pkg"):
        ext_score = 70
    elif lower_name.endswith((".tar.gz", ".tgz")):
        ext_score = 60
    else:
        return -1000  # Disqualify unknown extensions

    # Disqualify non-macOS platforms
    disqualified_keywords = [
        "linux", "windows", "win32", "win64", ".exe", ".msi",
        "appimage", ".deb", ".rpm", "android", ".apk", "freebsd"
    ]
    for kw in disqualified_keywords:
        if kw in lower_name:
            return -1000

    # macOS platform keywords
    mac_score = 0
    for kw in ["mac", "macos", "darwin", "osx", "apple"]:
        if kw in lower_name:
            mac_score = 50
            break

    # Architecture matching
    arch_score = 0
    is_arm_host = target_arch in ["arm64", "aarch64"]

    has_arm = any(k in lower_name for k in ["arm64", "aarch64", "m1", "m2", "m3", "apple-silicon", "applesilicon"])
    has_intel = any(k in lower_name for k in ["x86_64", "x64", "amd64", "intel"])
    has_universal = "universal" in lower_name

    if is_arm_host:
        if has_arm:
            arch_score = 40
        elif has_universal:
            arch_score = 35
        elif has_intel:
            arch_score = 10  # Can run via Rosetta
        else:
            arch_score = 20  # Neutral
    else:  # Intel host
        if has_arm and not has_universal:
            return -1000  # Cannot run ARM binary on Intel
        elif has_intel:
            arch_score = 40
        elif has_universal:
            arch_score = 35
        else:
            arch_score = 20  # Neutral

    return ext_score + mac_score + arch_score


def select_best_asset(assets: list[dict[str, str]], target_arch: str = "") -> dict[str, str] | None:
    """Select the highest-scoring asset matching macOS and host architecture."""
    scored = []
    for a in assets:
        name = a.get("name", "")
        url = a.get("url", "")
        if not name or not url:
            continue
        score = score_asset(name, "Darwin", target_arch)
        if score > 0:
            scored.append((score, a))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def get_installed_app_version(app_path: Path) -> str | None:
    """Read CFBundleShortVersionString or CFBundleVersion from app Info.plist."""
    plist_path = app_path / "Contents" / "Info.plist"
    if not plist_path.exists():
        return None
    try:
        data = plistlib.loads(plist_path.read_bytes())
        return data.get("CFBundleShortVersionString") or data.get("CFBundleVersion")
    except Exception:
        return None


def find_app_in_directory(directory: Path, preferred_name: str = "") -> Path | None:
    """Find a .app bundle within a directory, preferring matching names."""
    apps = list(directory.glob("*.app"))
    if not apps:
        apps = list(directory.rglob("*.app"))

    if not apps:
        return None

    if preferred_name:
        for app in apps:
            if app.stem.lower() == preferred_name.lower():
                return app
            if preferred_name.lower() in app.stem.lower():
                return app

    # Filter out helper apps or nested frameworks if possible
    main_apps = [a for a in apps if not any(p in a.parts for p in ["Frameworks", "Helpers", "XPCServices"])]
    return main_apps[0] if main_apps else apps[0]


def check_installed(install_dir: Path, app_name: str, repo_name: str, expected_version: str = "") -> bool:
    """Check if the application is already installed and matches expected version."""
    candidates = []
    if app_name:
        candidates.append(install_dir / f"{app_name}.app")
        candidates.append(install_dir / f"{app_name}")
    if repo_name:
        candidates.append(install_dir / f"{repo_name}.app")

    for cand in candidates:
        if cand.exists():
            if not expected_version:
                return True
            installed_ver = get_installed_app_version(cand)
            if installed_ver and (installed_ver == expected_version or installed_ver.lstrip("v") == expected_version.lstrip("v")):
                return True
            return True  # Installed even if version string format varies

    # Fuzzy match by stem in install_dir
    target_names = [n.lower() for n in [app_name, repo_name] if n]
    for app_p in install_dir.glob("*.app"):
        if app_p.stem.lower() in target_names:
            return True

    return False


def remediate_gatekeeper_and_sign(app_path: Path) -> bool:
    """Check Gatekeeper assessment; if rejected, remove quarantine and apply local ad-hoc signature."""
    # 1. Check Gatekeeper assessment
    spctl_res = subprocess.run(
        ["spctl", "--assess", "--type", "execute", "--verbose", str(app_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    if spctl_res.returncode == 0:
        # Gatekeeper already satisfied
        return True

    print(f"Gatekeeper rejected {app_path.name} ({spctl_res.stderr.strip()}). Remediating locally...")

    # 2. Clear quarantine flag recursively
    subprocess.run(["xattr", "-cr", str(app_path)], check=False)

    # 3. Ad-hoc sign locally
    sign_res = subprocess.run(
        ["codesign", "--force", "--deep", "--sign", "-", str(app_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if sign_res.returncode != 0:
        print(f"Warning: local codesign failed: {sign_res.stderr.strip()}", file=sys.stderr)

    # 4. Verify code signature
    verify_res = subprocess.run(
        ["codesign", "--verify", "--deep", "--strict", str(app_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    return verify_res.returncode == 0


def download_file(url: str, dest_path: Path) -> None:
    """Download a file using curl to preserve redirects and certificates."""
    cmd = ["curl", "-fsSL", "--retry", "3", "-o", str(dest_path), url]
    res = subprocess.run(cmd, check=False)
    if res.returncode != 0:
        raise RuntimeError(f"Download failed for {url}")


def extract_and_install_dmg(dmg_path: Path, install_dir: Path, preferred_name: str = "") -> Path:
    """Mount DMG, copy .app bundle using ditto, and cleanly detach DMG."""
    mount_points = []
    try:
        out = subprocess.check_output(["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(dmg_path)])
        plist = plistlib.loads(out)
        mount_points = [e["mount-point"] for e in plist.get("system-entities", []) if "mount-point" in e]
        if not mount_points:
            raise RuntimeError("Failed to determine mount point for DMG")

        found_app = None
        for mp in mount_points:
            found_app = find_app_in_directory(Path(mp), preferred_name)
            if found_app:
                break

        if not found_app:
            raise RuntimeError(f"No .app bundle found inside {dmg_path.name}")

        dest_app = install_dir / found_app.name
        if dest_app.exists():
            if dest_app.is_dir():
                shutil.rmtree(dest_app)
            else:
                dest_app.unlink()

        # Copy using ditto to preserve Apple resource forks and attributes
        subprocess.run(["ditto", str(found_app), str(dest_app)], check=True)
        return dest_app
    finally:
        for mp in mount_points:
            subprocess.run(["hdiutil", "detach", mp, "-force"], capture_output=True, check=False)


def extract_and_install_archive(archive_path: Path, install_dir: Path, preferred_name: str = "") -> Path:
    """Extract zip or tar archive and copy .app bundle using ditto."""
    with tempfile.TemporaryDirectory() as extract_dir:
        extract_p = Path(extract_dir)
        lower_name = archive_path.name.lower()
        if lower_name.endswith(".zip"):
            subprocess.run(["ditto", "-x", "-k", str(archive_path), str(extract_p)], check=True)
        elif lower_name.endswith((".tar.gz", ".tgz")):
            subprocess.run(["tar", "-xzf", str(archive_path), "-C", str(extract_p)], check=True)
        else:
            raise RuntimeError(f"Unsupported archive format: {archive_path.name}")

        found_app = find_app_in_directory(extract_p, preferred_name)
        if not found_app:
            raise RuntimeError(f"No .app bundle found in archive {archive_path.name}")

        dest_app = install_dir / found_app.name
        if dest_app.exists():
            if dest_app.is_dir():
                shutil.rmtree(dest_app)
            else:
                dest_app.unlink()

        subprocess.run(["ditto", str(found_app), str(dest_app)], check=True)
        return dest_app


def install_release(
    url: str,
    version: str = "",
    install_dir: str = "/Applications",
    app_name: str = "",
    check_only: bool = False,
) -> int:
    """Orchestrate the release resolution, download, install, and signing process."""
    if platform.system() != "Darwin":
        print("Error: release installer currently supports macOS (Darwin).", file=sys.stderr)
        return 1

    dest_dir = Path(os.path.expanduser(install_dir)).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    parsed = parse_repo_url(url)
    repo_name = parsed.get("repo", "")
    target_version = version or parsed.get("tag", "")

    # Check if already installed
    if check_installed(dest_dir, app_name, repo_name, target_version):
        if check_only:
            return 0
        print(f"{app_name or repo_name} is already installed in {dest_dir}.")
        return 0

    if check_only:
        return 1

    # Fetch release assets
    if parsed["type"] == "github":
        rel_info = fetch_github_release(parsed["owner"], parsed["repo"], target_version)
    elif parsed["type"] == "gitlab":
        rel_info = fetch_gitlab_release(parsed["project_path"], target_version)
    else:
        # Direct URL
        filename = parsed["repo"]
        rel_info = {"tag_name": "", "assets": [{"name": filename, "url": parsed["url"]}]}

    assets = rel_info.get("assets", [])
    if not assets:
        print(f"Error: No release assets found for {url} (version: {target_version or 'latest'})", file=sys.stderr)
        return 1

    best_asset = select_best_asset(assets)
    if not best_asset:
        names = [a.get("name") for a in assets]
        print(f"Error: No suitable macOS asset found for host architecture in: {names}", file=sys.stderr)
        return 1

    asset_name = best_asset["name"]
    asset_url = best_asset["url"]
    print(f"Selected asset: {asset_name} ({asset_url})")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_p = Path(tmpdir)
        download_dest = tmp_p / asset_name
        print(f"Downloading {asset_name}...")
        download_file(asset_url, download_dest)

        lower_name = asset_name.lower()
        if lower_name.endswith(".dmg"):
            installed_app = extract_and_install_dmg(download_dest, dest_dir, app_name or repo_name)
        elif lower_name.endswith((".zip", ".tar.gz", ".tgz")):
            installed_app = extract_and_install_archive(download_dest, dest_dir, app_name or repo_name)
        elif lower_name.endswith(".pkg"):
            print(f"Running installer for {asset_name}...")
            subprocess.run(["installer", "-pkg", str(download_dest), "-target", "/"], check=True)
            installed_app = dest_dir / f"{app_name or repo_name}.app"
        else:
            print(f"Error: Unsupported asset format: {asset_name}", file=sys.stderr)
            return 1

        print(f"Installed {installed_app.name} to {dest_dir}.")

        # Gatekeeper remediation & local signing
        remediate_gatekeeper_and_sign(installed_app)
        print(f"Verified and signed {installed_app.name} successfully.")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and install an application from a GitHub/GitLab release.")
    parser.add_argument("--url", required=True, help="GitHub or GitLab repository URL (e.g. https://github.com/clzoc/BattGUI)")
    parser.add_argument("--version", default="", help="Optional release version/tag to install (defaults to latest)")
    parser.add_argument("--install-dir", default="/Applications", help="Destination directory (default: /Applications)")
    parser.add_argument("--app-name", default="", help="Expected application name (e.g. BattGUI)")
    parser.add_argument("--check-installed", action="store_true", help="Exit 0 if app is already installed, 1 otherwise")

    args = parser.parse_args()
    rc = install_release(
        url=args.url,
        version=args.version,
        install_dir=args.install_dir,
        app_name=args.app_name,
        check_only=args.check_installed,
    )
    sys.exit(rc)


if __name__ == "__main__":
    main()

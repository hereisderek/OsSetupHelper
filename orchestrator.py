#!/usr/bin/env python3
"""Enhanced local orchestrator for Ansible-driven OS setup."""

from __future__ import annotations
import argparse
import getpass
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"
BOOTSTRAP_PLAYBOOK = PROJECT_ROOT / "bootstrap.yml"
RESUME_FILE = Path(tempfile.gettempdir()) / ".ossetup_resume.yaml"
CURRENT_OS = platform.system()
OS_KEY = "mac" if CURRENT_OS == "Darwin" else "win" if CURRENT_OS == "Windows" else "linux"


def is_url(source: str) -> bool:
    parsed = urllib.parse.urlparse(source)
    return parsed.scheme in {"http", "https"}


def maybe_raw_github_url(source: str) -> str:
    if "github.com" in source and "/blob/" in source:
        return source.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return source


def update_config_submodule(repo_url: str) -> None:
    """Update the config submodule to point to a new repository URL."""
    print(f"\nUpdating config submodule to: {repo_url}")
    try:
        # Check if project root is a git repo.
        if not (PROJECT_ROOT / ".git").exists():
            print("Warning: Project root is not a git repository. Cannot use git submodule for config.")
            return

        # Ensure config is tracked as a submodule with the correct URL
        # Update .gitmodules so future clones/pulls use the user's repo
        subprocess.run(["git", "submodule", "set-url", "config", repo_url], cwd=PROJECT_ROOT, check=True)
        
        if not CONFIG_DIR.exists() or not (CONFIG_DIR / ".git").exists():
            if CONFIG_DIR.exists():
                import shutil
                shutil.rmtree(CONFIG_DIR)
            subprocess.run(["git", "submodule", "add", "--force", repo_url, "config"], cwd=PROJECT_ROOT, check=True)
        else:
            # Update the remote URL in the actual submodule directory
            subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=CONFIG_DIR, check=True)
            subprocess.run(["git", "fetch", "origin"], cwd=CONFIG_DIR, check=True)
            
            # Try to checkout main or master
            current_branch = ""
            for branch in ["main", "master"]:
                res = subprocess.run(["git", "checkout", branch], cwd=CONFIG_DIR, capture_output=True)
                if res.returncode == 0:
                    current_branch = branch
                    break
            
            if current_branch:
                subprocess.run(["git", "pull", "origin", current_branch], cwd=CONFIG_DIR, check=True)
            else:
                subprocess.run(["git", "pull", "origin"], cwd=CONFIG_DIR, check=True)
        
        # Synchronize submodule configuration
        subprocess.run(["git", "submodule", "sync", "config"], cwd=PROJECT_ROOT, check=True)
        print(f"Successfully reconfigured config submodule to {repo_url}")
                
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to update config submodule: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while updating config: {e}")


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merges two dictionaries, combining lists and supporting blacklisting."""
    for key, value in overrides.items():
        if isinstance(value, dict) and key in base and isinstance(base[key], dict):
            deep_merge(base[key], value)
        elif isinstance(value, list) and key in base and isinstance(base[key], list):
            # Combine lists and handle blacklisting
            base_list = list(base[key])
            for item in value:
                if isinstance(item, str) and item.startswith("!"):
                    # Blacklist string item
                    rem = item[1:]
                    if rem in base_list:
                        base_list.remove(rem)
                elif isinstance(item, dict):
                    # Blacklist dict item by matching 'id' or 'name'
                    match_key = "id" if "id" in item else "name" if "name" in item else None
                    is_exclusion = item.get("exclude") or (match_key and str(item.get(match_key)).startswith("!"))
                    
                    val_to_match = item.get(match_key)
                    if match_key and str(val_to_match).startswith("!"):
                        val_to_match = str(val_to_match)[1:]
                        if match_key == "id" and val_to_match.isdigit():
                            val_to_match = int(val_to_match)

                    if is_exclusion:
                        if match_key:
                            base_list = [b for b in base_list if not (isinstance(b, dict) and b.get(match_key) == val_to_match)]
                    else:
                        # Add or update dict
                        exists = False
                        if match_key:
                            for i, b in enumerate(base_list):
                                if isinstance(b, dict) and b.get(match_key) == item.get(match_key):
                                    base_list[i] = deep_merge(dict(b), item)
                                    exists = True
                                    break
                        if not exists and item not in base_list:
                            base_list.append(item)
                else:
                    if item not in base_list:
                        base_list.append(item)
            base[key] = base_list
        else:
            base[key] = value
    return base


def load_config_with_overrides() -> dict[str, Any]:
    """Loads configuration with priority: config/config.override.yaml > config.override.yaml > config/config.yaml > config.yaml"""
    priority_list = [
        PROJECT_ROOT / "config.yaml",
        CONFIG_DIR / "config.yaml",
        PROJECT_ROOT / "config.override.yaml",
        CONFIG_DIR / "config.override.yaml",
    ]
    
    final_config: dict[str, Any] = {}
    found_any = False
    
    for p in priority_list:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as handle:
                    data = yaml.safe_load(handle)
                    if isinstance(data, dict):
                        final_config = deep_merge(final_config, data)
                        found_any = True
            except Exception as e:
                print(f"Warning: Failed to load {p}: {e}")
                
    if not found_any:
        raise FileNotFoundError("No configuration files found (checked root config.yaml and config/config.yaml)")
        
    return final_config


def load_yaml_source(source: str | Path) -> dict[str, Any]:
    source_str = str(source)
    if is_url(source_str):
        # If the URL ends in .git, treat it as a submodule update request
        if source_str.endswith(".git") or "/github.com/" in source_str and "/blob/" not in source_str:
            update_config_submodule(source_str)
            source_str = str(CONFIG_DIR / "config.yaml")
        else:
            source_str = maybe_raw_github_url(source_str)
            with urllib.request.urlopen(source_str, timeout=30) as response:
                payload = response.read().decode("utf-8")
                data = yaml.safe_load(payload)
                return data

    source_path = Path(source_str)
    if not source_path.exists():
        default_config_path = str(CONFIG_DIR / "config.yaml")
        if source_str == default_config_path:
            # If default config is missing, maybe it's a new submodule clone?
            print(f"Warning: Default configuration '{source_str}' not found.")
            # If config.bak exists, restore it
            bak_path = PROJECT_ROOT / "config.bak" / "config.yaml"
            if bak_path.exists():
                print("Restoring from backup...")
                source_path.parent.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.copy(bak_path, source_path)
            else:
                # Still missing, perhaps we should use a minimal fallback?
                raise FileNotFoundError(f"Configuration file not found: {source_str}. Please ensure your config repository has a config.yaml file.")
        else:
            raise FileNotFoundError(f"Configuration file not found: {source_str}")

    with open(source_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a YAML mapping.")
    return data


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized.setdefault("meta", {})
    normalized.setdefault("execution", {})
    normalized.setdefault("selections", {})

    for key in ["apps", "commandline_tools", "settings"]:
        normalized["selections"].setdefault(key, {})
        section = normalized["selections"][key]
        if isinstance(section, dict):
            for item in list(section.keys()):
                # Handle syntax like 'mole: false'
                if isinstance(section[item], bool):
                    section[item] = {"enabled": section[item]}
                elif section[item] is None:
                    section[item] = {"enabled": False}
                elif isinstance(section[item], dict):
                    section[item].setdefault("enabled", False)
        else:
            normalized["selections"][key] = {}

    normalized["execution"].setdefault("always_elevated", False)
    return normalized


def get_discovered_roles() -> dict[str, list[str]]:
    """Scan the filesystem to discover roles for the current OS."""
    categories = {
        "apps": ["common", OS_KEY],
        "commandline_tools": ["common", OS_KEY],
        "settings": ["common", OS_KEY]
    }
    
    discovered = {
        "discovered_apps_common": [],
        "discovered_apps_os": [],
        "discovered_commandline_tools_common": [],
        "discovered_commandline_tools_os": [],
        "discovered_settings_common": [],
        "discovered_settings_os": []
    }
    
    for cat, subdirs in categories.items():
        for subdir in subdirs:
            path = PROJECT_ROOT / cat / subdir
            key = f"discovered_{cat}_{'common' if subdir == 'common' else 'os'}"
            if path.exists():
                for item in path.iterdir():
                    if item.is_dir() and not item.name.startswith(("_", ".")):
                        discovered[key].append(item.name)
            discovered[key] = sorted(list(set(discovered[key])))
            
    return discovered


def get_applicable_roles() -> dict[str, list[str]]:
    """Flatten discovered roles into sections for the UI."""
    discovered = get_discovered_roles()
    return {
        "apps": sorted(list(set(discovered["discovered_apps_common"] + discovered["discovered_apps_os"]))),
        "commandline_tools": sorted(list(set(discovered["discovered_commandline_tools_common"] + discovered["discovered_commandline_tools_os"]))),
        "settings": sorted(list(set(discovered["discovered_settings_common"] + discovered["discovered_settings_os"])))
    }


def check_installed(role_name: str, section_key: str) -> bool:
    """Check if a role is already installed."""
    if section_key not in ["apps", "commandline_tools"]:
        return False

    possible_dirs = [
        PROJECT_ROOT / "apps" / "common" / role_name,
        PROJECT_ROOT / "apps" / OS_KEY / role_name,
        PROJECT_ROOT / "commandline_tools" / "common" / role_name,
        PROJECT_ROOT / "commandline_tools" / OS_KEY / role_name,
    ]

    defaults = {}
    for d in possible_dirs:
        p = d / "defaults" / "main.yml"
        if p.exists():
            with open(p, "r", encoding="utf-8") as handle:
                try:
                    role_defaults = yaml.safe_load(handle) or {}
                    defaults.update(role_defaults)
                except Exception:
                    pass

    if section_key == "apps":
        if CURRENT_OS == "Darwin":
            app_name = defaults.get("app_name_mac") or defaults.get("app_name")
            if app_name:
                for base in ["/Applications", f"{Path.home()}/Applications"]:
                    if (Path(base) / f"{app_name}.app").exists():
                        return True
            pkg_name = defaults.get("app_pkg_mac") or defaults.get("app_pkg")
            if pkg_name:
                try:
                    res = subprocess.run(["brew", "list", "--cask", pkg_name], capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        return True
                except FileNotFoundError:
                    pass
        elif CURRENT_OS == "Windows":
            pkg_name = defaults.get("app_pkg_win") or defaults.get("app_pkg")
            if pkg_name:
                try:
                    res = subprocess.run(["winget", "list", "-q", pkg_name], capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        return True
                except FileNotFoundError:
                    pass
        elif CURRENT_OS == "Linux":
            pkg_name = defaults.get("app_pkg_linux") or defaults.get("app_pkg")
            if pkg_name:
                if shutil.which("dpkg"):
                    res = subprocess.run(["dpkg", "-s", pkg_name], capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        return True
                if shutil.which(pkg_name):
                    return True

    if shutil.which(role_name):
        return True

    for key in ["binary_name", "tool_name", "pkg_name"]:
        if key in defaults and defaults[key] and shutil.which(defaults[key]):
            return True

    return False


def prompt_toggle(name: str, default: bool) -> bool:
    default_text = "Y/n" if default else "y/N"
    while True:
        raw = input(f"Enable {name}? [{default_text}] ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Please answer y or n.")


def apply_interactive_selection(config: dict[str, Any]) -> dict[str, Any]:
    applicable_roles = get_applicable_roles()
    selected = dict(config)
    sections = [
        ("apps", "App selection"),
        ("commandline_tools", "Commandline tool selection"),
        ("settings", "Settings selection"),
    ]

    for section_key, title in sections:
        all_items = selected["selections"].get(section_key, {})
        valid_role_names = applicable_roles.get(section_key, [])

        # Filter items to only those that are applicable
        items = {k: v for k, v in all_items.items() if k in valid_role_names}

        # Add missing roles
        for role in valid_role_names:
            if role not in items:
                items[role] = {"enabled": False}

        if not items:
            continue

        print(f"\n{title}")
        print("-" * len(title))
        for item_name in sorted(items.keys()):
            item_cfg = items.get(item_name) or {}
            is_installed = check_installed(item_name, section_key)
            current = bool(item_cfg.get("enabled", False))

            prompt_name = item_name
            if is_installed:
                prompt_name += " [Already installed]"

            item_cfg["enabled"] = prompt_toggle(prompt_name, current)
            
            # If it's an app and we enabled it, ask about Dock
            if section_key == "apps" and item_cfg["enabled"] and CURRENT_OS == "Darwin":
                dock_default = item_cfg.get("add_to_dock", False)
                item_cfg["add_to_dock"] = prompt_toggle(f"  -> Pin '{item_name}' to Dock?", dock_default)

            items[item_name] = item_cfg

        selected["selections"][section_key] = items

    return selected


def save_resume_config(config: dict[str, Any]) -> None:
    try:
        with open(RESUME_FILE, "w", encoding="utf-8") as handle:
            yaml.safe_dump(config, handle, sort_keys=False)
    except Exception as exc:
        print(f"Warning: Failed to save resume config: {exc}")


def load_resume_config() -> dict[str, Any] | None:
    if RESUME_FILE.exists():
        try:
            with open(RESUME_FILE, "r", encoding="utf-8") as handle:
                return yaml.safe_load(handle)
        except Exception:
            pass
    return None


def write_temp_vars_file(config: dict[str, Any]) -> str:
    fd, path = tempfile.mkstemp(prefix="ossetup-vars-", suffix=".yml")
    os.close(fd)
    os.chmod(path, 0o600)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    return path


def build_ansible_command(vars_file: str, always_elevated: bool, ask_become_pass: bool, 
                          become_pass_file: str | None = None, roles_metadata: dict[str, list[str]] | None = None,
                          results_file: str | None = None) -> list[str]:
    interpreter = sys.executable
    
    # If the interpreter is inside the PROJECT_ROOT, use a relative path
    # to avoid space issues in absolute paths during Ansible module execution
    try:
        rel_path = Path(interpreter).relative_to(PROJECT_ROOT)
        # Use ./ to ensure it's treated as a path relative to the current working directory
        interpreter_arg = f"./{rel_path}"
    except ValueError:
        # Not relative to project root, use absolute
        interpreter_arg = interpreter
    
    command = [
        interpreter,
        "-m",
        "ansible",
        "playbook",
        "-i",
        "localhost,",
        "-c",
        "local",
        "-e",
        f"@{vars_file}",
        "-e",
        f"ansible_python_interpreter={interpreter_arg}",
        "-e",
        f"os_key={OS_KEY}",
    ]
    
    if results_file:
        command += ["-e", f"ossetup_results_file={results_file}"]
    
    # Add discovered roles metadata
    if roles_metadata:
        for k, v in roles_metadata.items():
            # Use JSON dumps and wrap in single quotes to ensure Ansible 
            # interprets the entire string as a JSON list even with spaces
            val = json.dumps(v)
            command += ["-e", f"{k}='{val}'"]

    command.append(str(BOOTSTRAP_PLAYBOOK))

    if always_elevated:
        command.insert(-1, "-b")
    if ask_become_pass:
        if become_pass_file:
            command.insert(-1, f"--become-password-file={become_pass_file}")
        else:
            command.insert(-1, "-K")
    return command


def run_ansible(command: list[str], env: dict[str, str] | None = None) -> int:
    print("\nExecuting:")
    print(" ".join(command))
    
    # Use provided env or current system env
    run_env = env if env is not None else os.environ.copy()
    
    # Ensure Homebrew is in the PATH for macOS if not already in env
    if platform.system() == "Darwin":
        brew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
        current_path = run_env.get("PATH", "")
        for bp in brew_paths:
            if bp not in current_path:
                current_path = f"{bp}:{current_path}"
        run_env["PATH"] = current_path

    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env=run_env,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
    return process.wait()


def apply_cli_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not (args.apps or args.tools or args.settings or args.all):
        return config

    overridden = dict(config)
    applicable = get_applicable_roles()
    exclude_list = args.exclude or []

    # If specific flags are used (including --all), we want to disable everything by default
    # unless it is explicitly mentioned in the flags or handled by --all.
    for key in ["apps", "commandline_tools", "settings"]:
        for item in overridden["selections"][key].values():
            item["enabled"] = False
            
    # Helper to enable roles in a section
    def enable_roles(section_key: str, role_names: list[str]):
        valid_roles = applicable.get(section_key, [])
        for role in role_names:
            if role.lower() == "all":
                for r in valid_roles:
                    if r not in exclude_list:
                        role_cfg = overridden["selections"][section_key].setdefault(r, {})
                        if args.all: # If --all was used, we still want to check if installed
                             if not check_installed(r, section_key):
                                 role_cfg["enabled"] = True
                                 # Enable all boolean flags for this role
                                 for k, v in role_cfg.items():
                                     if isinstance(v, bool):
                                         role_cfg[k] = True
                        else:
                             role_cfg["enabled"] = True
                             # Enable all boolean flags for this role
                             for k, v in role_cfg.items():
                                 if isinstance(v, bool):
                                     role_cfg[k] = True
            elif role in valid_roles and role not in exclude_list:
                role_cfg = overridden["selections"][section_key].setdefault(role, {})
                role_cfg["enabled"] = True
                # Even for specific role via CLI, we might want to enable all its flags if not already?
                # For now, just enabling the role is enough as per current CLI design.

    if args.all:
        print("\nAnalyzing roles for '--all' run...")
        enable_roles("apps", ["all"])
        enable_roles("commandline_tools", ["all"])
        enable_roles("settings", ["all"])

    if args.apps:
        enable_roles("apps", args.apps)
            
    if args.tools:
        enable_roles("commandline_tools", args.tools)
            
    if args.settings:
        enable_roles("settings", args.settings)

    return overridden


def show_summary_and_confirm(config: dict[str, Any], skip_confirmation: bool) -> bool:
    """Show a summary of what will be executed and ask for confirmation."""
    print("\n" + "="*40)
    print("🚀 EXECUTION SUMMARY")
    print("="*40)
    
    any_enabled = False
    for section in ["apps", "commandline_tools", "settings"]:
        enabled = [k for k, v in config["selections"].get(section, {}).items() if v.get("enabled")]
        if enabled:
            any_enabled = True
            title = section.replace('_', ' ').capitalize()
            print(f"\n{title}:")
            for item in sorted(enabled):
                print(f"  - {item}")
    
    if not any_enabled:
        print("\nNo new items selected for installation (everything may already be installed).")
        return False

    print("\n" + "="*40)
    if skip_confirmation:
        return True
        
    resp = input("Proceed with these changes? [Y/n] ").strip().lower()
    return not resp or resp in {"y", "yes"}


def ask_save_final_config(config: dict[str, Any]) -> None:
    resp = input("\nDo you want to save the current selection to a custom configuration file? [y/N] ").strip().lower()
    if resp in {"y", "yes"}:
        path_str = input("Enter path to save (e.g., user_config.yaml): ").strip()
        if path_str:
            try:
                path = Path(path_str).expanduser().resolve()
                # Ensure parent directory exists
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "w", encoding="utf-8") as handle:
                    yaml.safe_dump(config, handle, sort_keys=False)
                print(f"Configuration saved to {path}")
            except Exception as exc:
                print(f"Error saving configuration: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OS setup orchestrator")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to local YAML config, a Git repo URL, or a GitHub RAW URL.",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip interactive toggles and run with config defaults.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from the last interactive selection.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Install all applicable apps, tools, and settings (skips already installed).",
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Space-separated list of roles to exclude (e.g., chrome iterm).",
    )
    parser.add_argument(
        "--apps",
        nargs="+",
        help="Space-separated list of apps to install (e.g., vscode chrome). Skips interactive mode.",
    )
    parser.add_argument(
        "--tools",
        nargs="+",
        help="Space-separated list of commandline tools to install. Skips interactive mode.",
    )
    parser.add_argument(
        "--settings",
        nargs="+",
        help="Space-separated list of settings to apply. Skips interactive mode.",
    )
    parser.add_argument(
        "-K", "--ask-become-pass",
        action="store_true",
        help="Ask for privilege escalation (sudo) password.",
    )
    return parser.parse_args()


def show_post_run_summary(config: dict[str, Any], success: bool, config_source: str, detailed_results: dict[str, Any] | None = None) -> None:
    """Show a detailed summary after the Ansible run."""
    print("\n" + "✨" * 20)
    print("🏁 SETUP COMPLETE")
    print("✨" * 20)
    
    if success:
        print("\n✅ Status: SUCCESS")
    else:
        print("\n❌ Status: COMPLETED WITH ERRORS (Check the logs above for details)")

    print(f"📄 Config Source: {config_source}")
    print(f"♻️  Resume File:  {RESUME_FILE}")

    print("\n📦 Installation Report:")
    results = detailed_results or {}
    
    for section in ["apps", "commandline_tools", "settings"]:
        enabled = [k for k, v in config["selections"].get(section, {}).items() if v.get("enabled")]
        if not enabled:
            continue
            
        title = section.replace('_', ' ').capitalize()
        print(f"\n--- {title} ---")
        for item in sorted(enabled):
            # Get status from detailed results if available, otherwise assume success if playbook succeeded
            # status can be 'success', 'failed', 'skipped'
            info = results.get(item, {})
            status = info.get("status")
            message = info.get("message", "")
            
            if status == "success":
                status_icon = "✅"
            elif status == "failed":
                status_icon = "❌"
            elif status == "skipped":
                status_icon = "⏭️ "
            else:
                status_icon = "✅" if success else "❓"

            details = []
            cfg = config["selections"][section][item]
            if section == "apps" and CURRENT_OS == "Darwin":
                if cfg.get("add_to_dock"):
                    # Check if actually pinned (reported by role)
                    if info.get("pinned"):
                        details.append("pinned to dock")
                    else:
                        details.append("add-to-dock enabled")
            
            if info.get("path_added"):
                details.append("added to PATH")
            if info.get("env_added"):
                details.append("added to ENV")
            
            detail_str = f" ({', '.join(details)})" if details else ""
            msg_str = f" - {message}" if message else ""
            print(f"  {status_icon} {item}{detail_str}{msg_str}")

    print("\n" + "="*40)
    if success:
        print("Your system is now configured! You may need to restart your")
        print("terminal or log out/in for all changes to take effect.")
    else:
        print("Some tasks encountered issues. Please review the output above.")
    print("="*40 + "\n")


def needs_sudo_password() -> bool:
    """Check if sudo requires a password."""
    if platform.system() == "Windows":
        return False
    if hasattr(os, 'getuid') and os.getuid() == 0:
        return False
    try:
        # -n means non-interactive, will fail if password is required
        res = subprocess.run(["sudo", "-n", "true"], capture_output=True)
        return res.returncode != 0
    except Exception:
        return True


def main() -> int:
    args = parse_args()
    
    # Check if sudo password is likely needed and not provided
    sudo_password = None
    if not args.ask_become_pass and not args.non_interactive and CURRENT_OS != "Windows":
        if needs_sudo_password():
            print("\n🔐 Privilege escalation (sudo) usually requires a password on this system.")
            resp = input("Do you want to enter the sudo password now to avoid multiple prompts? [Y/n] ").strip().lower()
            if not resp or resp in {"y", "yes"}:
                sudo_password = getpass.getpass("Enter sudo password: ")
                args.ask_become_pass = True

    # Discovered roles for dynamic playbook execution
    discovered_metadata = get_discovered_roles()

    # Proactively initialize submodules if config is missing and we are in a git repo
    if args.config is None:
        if not (PROJECT_ROOT / "config.yaml").exists() and not (CONFIG_DIR / "config.yaml").exists():
            if (PROJECT_ROOT / ".git").exists():
                print("Default configuration missing. Attempting to initialize submodules...")
                try:
                    subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=PROJECT_ROOT, check=True)
                except subprocess.CalledProcessError:
                    print("Warning: Could not initialize submodules automatically.")
    
    # Handle Resume Logic
    resume_config = None
    config_source = args.config if args.config else "Default (merged)"
    if args.resume:
        resume_config = load_resume_config()
        if not resume_config:
            print("No resume configuration found.")
        else:
            config_source = "Last session (Resume)"
    elif not (args.apps or args.tools or args.settings or args.non_interactive or args.all) and RESUME_FILE.exists():
        resp = input("Found a previous selection. Do you want to resume? [Y/n] ").strip().lower()
        if not resp or resp in {"y", "yes"}:
            resume_config = load_resume_config()
            if resume_config:
                config_source = "Last session (Resume)"
                print("\nPrevious selections found:")
                for section in ["apps", "commandline_tools", "settings"]:
                    enabled = [k for k, v in resume_config["selections"].get(section, {}).items() if v.get("enabled")]
                    if enabled:
                        print(f"  {section.replace('_', ' ').capitalize()}: {', '.join(enabled)}")
                
                resp2 = input("\nDo you want to: [1] Continue with these selections, [2] Start over? [1] ").strip()
                if resp2 == "2":
                    resume_config = None
                    config_source = args.config if args.config else "Default (merged)"

    if resume_config:
        config = resume_config
    else:
        try:
            if args.config:
                config = normalize_config(load_yaml_source(args.config))
            else:
                config = normalize_config(load_config_with_overrides())
        except Exception as exc:
            print(f"Failed to load config: {exc}")
            return 2

    if args.apps or args.tools or args.settings or args.all:
        config = apply_cli_overrides(config, args)
    elif not args.non_interactive and not (args.resume or resume_config):
        config = apply_interactive_selection(config)

    # Show summary and confirm before proceeding (only for CLI-driven or Interactive runs)
    if not args.non_interactive:
        if not show_summary_and_confirm(config, args.yes):
            print("Execution cancelled.")
            return 0

    save_resume_config(config)

    vars_file = write_temp_vars_file(config)
    
    # Create a temporary results file for Ansible to report back
    fd, results_file = tempfile.mkstemp(prefix="ossetup-results-", suffix=".json")
    os.close(fd)
    # Initialize with empty dict
    with open(results_file, "w") as f:
        json.dump({}, f)
    
    become_pass_file = None
    askpass_file = None
    sudo_wrapper_dir = None
    
    env = os.environ.copy()
    if platform.system() == "Darwin":
        brew_paths = ["/opt/homebrew/bin", "/usr/local/bin"]
        current_path = env.get("PATH", "")
        for bp in brew_paths:
            if bp not in current_path:
                current_path = f"{bp}:{current_path}"
        env["PATH"] = current_path

    if sudo_password:
        # 1. Create Ansible become-pass file
        fd, become_pass_file = tempfile.mkstemp(prefix="ossetup-pass-", suffix=".txt")
        os.close(fd)
        os.chmod(become_pass_file, 0o600)
        with open(become_pass_file, "w", encoding="utf-8") as f:
            f.write(sudo_password)
            
    command = build_ansible_command(
        vars_file=vars_file,
        always_elevated=bool(config["execution"].get("always_elevated", True)),
        ask_become_pass=args.ask_become_pass,
        become_pass_file=become_pass_file,
        roles_metadata=discovered_metadata,
        results_file=results_file
    )

    try:
        ret = run_ansible(command, env=env)
        success = (ret == 0)
        
        # Load detailed results
        detailed_results = {}
        try:
            if os.path.exists(results_file):
                with open(results_file, "r") as f:
                    detailed_results = json.load(f)
        except Exception:
            pass

        show_post_run_summary(config, success, config_source, detailed_results)
        if success:
            ask_save_final_config(config)
        return ret
    finally:
        try:
            if vars_file and os.path.exists(vars_file):
                os.remove(vars_file)
            if become_pass_file and os.path.exists(become_pass_file):
                os.remove(become_pass_file)
            if results_file and os.path.exists(results_file):
                os.remove(results_file)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)

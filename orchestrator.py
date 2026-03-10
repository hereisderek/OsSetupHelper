#!/usr/bin/env python3
"""Enhanced local orchestrator for Ansible-driven OS setup."""

from __future__ import annotations

import argparse
import os
import platform
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
BOOTSTRAP_PLAYBOOK = PROJECT_ROOT / "bootstrap.yml"
RESUME_FILE = Path.home() / ".ossetup_resume.yaml"
CURRENT_OS = platform.system()
OS_KEY = "mac" if CURRENT_OS == "Darwin" else "win" if CURRENT_OS == "Windows" else "linux"


def is_url(source: str) -> bool:
    parsed = urllib.parse.urlparse(source)
    return parsed.scheme in {"http", "https"}


def maybe_raw_github_url(source: str) -> str:
    if "github.com" in source and "/blob/" in source:
        return source.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
    return source


def load_yaml_source(source: str) -> dict[str, Any]:
    if is_url(source):
        source = maybe_raw_github_url(source)
        with urllib.request.urlopen(source, timeout=30) as response:
            payload = response.read().decode("utf-8")
            data = yaml.safe_load(payload)
    else:
        with open(source, "r", encoding="utf-8") as handle:
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
            for item in section:
                if section[item] is None:
                    section[item] = {}
        else:
            normalized["selections"][key] = {}

    normalized["execution"].setdefault("always_elevated", False)
    return normalized


def get_applicable_roles() -> dict[str, list[str]]:
    """Extract applicable roles from bootstrap.yml based on current OS."""
    if not BOOTSTRAP_PLAYBOOK.exists():
        return {"apps": [], "commandline_tools": [], "settings": []}

    with open(BOOTSTRAP_PLAYBOOK, "r", encoding="utf-8") as handle:
        playbook = yaml.safe_load(handle)
        if not playbook or not isinstance(playbook, list):
            return {"apps": [], "commandline_tools": [], "settings": []}
        vars_dict = playbook[0].get("vars", {})

    applicable = {
        "apps": vars_dict.get("common_app_roles", []).copy(),
        "commandline_tools": vars_dict.get("common_cli_roles", []).copy(),
        "settings": vars_dict.get("common_settings_roles", []).copy()
    }

    if CURRENT_OS == "Darwin":
        applicable["apps"] += vars_dict.get("mac_app_roles", [])
        applicable["commandline_tools"] += vars_dict.get("mac_cli_roles", [])
        applicable["settings"] += vars_dict.get("mac_settings_roles", [])
    elif CURRENT_OS == "Linux":
        applicable["apps"] += vars_dict.get("linux_app_roles", [])
        applicable["commandline_tools"] += vars_dict.get("linux_cli_roles", [])
        applicable["settings"] += vars_dict.get("linux_settings_roles", [])
    elif CURRENT_OS == "Windows":
        applicable["apps"] += vars_dict.get("win_app_roles", [])
        applicable["commandline_tools"] += vars_dict.get("win_cli_roles", [])
        applicable["settings"] += vars_dict.get("win_settings_roles", [])

    return applicable


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

        # Add missing roles from bootstrap.yml
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


def build_ansible_command(vars_file: str, always_elevated: bool, ask_become_pass: bool) -> list[str]:
    command = [
        sys.executable,
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
        f"ansible_python_interpreter={sys.executable}",
        str(BOOTSTRAP_PLAYBOOK),
    ]
    if always_elevated:
        command.insert(-1, "-b")
    if ask_become_pass:
        command.insert(-1, "-K")
    return command


def run_ansible(command: list[str]) -> int:
    print("\nExecuting:")
    print(" ".join(command))
    process = subprocess.Popen(
        command,
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        print(line, end="")
    return process.wait()


def apply_cli_overrides(config: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    if not (args.apps or args.tools or args.settings):
        return config

    overridden = dict(config)

    for key in ["apps", "commandline_tools", "settings"]:
        for item in overridden["selections"][key].values():
            item["enabled"] = False

    if args.apps:
        for app in args.apps:
            overridden["selections"]["apps"].setdefault(app, {})["enabled"] = True

    if args.tools:
        for tool in args.tools:
            overridden["selections"]["commandline_tools"].setdefault(tool, {})["enabled"] = True

    if args.settings:
        for setting in args.settings:
            overridden["selections"]["settings"].setdefault(setting, {})["enabled"] = True

    return overridden


def ask_save_final_config(config: dict[str, Any]) -> None:
    resp = input("\nDo you want to save the current selection to a custom configuration file? [y/N] ").strip().lower()
    if resp in {"y", "yes"}:
        path_str = input("Enter path to save (e.g., user_config.yaml): ").strip()
        if path_str:
            try:
                path = Path(path_str).expanduser().resolve()
                with open(path, "w", encoding="utf-8") as handle:
                    yaml.safe_dump(config, handle, sort_keys=False)
                print(f"Configuration saved to {path}")
            except Exception as exc:
                print(f"Error saving configuration: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="OS setup orchestrator")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to local YAML config or a GitHub RAW URL.",
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


def main() -> int:
    args = parse_args()
    
    # Handle Resume Logic
    resume_config = None
    if args.resume:
        resume_config = load_resume_config()
        if not resume_config:
            print("No resume configuration found.")
    elif not (args.apps or args.tools or args.settings or args.non_interactive) and RESUME_FILE.exists():
        resp = input("Found a previous selection. Do you want to resume? [Y/n] ").strip().lower()
        if not resp or resp in {"y", "yes"}:
            resume_config = load_resume_config()
            if resume_config:
                print("\nPrevious selections found:")
                for section in ["apps", "commandline_tools", "settings"]:
                    enabled = [k for k, v in resume_config["selections"].get(section, {}).items() if v.get("enabled")]
                    if enabled:
                        print(f"  {section.replace('_', ' ').capitalize()}: {', '.join(enabled)}")
                
                resp2 = input("\nDo you want to: [1] Continue with these selections, [2] Start over? [1] ").strip()
                if resp2 == "2":
                    resume_config = None

    if resume_config:
        config = resume_config
    else:
        try:
            config = normalize_config(load_yaml_source(args.config))
        except Exception as exc:
            print(f"Failed to load config: {exc}")
            return 2

    if args.apps or args.tools or args.settings:
        config = apply_cli_overrides(config, args)
    elif not args.non_interactive and not (args.resume or resume_config):
        config = apply_interactive_selection(config)
    elif not args.non_interactive and resume_config:
        # We already have the config from resume, but we might want to allow re-selection?
        # The prompt above asked "Continue with these selections" or "Start over".
        # If they chose "Continue", we just use it.
        pass

    save_resume_config(config)

    vars_file = write_temp_vars_file(config)
    command = build_ansible_command(
        vars_file=vars_file,
        always_elevated=bool(config["execution"].get("always_elevated", True)),
        ask_become_pass=args.ask_become_pass,
    )

    try:
        ret = run_ansible(command)
        if ret == 0:
            ask_save_final_config(config)
        return ret
    finally:
        try:
            os.remove(vars_file)
        except OSError:
            pass


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        sys.exit(1)

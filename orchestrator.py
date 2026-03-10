#!/usr/bin/env python3
"""Minimal local orchestrator for Ansible-driven OS setup."""

from __future__ import annotations

import argparse
import os
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
            
    normalized["execution"].setdefault("always_elevated", True)
    return normalized


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
    selected = dict(config)
    sections = [
        ("apps", "App selection"),
        ("commandline_tools", "Commandline tool selection"),
        ("settings", "Settings selection"),
    ]

    for section_key, title in sections:
        items = selected["selections"].get(section_key, {})
        if not items:
            continue

        print(f"\n{title}")
        print("-" * len(title))
        for item_name in sorted(items.keys()):
            item_cfg = items.get(item_name) or {}
            current = bool(item_cfg.get("enabled", False))
            item_cfg["enabled"] = prompt_toggle(item_name, current)
            items[item_name] = item_cfg

        selected["selections"][section_key] = items

    return selected


def write_temp_vars_file(config: dict[str, Any]) -> str:
    fd, path = tempfile.mkstemp(prefix="ossetup-vars-", suffix=".yml")
    os.close(fd)
    os.chmod(path, 0o600)
    with open(path, "w", encoding="utf-8") as handle:
        yaml.safe_dump(config, handle, sort_keys=False)
    return path


def build_ansible_command(vars_file: str, always_elevated: bool) -> list[str]:
    command = [
        "ansible-playbook",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = normalize_config(load_yaml_source(args.config))
    except Exception as exc:
        print(f"Failed to load config: {exc}")
        return 2

    if not args.non_interactive:
        config = apply_interactive_selection(config)

    vars_file = write_temp_vars_file(config)
    command = build_ansible_command(
        vars_file=vars_file,
        always_elevated=bool(config["execution"].get("always_elevated", True)),
    )

    try:
        return run_ansible(command)
    finally:
        try:
            os.remove(vars_file)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())

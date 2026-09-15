#!/usr/bin/env python3
"""Enhanced local orchestrator for Ansible-driven OS setup."""

from __future__ import annotations
import argparse
import copy
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

import questionary
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
CONFIG_DIR = PROJECT_ROOT / "config"
BOOTSTRAP_PLAYBOOK = PROJECT_ROOT / "bootstrap.yml"
# The config/ submodule's default remote (see .gitmodules) — used as-is when
# the user doesn't fork their own config repo via --config <git-url>.
DEFAULT_CONFIG_REPO_URL = "https://github.com/hereisderek/OsSetupHelperConfig.git"
CATEGORIES = ["apps", "cli", "settings"]
# Role content lives in content/ (this repo) and config/content/ (the config
# repo/submodule). config/content/ is listed first so a same-named role there
# overlays/overrides the one in content/ — mirrors ansible.cfg's roles_path.
CONTENT_ROOTS = [CONFIG_DIR / "content", PROJECT_ROOT / "content"]
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


def _update_existing_clone(path: Path, repo_url: str) -> None:
    """Repoint an existing git checkout at `path` to `repo_url` and fast-forward it."""
    subprocess.run(["git", "remote", "set-url", "origin", repo_url], cwd=path, check=True)
    subprocess.run(["git", "fetch", "origin"], cwd=path, check=True)
    for branch in ["main", "master"]:
        if subprocess.run(["git", "checkout", branch], cwd=path, capture_output=True).returncode == 0:
            subprocess.run(["git", "reset", "--hard", f"origin/{branch}"], cwd=path, check=True)
            return
    subprocess.run(["git", "pull", "origin"], cwd=path, check=True)


def ensure_config_repo(repo_url: str) -> None:
    """Ensure config/ is a clone of repo_url — whether or not PROJECT_ROOT is
    itself a git repo. A plain directory copy (e.g. rsync'd to another
    machine for a quick test, no .git at all) must still be able to fetch a
    config repo on its own, not just a real git-cloned checkout of the engine
    repo. Prefers real git-submodule semantics when this checkout supports
    them; falls back to a plain clone/pull otherwise.
    """
    print(f"\nSetting up config/ from: {repo_url}")
    is_project_git_repo = (PROJECT_ROOT / ".git").exists()
    has_gitmodules = (PROJECT_ROOT / ".gitmodules").exists()
    config_is_git_repo = (CONFIG_DIR / ".git").exists()

    if is_project_git_repo and has_gitmodules:
        try:
            subprocess.run(["git", "submodule", "set-url", "config", repo_url], cwd=PROJECT_ROOT, check=True)
            if config_is_git_repo:
                _update_existing_clone(CONFIG_DIR, repo_url)
            else:
                if CONFIG_DIR.exists():
                    shutil.rmtree(CONFIG_DIR)
                subprocess.run(["git", "submodule", "update", "--init", "--force", "config"], cwd=PROJECT_ROOT, check=True)
            subprocess.run(["git", "submodule", "sync", "config"], cwd=PROJECT_ROOT, check=True)
            print(f"Successfully set up config/ via git submodule ({repo_url}).")
            return
        except subprocess.CalledProcessError as e:
            print(f"Warning: submodule-based setup failed ({e}); falling back to a plain clone...")

    # Plain clone/update fallback (also what bootstrap.sh's own submodule sync
    # does): works with or without PROJECT_ROOT being a git repo at all.
    try:
        if config_is_git_repo:
            _update_existing_clone(CONFIG_DIR, repo_url)
        else:
            if CONFIG_DIR.exists():
                shutil.rmtree(CONFIG_DIR)
            subprocess.run(["git", "clone", repo_url, str(CONFIG_DIR)], check=True)
        print(f"Successfully set up config/ ({repo_url}).")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Failed to set up config/: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while setting up config/: {e}")


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

                    # Compare as strings: YAML lets ids/names be written as
                    # either a bare number or a quoted string, and both must
                    # match each other (e.g. base id: 123 vs override id: "!123").
                    if is_exclusion:
                        if match_key:
                            base_list = [b for b in base_list if not (isinstance(b, dict) and str(b.get(match_key)) == str(val_to_match))]
                    else:
                        # Add or update dict
                        exists = False
                        if match_key:
                            for i, b in enumerate(base_list):
                                if isinstance(b, dict) and str(b.get(match_key)) == str(item.get(match_key)):
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
    """Loads configuration from the config/ submodule: config.yaml, then config.override.yaml on top.

    All user config lives in config/ (a checkout of the config repo — the
    user's own fork, or DEFAULT_CONFIG_REPO_URL as the fallback). This repo
    ships no config of its own.
    """
    priority_list = [
        CONFIG_DIR / "config.yaml",
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
        raise FileNotFoundError(
            f"No configuration found in {CONFIG_DIR}. Run with --config <git-url> to use your own, "
            f"or 'git submodule update --init' to fetch the default ({DEFAULT_CONFIG_REPO_URL})."
        )

    return final_config


def load_yaml_source(source: str | Path) -> dict[str, Any]:
    source_str = str(source)
    if is_url(source_str):
        # If the URL ends in .git, treat it as a submodule update request
        if source_str.endswith(".git") or ("/github.com/" in source_str and "/blob/" not in source_str):
            ensure_config_repo(source_str)
            # Delegate to the standard config/ loader so config.override.yaml
            # (if the newly-pointed repo has one) still applies on top.
            return load_config_with_overrides()
        else:
            source_str = maybe_raw_github_url(source_str)
            with urllib.request.urlopen(source_str, timeout=30) as response:
                payload = response.read().decode("utf-8")
                data = yaml.safe_load(payload)
                return data

    source_path = Path(source_str)
    if not source_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {source_str}")

    with open(source_path, "r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if not isinstance(data, dict):
        raise ValueError("Configuration root must be a YAML mapping.")
    return data


def _expand_subcategory_groups(section: dict[str, Any], known_names: set[str]) -> None:
    """Expand a whole-category group like:

        ai:
          enabled: true
          submodule:
            app: { enabled: true, add_to_dock: true }

    into flat 'ai/submodule/app' entries (the form role discovery/selection
    actually understands), at any nesting depth. A group's 'enabled' acts as
    a master switch cascading down: any disabled ancestor group forces every
    descendant leaf off regardless of its own 'enabled'; all-enabled
    ancestors let each leaf's own 'enabled' (default true) decide.

    A group's 'enabled' also seeds every descendant role under it that
    *isn't* explicitly listed (e.g. 'ai: { enabled: true, opencode: {...} }'
    also enables 'ai/claude', 'ai/codex', etc.) - the point of a whole-
    category toggle is to cover roles you never had to name.

    A top-level key that's already a known leaf role name (e.g. 'vscode')
    is left untouched here - it's handled by normalize_config's own loop,
    including its 'enabled' defaults to false when unset.
    """
    groups_seen: list[tuple[str, bool]] = []

    def expand(node: dict[str, Any], prefix: str, inherited_enabled: bool | None) -> None:
        for key in list(node.keys()):
            path = f"{prefix}{key}"
            value = node[key]
            if path in known_names:
                if inherited_enabled is None:
                    continue  # real top-level role, not part of any group
                node.pop(key, None)
                if isinstance(value, bool):
                    cfg = {"enabled": value}
                elif value is None:
                    cfg = {"enabled": False}
                elif isinstance(value, dict):
                    cfg = dict(value)
                    cfg.setdefault("enabled", True)
                else:
                    continue
                if not inherited_enabled:
                    cfg["enabled"] = False
                section[path] = cfg
                continue
            if isinstance(value, dict) and any(name.startswith(path + "/") for name in known_names):
                if inherited_enabled is None:
                    node.pop(key, None)
                group_enabled = value.get("enabled", True)
                next_enabled = group_enabled if inherited_enabled is None else (inherited_enabled and group_enabled)
                groups_seen.append((path, next_enabled))
                expand(value, path + "/", next_enabled)

    expand(section, "", None)

    # Seed every known descendant of a seen group that wasn't explicitly
    # listed, using the most specific (longest-prefix) group's cascaded state.
    for name in known_names:
        if name in section:
            continue
        best: tuple[int, bool] | None = None
        for group_path, enabled in groups_seen:
            if name.startswith(group_path + "/") and (best is None or len(group_path) > best[0]):
                best = (len(group_path), enabled)
        if best is not None:
            section[name] = {"enabled": best[1]}


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(config)
    normalized.setdefault("meta", {})
    normalized.setdefault("execution", {})
    normalized.setdefault("selections", {})

    known_roles = get_all_known_roles()

    for key in CATEGORIES:
        normalized["selections"].setdefault(key, {})
        section = normalized["selections"][key]
        if isinstance(section, dict):
            _expand_subcategory_groups(section, set(known_roles.get(key, [])))
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


def _walk_roles(base: Path, current: Path, names: set[str]) -> None:
    """Recurse under `current`, adding a role name (posix path relative to
    `base`) for every directory that has its own tasks/ subdir, and
    recursing into anything else as an (optional) organizational subcategory.
    Stops at the first tasks/ found, so a role's own internal dirs (files/,
    templates/, handlers/...) are never mistaken for further subcategories.
    """
    for item in current.iterdir():
        if not item.is_dir() or item.name.startswith(("_", ".")):
            continue
        if (item / "tasks").is_dir():
            names.add(item.relative_to(base).as_posix())
        else:
            _walk_roles(base, item, names)


def _role_names(category: str, subdir: str) -> set[str]:
    """Role names (e.g. 'vscode', or 'dev/vscode' under an optional
    subcategory) for one category/subdir, across all CONTENT_ROOTS."""
    names: set[str] = set()
    for root in CONTENT_ROOTS:
        base = root / category / subdir
        if base.exists():
            _walk_roles(base, base, names)
    return names


def _group_by_subcategory(role_names: list[str]) -> list[tuple[str | None, list[str]]]:
    """Group role names by their parent directory ('dev/vscode' -> group 'dev').

    Top-level roles (no '/') form one ungrouped, header-less bucket printed
    first; subcategories follow, sorted, each with their own header.
    """
    groups: dict[str | None, list[str]] = {}
    for name in sorted(role_names):
        parent = name.rsplit("/", 1)[0] if "/" in name else None
        groups.setdefault(parent, []).append(name)
    ordered = []
    if None in groups:
        ordered.append((None, groups.pop(None)))
    for parent in sorted(groups):
        ordered.append((parent, groups[parent]))
    return ordered


def get_discovered_roles() -> dict[str, list[str]]:
    """Scan content/ + config/content/ to discover roles for the current OS."""
    discovered: dict[str, list[str]] = {}
    for cat in CATEGORIES:
        discovered[f"discovered_{cat}_common"] = sorted(_role_names(cat, "common"))
        discovered[f"discovered_{cat}_os"] = sorted(_role_names(cat, OS_KEY))
    return discovered


def get_applicable_roles() -> dict[str, list[str]]:
    """Flatten discovered roles into sections for the UI."""
    discovered = get_discovered_roles()
    return {
        cat: sorted(set(discovered[f"discovered_{cat}_common"] + discovered[f"discovered_{cat}_os"]))
        for cat in CATEGORIES
    }


def get_all_known_roles() -> dict[str, list[str]]:
    """Role names across every OS subdir, not just the current one.

    A single config.yaml can legitimately be shared across machines (mac
    entries alongside linux/win entries), so validation must not flag a
    role just because it's not applicable to *this* OS.
    """
    known: dict[str, list[str]] = {}
    for category in CATEGORIES:
        names: set[str] = set()
        for os_dir in ["common", "mac", "linux", "win"]:
            names |= _role_names(category, os_dir)
        known[category] = sorted(names)
    return known


def warn_unknown_selections(config: dict[str, Any]) -> None:
    """Flag likely-typo'd role names in config.yaml instead of silently no-oping."""
    known = get_all_known_roles()
    for section in CATEGORIES:
        unknown = sorted(set(config["selections"].get(section, {})) - set(known.get(section, [])))
        if unknown:
            print(f"Warning: unrecognized {section} role(s) in config (typo?): {', '.join(unknown)}")


def check_installed(role_name: str, section_key: str) -> bool:
    """Check if a role is already installed."""
    if section_key not in ["apps", "cli"]:
        return False

    possible_dirs = [
        root / category / subdir / role_name
        for root in CONTENT_ROOTS
        for category in ["apps", "cli"]
        for subdir in ["common", OS_KEY]
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

    # YAML lets a role's defaults.yml write an unquoted number (e.g. a Mac App
    # Store id) where a string is expected — coerce everything used as a
    # subprocess arg or shutil.which() name so one malformed role's metadata
    # can't crash installed-detection for every role in the interactive picker.
    def _str_or_none(value: Any) -> str | None:
        return str(value) if value not in (None, "", False) else None

    if section_key == "apps":
        if CURRENT_OS == "Darwin":
            app_name = _str_or_none(defaults.get("app_name_mac") or defaults.get("app_name"))
            if app_name:
                for base in ["/Applications", f"{Path.home()}/Applications"]:
                    if (Path(base) / f"{app_name}.app").exists():
                        return True
            pkg_name = _str_or_none(defaults.get("app_pkg_mac") or defaults.get("app_pkg"))
            if pkg_name:
                try:
                    res = subprocess.run(["brew", "list", "--cask", pkg_name], capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        return True
                except FileNotFoundError:
                    pass
        elif CURRENT_OS == "Windows":
            pkg_name = _str_or_none(defaults.get("app_pkg_win") or defaults.get("app_pkg"))
            if pkg_name:
                try:
                    res = subprocess.run(["winget", "list", "-q", pkg_name], capture_output=True, text=True, check=False)
                    if res.returncode == 0:
                        return True
                except FileNotFoundError:
                    pass
        elif CURRENT_OS == "Linux":
            pkg_name = _str_or_none(defaults.get("app_pkg_linux") or defaults.get("app_pkg"))
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
        value = _str_or_none(defaults.get(key))
        if value and shutil.which(value):
            return True

    return False


def apply_interactive_selection(config: dict[str, Any]) -> dict[str, Any]:
    """Arrow-key/space-toggle checklist per section."""
    applicable_roles = get_applicable_roles()
    selected = dict(config)
    sections = [
        ("apps", "App selection"),
        ("cli", "Commandline tool selection"),
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

        previously_enabled = {k for k, v in items.items() if v.get("enabled")}

        choices: list[questionary.Choice | questionary.Separator] = []
        for subcategory, names in _group_by_subcategory(list(items.keys())):
            if subcategory:
                choices.append(questionary.Separator(f"-- {subcategory} --"))
            for name in names:
                label = f"{name} [Already installed]" if check_installed(name, section_key) else name
                choices.append(questionary.Choice(title=label, value=name, checked=name in previously_enabled))

        answer = questionary.checkbox(
            f"{title} (↑/↓ move, space toggle, enter confirm)", choices=choices
        ).unsafe_ask()
        chosen = set(answer)

        for name, item_cfg in items.items():
            item_cfg["enabled"] = name in chosen

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
                          become_pass_file: str | None = None,
                          results_file: str | None = None, check_mode: bool = False) -> list[str]:
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

    if check_mode:
        # ponytail: --check/--diff only previews modules with real check-mode
        # support (homebrew, osx_defaults, package, file, copy, lineinfile...).
        # A handful of roles shell out directly (e.g. dockutil, some
        # macos_tweaks `defaults write`/PlistBuddy commands) — those are
        # skipped rather than previewed under --check, which is safe but can
        # make an otherwise-enabled role look like it did nothing.
        command += ["--check", "--diff"]

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
    for key in CATEGORIES:
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
        enable_roles("cli", ["all"])
        enable_roles("settings", ["all"])

    if args.apps:
        enable_roles("apps", args.apps)
            
    if args.tools:
        enable_roles("cli", args.tools)
            
    if args.settings:
        # Special shortcut: --settings env -> setup_environment
        if "env" in args.settings:
            args.settings = [s if s != "env" else "setup_environment" for s in args.settings]
        enable_roles("settings", args.settings)

    return overridden


def show_summary_and_confirm(config: dict[str, Any], skip_confirmation: bool) -> bool:
    """Show a summary of what will be executed and ask for confirmation."""
    print("\n" + "="*40)
    print("🚀 EXECUTION SUMMARY")
    print("="*40)
    
    any_enabled = False
    for section in CATEGORIES:
        enabled = [k for k, v in config["selections"].get(section, {}).items() if v.get("enabled")]
        if enabled:
            any_enabled = True
            title = section.replace('_', ' ').capitalize()
            print(f"\n{title}:")
            for subcategory, names in _group_by_subcategory(enabled):
                if subcategory:
                    print(f"  -- {subcategory} --")
                for item in names:
                    print(f"  - {item}")
    
    if not any_enabled:
        print("\nNo new items selected for installation (everything may already be installed).")
        return False

    print("\n" + "="*40)
    if skip_confirmation:
        return True
        
    resp = input("Proceed with these changes? [Y/n] ").strip().lower()
    return not resp or resp in {"y", "yes"}


def build_full_config_export(config: dict[str, Any]) -> dict[str, Any]:
    """A copy of `config` with every known role (every category, every OS)
    present in `selections`, defaulting to {'enabled': False} for anything
    not already selected/configured. Unlike the raw resolved config (which
    only contains roles someone actually mentioned), this is a complete
    snapshot fit to save wholesale as a new config.override.yaml.
    """
    exported = copy.deepcopy(config)
    known = get_all_known_roles()
    for category in CATEGORIES:
        section = exported["selections"].setdefault(category, {})
        for role in known.get(category, []):
            section.setdefault(role, {"enabled": False})
    return exported


def _write_config_export(config: dict[str, Any], path_str: str) -> Path | None:
    try:
        path = Path(path_str).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            yaml.safe_dump(build_full_config_export(config), handle, sort_keys=False)
        return path
    except Exception as exc:
        print(f"Error saving configuration: {exc}")
        return None


def ask_save_final_config(config: dict[str, Any]) -> None:
    resp = input("\nDo you want to export the full current selection (every app/tool/setting, "
                 "usable as a new config.override.yaml) to a file? [y/N] ").strip().lower()
    if resp in {"y", "yes"}:
        path_str = input("Enter path to save (e.g., config.override.yaml): ").strip()
        if path_str:
            path = _write_config_export(config, path_str)
            if path:
                print(f"Configuration saved to {path}")


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
        "-i", "--interactive",
        action="store_true",
        help="Force the interactive selection TUI (review/tweak a provided --config's "
             "selections before applying), overriding any auto-detected non-interactive default.",
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
    parser.add_argument(
        "--export-config",
        metavar="PATH",
        default=None,
        help="Write the fully resolved selection (every known app/tool/setting filled in, "
             "usable as a new config.override.yaml) to PATH and exit without running Ansible.",
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
    
    for section in CATEGORIES:
        enabled = [k for k, v in config["selections"].get(section, {}).items() if v.get("enabled")]
        if not enabled:
            continue
            
        title = section.replace('_', ' ').capitalize()
        print(f"\n--- {title} ---")
        for subcategory, names in _group_by_subcategory(enabled):
            if subcategory:
                print(f"  -- {subcategory} --")
            for item in names:
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

    if args.interactive:
        # Explicit request wins over bootstrap.sh's auto-non-interactive-if-no-tty default.
        args.non_interactive = False

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

    # Proactively fetch the default config repo if config/ is missing —
    # regardless of whether PROJECT_ROOT is itself a git repo (ensure_config_repo
    # falls back to a plain clone when it isn't, e.g. a directory copied
    # without .git for a quick test on another machine).
    if args.config is None:
        if not (CONFIG_DIR / "config.yaml").exists():
            ensure_config_repo(DEFAULT_CONFIG_REPO_URL)
    
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
                for section in CATEGORIES:
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

    warn_unknown_selections(config)

    if args.apps or args.tools or args.settings or args.all:
        config = apply_cli_overrides(config, args)
    elif not args.non_interactive and not (args.resume or resume_config):
        config = apply_interactive_selection(config)

    if args.export_config:
        path = _write_config_export(config, args.export_config)
        if not path:
            return 2
        print(f"Exported full configuration to {path}")
        return 0

    # Show summary and confirm before proceeding (only for CLI-driven or Interactive runs)
    if not args.non_interactive:
        if not show_summary_and_confirm(config, args.yes):
            print("Execution cancelled.")
            return 0

    save_resume_config(config)

    # discovered_metadata (lists of role names) must travel through the YAML
    # vars file, not as individual `-e key=value` flags: ansible-core parses
    # `-e @file` as YAML but treats every `-e key=value` as a plain string,
    # so a list passed that way arrives character-iterable, not iterable by
    # role name (see bootstrap.yml's active-role lookup).
    vars_file = write_temp_vars_file({**config, **discovered_metadata})
    
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
        results_file=results_file,
        check_mode=bool(config["execution"].get("check_mode", False)),
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
        if success and not args.non_interactive:
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

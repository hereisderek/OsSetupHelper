# ♊ GEMINI Context: OsSetupHelper

## Project Overview
**OsSetupHelper** is a modular, cross-platform OS initialization and setup utility. It uses a **Python-based orchestrator** as a frontend to provide an interactive (TUI) or non-interactive selection process, which then triggers **Ansible playbooks** to perform system configuration.

### Core Architecture
- **Orchestrator (`orchestrator.py`)**: 
    - **Discovery**: Scans `apps/`, `commandline_tools/`, and `settings/` for roles compatible with the current OS.
    - **Config Merging**: Implements a robust `deep_merge` that combines `config.yaml` and `config.override.yaml`. 
        - **Lists**: Merged (additive) instead of replaced.
        - **Blacklisting**: Items prefixed with `!` (e.g., `!wget`) are removed from base lists.
    - **Ansible Glue**: Dynamically builds the `ansible-playbook` command, passing discovered metadata and user selections via JSON-encoded extra-vars to ensure correct type handling (lists).
- **Ansible Backend (`bootstrap.yml`)**:
    - **Log Optimization**: Pre-filters roles in the `Identify active roles` task to eliminate "skipping" logs for unselected items.
    - **Granular Execution**: Uses a standardized `_shared_tasks/run_role_with_hooks.yml` wrapper to handle per-role pre/post hooks.
- **Centralized Installer (`_shared_tasks/installer/`)**: Unified entry point for apps using `brew`, `brew cask`, `mas`, `apt`, `dnf`, `pacman`, `apk`, and `winget`.

## Technical Requirements for Rebuilding

### 1. Configuration Engine
- Support multiple override layers.
- **Merging Logic**:
    - Dictionaries: Recursive merge.
    - Lists: Append-only by default.
    - Exclusions: Support `!` prefix for strings and `exclude: true` or `!` for keyed objects (e.g., `id` for `mas` apps).
- **Type Safety**: Use `json.dumps()` when passing complex structures to Ansible `-e` flags to avoid string-parsing ambiguities.

### 2. Role Structure (Standardized)
- **Granular Subtasks**: Large roles (like `macos_tweaks`) must be broken into `subtasks/*.yml` files called by a manager `tasks/main.yml`.
- **Platform Agnosticism**: Use `settings/common` for logic that applies to multiple OSes (e.g., `setup_hostname`, `setup_packages`).
- **Hook System**: Every role supports:
    - `tasks/pre.yml` & `tasks/post.yml` (inside the role).
    - `config/<category>/<role>/pre.yml` & `post.yml` (user-defined in config repo).

### 3. Installation Logic
- **Homebrew**: Prefer `community.general.homebrew` and `homebrew_cask` modules over raw shell commands.
- **Mac App Store (mas)**: 
    - Handle version 6.0+ (no `account` command).
    - Provide `ansible.builtin.debug` progress messages for slow installs.
    - Use `become: true` for `mas install`.
- **Linux**: Distro-aware package management using `ansible.builtin.package`.
- **Windows**: Use `community.windows.win_winget`.

## Key Files & Directories
- `orchestrator.py`: The brain (Discovery, Merging, Execution).
- `bootstrap.yml`: The entry point (Filtering, Orchestration).
- `_shared_tasks/`: reusable logic for installers, hooks, and reporting.
- `apps/`, `commandline_tools/`, `settings/`: Category-based role storage.
- `config/`: Git submodule for user-specific configurations and hooks.

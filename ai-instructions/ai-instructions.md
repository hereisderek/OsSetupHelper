# 🤖 AI System Instructions: OsSetupHelper Core Architecture

When rebuilding or extending the **OsSetupHelper**, follow these rigid architectural patterns.

## 1. Orchestrator Logic (Python)
- **Role Discovery**: 
    - Categories: `apps`, `commandline_tools`, `settings`.
    - Paths: `<category>/common/`, `<category>/<os_key>/`.
    - OS Keys: `mac`, `linux`, `win`.
- **Configuration Merging (`deep_merge`)**:
    - **Recursive Dictionaries**: Key-value replacement.
    - **Lists**: **additive** (base + override).
    - **Blacklisting**: 
        - String `!item` removes `item`.
        - Dict `{ "id": 123, "exclude": true }` or `{ "id": "!123" }` removes based on key.
- **Ansible Execution**:
    - Pass complex data (lists) as single-quoted JSON strings in `-e`.
    - Example: `-e discovered_apps_common='["app1", "app2"]'`.
    - Include `os_key` as an extra-var.

## 2. Playbook Orchestration (Ansible)
- **Log Management**:
    - Avoid `when` conditions for role inclusion in `loop`.
    - **Mandatory Pattern**: Use `ansible.builtin.set_fact` with Jinja2 loop filtering to create `active_<category>_roles` lists.
    - Loop over these active lists only.
- **Role Execution**:
    - Standardize on `_shared_tasks/run_role_with_hooks.yml`.
    - Support per-role `pre.yml` and `post.yml` (from both role and config submodule).

## 3. Installation Pattern
- **Centralized Installer**:
    - Role `tasks/main.yml` should only include `_shared_tasks/installer/main.yml` or a category-specific subtask.
    - Use Homebrew/mas modules for macOS.
    - Use native `ansible.builtin.package` for Linux.
    - Use `win_winget` for Windows.
- **User Feedback**:
    - Use `ansible.builtin.debug` messages for slow operations (App Store, Homebrew).
    - Trigger `Restart Dock`/`Restart Finder` via global handlers in `bootstrap.yml`.

## 4. Bootstrapper (Shell)
- **Zero-Dependency Goal**: The `bootstrap.sh` should handle Python venv, dependencies, and Xcode CLT (macOS) before invoking the orchestrator.
- **Robustness**: 
    - Support `--sync` to update remote configs.
    - Auto-detect the best available Python 3 interpreter.
    - Don't get stuck on Xcode CLT - let Homebrew handle the heavy lifting.

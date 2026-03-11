# ♊ GEMINI Context: OsSetupHelper

## Project Overview
**OsSetupHelper** is a modular, cross-platform OS initialization and setup utility. It uses a **Python-based orchestrator** as a frontend to provide an interactive (TUI) or non-interactive selection process, which then triggers **Ansible playbooks** to perform the actual system configuration.

### Core Architecture
- **Orchestrator (`orchestrator.py`)**: A Python 3 script that manages OS detection, interactive role selection, installed app detection, and session resume (`~/.ossetup_resume.yaml`).
- **Bootstrapper (`bootstrap.sh`)**: A shell script designed for "one-liner" execution. It handles environment setup (Python venv, dependencies) and clones the repository if necessary.
- **Ansible Backend (`bootstrap.yml`)**: The primary playbook that dynamically includes roles based on user selections.
- **Centralized Installer (`_shared_tasks/installer/`)**: A unified entry point for all application installations across macOS, Windows, and Linux.
- **External Configuration (`config/`)**: A dedicated directory for user preferences, pre/post installation hooks, and custom environment files. This directory is managed as a Git submodule, allowing users to maintain their configurations in a separate repository (e.g., [OsSetupHelperConfig](https://github.com/hereisderek/OsSetupHelperConfig)).

### Configuration Repository Structure
The `config/` directory includes the following hooks:
- `config.yaml`: The main user preference file.
- `preinstall/`: Directory for custom bash scripts executed before role inclusion.
- `postinstall/`: Directory for custom bash scripts executed after all roles are processed.
- `ansible_tasks/`: Custom Ansible tasks (e.g., `pre.yml`, `post.yml`).
- `user_env/`: Files to be automatically copied to `~/.config/env/app/`.

## Building and Running

### Prerequisites
- Python 3.9+
- Ansible (automatically handled by `requirements.txt`)
- Git

### Key Commands
- **Recommended One-Liner**:
  ```bash
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)"
  ```
- **Manual Execution**:
  ```bash
  python3 -m pip install -r requirements.txt
  python3 orchestrator.py
  ```
- **Resume Previous Selection**:
  ```bash
  python3 orchestrator.py --resume
  ```
- **Install All Applicable (Skips Installed)**:
  ```bash
  python3 orchestrator.py --all [-y]
  ```
- **Non-Interactive Mode (CI/Automation)**:
  ```bash
  python3 orchestrator.py --non-interactive --config config/config.yaml
  ```
- **Custom Configuration (Git Repository)**:
  ```bash
  python3 orchestrator.py --config https://github.com/your-username/OsSetupHelperConfig.git
  ```
  Providing a Git URL will automatically initialize or update the `config/` directory as a submodule pointing to your repository.

## Development Conventions

### Role Structure
Each module (app/tool/setting) follows the Ansible role pattern. New roles should be modeled after the templates in `_role_templates/`.

**Typical Role Layout:**
- `defaults/main.yml`: Default package IDs and variables.
- `meta/main.yml`: Role metadata and dependencies.
- `tasks/main.yml`: Main entry point, typically including the centralized installer.

### Coding Standards
- **Idempotency**: All tasks must be safe to run multiple times.
- **Centralized Installation**: Use `_shared_tasks/installer/main.yml` for all application installs.
- **Platform Agnosticism**: Favor `apps/common` roles that use the centralized installer to resolve OS-specific package names.
- **Configuration**: Use `config.yaml` as the source of truth.

### Testing & Validation
- **YAML Linting**: Ensure all `.yml` and `.yaml` files are valid.
- **Ansible Linting**: Follow best practices for Ansible modules (e.g., use `ansible.builtin` prefix).
- **Dry Run**: Use the `--check` flag in Ansible if implemented via `config.yaml` (`execution.check_mode`).

## Key Files
- `orchestrator.py`: The heart of the user interaction and Ansible glue.
- `bootstrap.yml`: The master playbook defining role execution order.
- `config.yaml`: Default user preferences and schema example.
- `ansible.cfg`: Configures role search paths across the modular directory structure.
- `bootstrap.sh`: The entry point for fresh system installations.

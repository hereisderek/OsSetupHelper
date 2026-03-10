# ♊ GEMINI Context: OsSetupHelper

## Project Overview
**OsSetupHelper** is a modular, cross-platform OS initialization and setup utility. It uses a **Python-based orchestrator** as a frontend to provide an interactive (TUI) or non-interactive selection process, which then triggers **Ansible playbooks** to perform the actual system configuration.

### Core Architecture
- **Orchestrator (`orchestrator.py`)**: A Python 3 script that loads configurations, handles user selections, and generates a temporary variables file for Ansible.
- **Bootstrapper (`bootstrap.sh`)**: A shell script designed for "one-liner" execution. It handles environment setup (Python venv, dependencies) and clones the repository if necessary.
- **Ansible Backend (`bootstrap.yml`)**: The primary playbook that dynamically includes roles based on the user's selections and the target operating system.
- **Modular Roles**: System components are organized into three main categories:
  - `apps/`: GUI applications (Common, Mac, Linux, Win).
  - `commandline_tools/`: CLI utilities and shells.
  - `settings/`: System tweaks, SSH/Git configuration, and environment variables.

## Building and Running

### Prerequisites
- Python 3.9+
- Ansible (automatically handled by `requirements.txt`)
- Git

### Key Commands
- **Recommended One-Liner**:
  ```bash
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/derek/OsSetupHelper/main/bootstrap.sh)"
  ```
- **Manual Execution**:
  ```bash
  python3 -m pip install -r requirements.txt
  python3 orchestrator.py
  ```
- **Non-Interactive Mode (CI/Automation)**:
  ```bash
  python3 orchestrator.py --non-interactive --config config.yaml
  ```
- **Custom Configuration**:
  ```bash
  python3 orchestrator.py --config https://github.com/user/repo/blob/main/my_config.yaml
  ```

## Development Conventions

### Role Structure
Each module (app/tool/setting) follows the Ansible role pattern. New roles should be modeled after the templates in `_role_templates/`.

**Typical Role Layout:**
- `defaults/main.yml`: Default package IDs and variables.
- `meta/main.yml`: Role metadata and dependencies.
- `tasks/main.yml`: Main entry point, often resolving the platform.
- `tasks/platform/`: OS-specific task files (`mac.yml`, `linux.yml`, `win.yml`).

### Coding Standards
- **Idempotency**: All tasks must be safe to run multiple times. Check if an app is installed before attempting installation.
- **Platform Agnosticism**: Where possible, use the `apps/common` pattern with platform-specific task inclusions.
- **Configuration**: Use `config.yaml` as the source of truth for all user-adjustable parameters. The orchestrator ensures these are passed to Ansible via the `selections` variable.
- **Python Style**: Follow PEP 8. Use `argparse` for CLI arguments and `urllib` for fetching remote configs.

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

# 🚀 Universal OS Bootstrapper

A modular, cross-platform OS initialization and setup utility. This tool provides a clean Terminal UI (TUI) to bootstrap fresh installs of Windows, macOS, and Linux machines based on customizable YAML configurations.

Unlike opaque binaries, this project is driven by **Ansible** on the backend. This means the actual installation logic is transparent, easy to read, and simple to modify or fork for your own homelab needs.

## ✨ Features

* **Interactive TUI:** An arrow-key/space-toggle checklist (↑/↓ to move, space to select, enter to confirm) lets you pick exactly which apps, tools, and settings to apply — enabled apps get a quick follow-up (e.g. pin to Dock?) before moving on.
* **OS-Aware Selection:** Only shows apps and settings relevant to your current operating system (macOS, Windows, or Linux).
* **Installed App Detection:** Automatically detects if an app is already installed and flags it in the TUI.
* **Resume Capability:** Saves your selections so you can pick up where you left off or reuse previous configurations.
* **Cross-Platform:** Supports Windows, macOS, and Linux out of the box.
* **Highly Modular:** Every app, command-line tool, and system setting lives in its own isolated folder (Ansible Role), sharing a centralized installation logic.
* **Dynamic Configurations:** Load your preferred software stack from your own config repo, a local YAML file, or a raw GitHub URL — or just use the built-in recommended defaults.
* **Idempotent Execution:** Safe to run multiple times. If an app is already installed, the script simply moves on.
* **Dock Management (macOS):** Simply toggle `add_to_dock: true` in your config to automatically pin any UI app to your macOS dock during installation.
* **Native Installers Per OS:** Homebrew formulae/casks and the Mac App Store (`mas`) on macOS, `winget` on Windows, and your distro's native package manager (`apt`/`dnf`/`pacman`/`apk`) on Linux — no custom package format to learn.

**👉 [View the full list of supported apps, tools, and settings here](FEATURES.md)**

## 🏗️ The Two-Repo Architecture

This project is designed with a strict separation between the **Engine** and your **Configuration**. This allows you to pull updates for the installer without affecting your personal settings.

1.  **Engine Repo ([OsSetupHelper](https://github.com/hereisderek/OsSetupHelper))**: Contains the built-in roles (in `content/apps/`, `content/cli/`, `content/settings/`), orchestrator logic, and common installation tasks. Ships with **no config of its own**.
2.  **Config Repo ([OsSetupHelperConfig](https://github.com/hereisderek/OsSetupHelperConfig))**: Contains `config.yaml`, custom pre/post hooks, environment files, and optionally its own `content/apps/`, `content/cli/`, `content/settings/` — anything there **overrides or adds to** the engine's roles of the same name. Fork it and point `--config` at your fork to use your own; if you don't, the engine falls back to this repo's own recommended defaults automatically.

The engine manages your config repo as a **Git Submodule** in the `config/` directory — that's the only place `config.yaml` lives; there's no copy at the project root.

---

## 🏁 Quickstart (Recommended)

One command bootstraps a fresh machine — installs prerequisites (Homebrew/Python/etc.), sets up the Python environment, and runs the orchestrator. Works on macOS, Linux, and Windows (via Git Bash or WSL).

```bash
# Uses your own config repo:
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" -- --config https://github.com/<you>/OsSetupHelperConfig.git

# Or omit --config entirely to use the recommended defaults:
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)"
```

By default this runs fully unattended, applying whatever the config has marked `enabled: true` — no prompts. Add `-i`/`--interactive` to review or tweak the selections first:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" -- --config https://github.com/<you>/OsSetupHelperConfig.git -i
```

*Note: the `bash -c "$(curl ...)"` form (not a plain `curl | bash` pipe) keeps your real terminal attached, which `-i`/`--interactive` needs to prompt you. A plain piped install (no terminal attached) automatically runs unattended even without `--non-interactive`.*

*The orchestrator automatically attaches your config repo as a git submodule in the `config/` folder.*

## 🛠️ Manual & Local Usage

1. Install Python dependencies:

```bash
python3 -m venv .venv 
source .venv/bin/activate 
pip install -r requirements.txt
```

```dos
python3 -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
```

```powershell
python3 -m venv .venv ; .\.venv\Scripts\Activate.ps1 ; pip install -r requirements.txt
```

2. Set up your config: `git submodule update --init` for the recommended defaults, or `python3 orchestrator.py --config https://github.com/<you>/OsSetupHelperConfig.git` to point at your own fork (this repoints the submodule for future runs too). Either way, edit `config/config.yaml` after.

3. Run the orchestrator interactively:

```bash
python3 orchestrator.py
```

4. Resume a previous session:

```bash
python3 orchestrator.py --resume
```

5. Run non-interactive mode (CI or scripted use) — reads `config/config.yaml` by default:

```bash
python3 orchestrator.py --non-interactive
```

### Running Specific Tasks

You can optionally specify exactly which apps, tools, or settings to apply, or use the `--all` flag to install everything applicable to your OS:

```bash
# Install everything applicable (skipping already installed items)
python3 orchestrator.py --all

# Skip confirmation prompts with -y or --yes
python3 orchestrator.py --all -y

# Use 'all' for specific categories and exclude roles
python3 orchestrator.py --apps all --exclude steam discord
python3 orchestrator.py --tools all --exclude gemini

# Install specific apps
python3 orchestrator.py --apps vscode chrome

# Install specific command-line tools
python3 orchestrator.py --tools zsh_ohmyzsh gemini

# Apply specific settings
python3 orchestrator.py --settings macos_tweaks setup_ssh_git
```

*Note: When using these flags, all other tasks are disabled by default.*

### Synchronizing with Remote

When running `./bootstrap.sh` locally, it skips remote synchronization by default to protect your local changes. Use the `--sync` flag to force an update from the remote repository:

```bash
./bootstrap.sh --sync
```

### Sudo Permissions

By default, the orchestrator tries to run Ansible with elevated privileges (`sudo`). If your system requires a password for sudo, you must pass the `-K` (or `--ask-become-pass`) flag to prompt for it securely:

```bash
python3 orchestrator.py -K --tools zsh_ohmyzsh
```

Alternatively, you can run the orchestrator itself as root (`sudo python3 orchestrator.py`), or disable elevation entirely inside `config/config.yaml` (`execution.always_elevated: false`).

The orchestrator writes a temporary variables file and invokes `ansible-playbook` against `bootstrap.yml` locally.

`bootstrap.yml` includes roles dynamically by reading `selections.apps`, `selections.cli`, and `selections.settings` in `config/config.yaml` — see [FEATURES.md](FEATURES.md) for the current list of what's supported.

## Adding Your Own App, Tool, or Setting

Roles are auto-discovered by directory, so there's nothing to register. Scaffold one with:

```bash
./new_role.sh apps mac my_app
```

(first argument: `apps`, `cli`, or `settings`; second: `common`, `mac`, `linux`, or `win`), then fill in the generated `defaults/main.yml` (`app_pkg_mac`/`app_pkg_linux`/`app_pkg_win`, `app_name`) and add it to `config/config.yaml` under `selections.<category>.<name>`.

Add `--config` to the same command (`./new_role.sh apps mac my_app --config`) to scaffold it inside your **config repo** instead (`config/content/...`) — roles there are checked first, so this also lets you override/replace a built-in role by giving yours the same name. See your config repo's own README for the lighter-weight pre/post-hook-only option.

Roles can optionally be grouped into subfolders for organization — e.g. `content/apps/mac/dev/vscode/` instead of `content/apps/mac/vscode/` — just move the role's folder under whatever subfolder name you like (any depth). It's auto-detected (any folder without its own role files is treated as a group) and shows up as a grouped header in the interactive selection menu. In `config.yaml`, key it by the full path, still under `apps:`:

```yaml
apps:
  dev/vscode:
    enabled: true
```
# 🚀 Universal OS Bootstrapper

A modular, cross-platform OS initialization and setup utility. This tool provides a clean Terminal UI (TUI) to bootstrap fresh installs of Windows, macOS, and Linux machines based on customizable YAML configurations.

Unlike opaque binaries, this project is driven by **Ansible** on the backend. This means the actual installation logic is transparent, easy to read, and simple to modify or fork for your own homelab needs.

## ✨ Features

* **Interactive TUI:** A lightweight Python frontend allows you to select exactly which apps, tools, and settings you want to apply.
* **Cross-Platform:** Supports Windows, macOS, and Linux out of the box.
* **Highly Modular:** Every app, command-line tool, and system setting lives in its own isolated folder (similar to Ansible Roles).
* **Dynamic Configurations:** Load your preferred software stack from a local YAML file or directly from a raw GitHub URL.
* **Idempotent Execution:** Safe to run multiple times. If an app is already installed, the script simply moves on.
* **Dock Management (macOS):** Simply toggle `add_to_dock: true` in your `config.yaml` to automatically pin any UI app to your macOS dock during installation.

## 📂 Project Structure

The project directory is structured to separate GUI apps, CLI tools, and system optimizations by OS:

```text
root/
├── settings/                # OS optimization and cleanup scripts
│   ├── win/
│   ├── linux/
│   └── mac/
├── apps/                    # GUI Applications
│   ├── common/              # Cross-platform apps (e.g., VS Code, Firefox)
│   ├── win/
│   ├── linux/
│   └── mac/
├── commandline_tools/       # CLI Tools
│   ├── common/              # Cross-platform tools (e.g., git, ripgrep)
│   ├── win/
│   ├── linux/
│   └── mac/
├── config.yaml              # Your default user preferences
└── orchestrator.py          # The Python UI frontend

## 🏁 Quickstart (Recommended)

You can bootstrap your machine with a single command by providing a link to your configuration file on GitHub. The script will automatically setup the Python environment and start the orchestration.

**🍎 macOS / 🐧 Linux**
Open your terminal and run:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" -- --config https://github.com/derek/OsSetupHelper/blob/main/config.yaml
```

**🪟 Windows**
Open **Git Bash** or **WSL** (do not use standard PowerShell or Command Prompt for the bash script) and run:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" -- --config https://github.com/hereisderek/OsSetupHelper/blob/main/config.yaml
```

*Note: The script automatically handles converting GitHub 'blob' URLs to 'raw' URLs for you.*

## 🛠️ Manual & Local Usage

1. Install Python dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Review or edit `config.yaml`.

3. Run the orchestrator interactively:

```bash
python3 orchestrator.py
```

4. Run non-interactive mode (CI or scripted use):

```bash
python3 orchestrator.py --non-interactive --config config.yaml
```

### Running Specific Tasks

You can optionally specify exactly which apps, tools, or settings to apply, bypassing the interactive prompt. This is useful for installing a single application or applying a specific setting:

```bash
# Install specific apps
python3 orchestrator.py --apps vscode chrome

# Install specific command-line tools
python3 orchestrator.py --tools zsh_ohmyzsh gemini

# Apply specific settings
python3 orchestrator.py --settings macos_tweaks

# Combine multiple specific tasks
python3 orchestrator.py --apps vscode --tools opencode --settings setup_ssh_git
```

*Note: When using these flags, all other tasks are disabled by default.*

### Sudo Permissions

By default, the orchestrator tries to run Ansible with elevated privileges (`sudo`). If your system requires a password for sudo, you must pass the `-K` (or `--ask-become-pass`) flag to prompt for it securely:

```bash
python3 orchestrator.py -K --tools zsh_ohmyzsh
```

Alternatively, you can run the orchestrator itself as root (`sudo python3 orchestrator.py`), or disable elevation entirely inside `config.yaml` (`execution.always_elevated: false`).

The orchestrator writes a temporary variables file and invokes `ansible-playbook` against `bootstrap.yml` locally.

## Module Coverage

Implemented from the instruction files:

- Common apps in `apps/common/`: `chrome`, `vscode`, `sourcetree`, `jetbrains_toolbox`, `sublime`, `steam`, `discord`, `spotify`, `notion`, `postman`, `slack`, `obs_studio`, `docker_desktop`, `freedownloadmanager`, `localsend`, `wechat`, `google_drive`, `pixpin`, `android_studio`
- macOS apps in `apps/mac/`: `iterm`, `charles`, `betterdisplay`, `stats`, `appcleaner`, `macs_fan_control`, `displaylink_manager`, `handbrake`, `iina`, `raycast`, `xcode`, `utm`
- Linux apps in `apps/linux/`: `gnome_tweaks`, `gnome_shell_extensions`
- Windows apps in `apps/win/`: `wsl2`, `windows_terminal`, `winget`, `powershell`
- Common settings in `settings/common/`: `setup_ssh_git`, `setup_environment`
- macOS settings in `settings/mac/`: `macos_tweaks`
- Commandline tools in `commandline_tools/common/`: `zsh_ohmyzsh`, `opencode`, `gemini`, `cloudcode`
- macOS Commandline tools in `commandline_tools/mac/`: `mole`, `mist_cli`

`bootstrap.yml` now includes roles dynamically by reading `selections.apps`, `selections.commandline_tools`, and `selections.settings` in `config.yaml`.
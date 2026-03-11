# 🚀 Universal OS Bootstrapper

A modular, cross-platform OS initialization and setup utility. This tool provides a clean Terminal UI (TUI) to bootstrap fresh installs of Windows, macOS, and Linux machines based on customizable YAML configurations.

Unlike opaque binaries, this project is driven by **Ansible** on the backend. This means the actual installation logic is transparent, easy to read, and simple to modify or fork for your own homelab needs.

## ✨ Features

* **Interactive TUI:** A lightweight Python frontend allows you to select exactly which apps, tools, and settings you want to apply.
* **OS-Aware Selection:** Only shows apps and settings relevant to your current operating system (macOS, Windows, or Linux).
* **Installed App Detection:** Automatically detects if an app is already installed and flags it in the TUI.
* **Resume Capability:** Saves your selections so you can pick up where you left off or reuse previous configurations.
* **Cross-Platform:** Supports Windows, macOS, and Linux out of the box.
* **Highly Modular:** Every app, command-line tool, and system setting lives in its own isolated folder (Ansible Role), sharing a centralized installation logic.
* **Dynamic Configurations:** Load your preferred software stack from a local YAML file or directly from a raw GitHub URL.
* **Idempotent Execution:** Safe to run multiple times. If an app is already installed, the script simply moves on.
* **Dock Management (macOS):** Simply toggle `add_to_dock: true` in your `config.yaml` to automatically pin any UI app to your macOS dock during installation.

**👉 [View the full list of supported apps, tools, and settings here](FEATURES.md)**

## 🏗️ The Two-Repo Architecture

This project is designed with a strict separation between the **Engine** and your **Configuration**. This allows you to pull updates for the installer without affecting your personal settings.

1.  **Engine Repo ([OsSetupHelper](https://github.com/hereisderek/OsSetupHelper))**: Contains the Ansible roles, orchestrator logic, and common installation tasks.
2.  **Config Repo ([OsSetupHelperConfig](https://github.com/hereisderek/OsSetupHelperConfig))**: Your personal fork containing your `config.yaml`, custom pre/post hooks, and environment files.

The engine manages your config repo as a **Git Submodule** in the `config/` directory.

---

## 🏁 Quickstart (Recommended)

You can bootstrap your machine with a single command by providing a link to your configuration repository on GitHub. The script will automatically setup the Python environment and start the orchestration.

**🍎 macOS / 🐧 Linux**
Open your terminal and run:
```bash
# remember to use your own config repo URL if you have one
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" -- --config https://github.com/hereisderek/OsSetupHelperConfig.git
```

**🪟 Windows**
Open **Git Bash** or **WSL** and run:
```bash
# remember to use your own config repo URL if you have one
bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" -- --config https://github.com/hereisderek/OsSetupHelperConfig.git
```

*Note: The orchestrator will automatically attach your repository as a git submodule in the `config/` folder.*

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

4. Resume a previous session:

```bash
python3 orchestrator.py --resume
```

5. Run non-interactive mode (CI or scripted use):

```bash
python3 orchestrator.py --non-interactive --config config.yaml
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
```

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

Alternatively, you can run the orchestrator itself as root (`sudo python3 orchestrator.py`), or disable elevation entirely inside `config.yaml` (`execution.always_elevated: false`).

The orchestrator writes a temporary variables file and invokes `ansible-playbook` against `bootstrap.yml` locally.

## Module Coverage

Implemented from the instruction files:

- Common apps in `apps/common/`: `chrome`, `vscode`, `sourcetree`, `jetbrains_toolbox`, `sublime`, `steam`, `discord`, `spotify`, `notion`, `postman`, `slack`, `obs_studio`, `docker_desktop`, `freedownloadmanager`, `localsend`, `wechat`, `google_drive`, `pixpin`, `android_studio`
- macOS apps in `apps/mac/`: `iterm`, `charles`, `betterdisplay`, `stats`, `appcleaner`, `macs_fan_control`, `displaylink_manager`, `handbrake`, `iina`, `raycast`, `xcode`, `utm`
- Linux apps in `apps/linux/`: `gnome_tweaks`, `gnome_shell_extensions`
- Windows apps in `apps/win/`: `wsl2`, `windows_terminal`, `winget`, `powershell`
- Common settings in `settings/common/`: `setup_ssh_git`, `setup_environment`, `setup_hostname`, `setup_packages`
- macOS settings in `settings/mac/`: `macos_tweaks`
- Commandline tools in `commandline_tools/common/`: `nodejs`, `zsh_ohmyzsh`, `opencode`, `gemini`, `claudcode`, `openjdk-latest`, `openjdk-17`

- macOS Commandline tools in `commandline_tools/mac/`: `mole`, `mist_cli`

`bootstrap.yml` now includes roles dynamically by reading `selections.apps`, `selections.commandline_tools`, and `selections.settings` in `config.yaml`.
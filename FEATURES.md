# 📋 Detailed Project Inventory

This document provides a comprehensive list of all applications, command-line tools, and system settings currently supported by OsSetupHelper.

## 📱 Applications (GUI)

### Cross-Platform (Common)
- **Browsers**: `chrome`
- **Development**: `vscode`, `sourcetree`, `jetbrains_toolbox`, `android_studio`, `sublime`, `postman`, `docker_desktop`
- **Communication**: `discord`, `slack`, `wechat`
- **Productivity**: `notion`, `google_drive`
- **Media**: `spotify`, `obs_studio`, `pixpin`
- **Utilities**: `freedownloadmanager`, `localsend`
- **Gaming**: `steam`
- **AI** (`ai/` subfolder — see [Adding Your Own App, Tool, or Setting](README.md#adding-your-own-app-tool-or-setting) for how subfolders work): `ai/antigravity` (Google Antigravity IDE), `ai/claude` (Claude desktop app), `ai/codex` (OpenAI Codex), `ai/opencode` (OpenCode desktop app)
- **Networking/Utilities** (mac + Windows + Linux, though non-mac coverage varies by app — see each role's own README for exactly which OSes have a verified package): `wireguard` (mac App Store, Windows/Linux via package manager), `handbrake` (mac + Windows only), `charles` (mac + Windows only), `displaylink_manager` (mac + Windows only), `ghostty` (mac + Linux on newer distros, no official Windows build)

### macOS Specific
- `iterm`: Terminal emulator for macOS.
- `betterdisplay`: Display resolution management.
- `stats`: System monitor for the menu bar.
- `appcleaner`: Application uninstaller.
- `macs_fan_control`: Manual fan control.
- `iina`: Modern video player.
- `raycast`: Extensible launcher.
- `xcode`: IDE for Apple platforms (via App Store).
- `utm`: Virtual machine manager.

### Linux Specific
- `gnome_tweaks`: Advanced GNOME customization.
- `gnome_shell_extensions`: Includes popular extensions (Dash to Dock, etc.).

### Windows Specific
- `wsl2`: Windows Subsystem for Linux.
- `windows_terminal`: Modern terminal application.
- `winget`: Windows Package Manager.
- `powershell`: Modern PowerShell Core.

---

## 🛠️ Command-Line Tools

### Cross-Platform (Common)
- `nodejs`: Node.js and npm package manager.
- `openjdk-latest`: Latest OpenJDK (includes macOS JVM symlinking).
- `openjdk-17`: OpenJDK 17 LTS (includes macOS JVM symlinking).
- `zsh_ohmyzsh`: Zsh shell with Oh My Zsh framework.
- `opencode`: Open Source development utilities.
- `gemini`: AI command-line integration.
- `claudcode`: Anthropic's Claude Code agentic CLI tool.

### macOS Specific
- `mole`: CLI tool for connecting to remote hosts.
- `mist_cli`: macOS Installer download & creation tool.

---

## ⚙️ System Settings

### Cross-Platform (Common)
- `setup_ssh_git`: Configures Git global user, email, and trusts SSH keys from GitHub accounts.
- `setup_environment`: Manages custom environment variables and shell scripts in `~/.config/env/`.

### macOS Specific
- `macos_tweaks`: A comprehensive set of macOS system optimizations, including:
    - **Hostname**: Automatically sets `ComputerName`, `HostName`, and `LocalHostName` based on `config.yaml` or current username.
    - **Finder**: List view defaults, search scope to current folder, show hidden files.
    - **Desktop**: Hard disk/External drive visibility, label positioning, item info.
    - **Menu Bar**: Battery percentage, volume indicator.
    - **Input**: Tap-to-click, three-finger drag, right-click enable, swap Cmd/Opt on external keyboards.
    - **Dock**: Remove known Apple stock apps (Safari, Mail, Messages, Maps, Photos, FaceTime, Phone, Calendar, Contacts, Reminders, Notes, Freeform, Music, TV, Podcasts, News, Games, App Store, iPhone Mirroring) while keeping Finder, Launchpad/Apps, System Settings, Trash, and anything you've installed yourself (`clean_dock_icons`).
    - **Displays**: Set the main display's scaled resolution to "More Space" — the largest HiDPI mode, via `displayplacer` (`display_more_space`).
    - **Zsh**: Enable interactive comments.

## apps to install

All application roles should use the centralized installer task in `_shared_tasks/installer/main.yml`. 
The `tasks/main.yml` for a common app should typically just be:
```yaml
---
- name: Run installer
  ansible.builtin.include_tasks: "{{ playbook_dir }}/_shared_tasks/installer/main.yml"
```
The installer uses variables from `defaults/main.yml` (e.g., `app_pkg_mac`, `app_pkg_win`, `app_pkg_linux`).

### common
* chrome
* vscode
* sourcetree
* jetbrain toolkit
    * android studio
    * intellij
* sublime
* steam
* discord
* spotify
* notion
* postman
* slack
* obs studio
* docker desktop
* freedownloadmanager
* localsend
* wechat
* google drive
* pixpin
* ai (subcategory folder, `apps/common/ai/`)
    * antigravity (Google Antigravity — Gemini-powered agentic IDE)
    * claude (Claude desktop app — distinct from the `claudcode` CLI role)
    * codex (OpenAI Codex — cask on macOS, npm elsewhere)
    * opencode (OpenCode desktop app — distinct from the `opencode` CLI role)
* wireguard — `wireguard-tools` via Homebrew *formula* on mac (brew preferred over the Mac App Store GUI app — no cask exists for wireguard-tools, and the centralized installer always uses cask for `apps` on Darwin, so this role has its own `tasks/main.yml` routing mac through `mac_install_formula.yml` directly), same package name on Linux, official app via winget on Windows
* handbrake — mac + Windows only (no verified simple Linux package; upstream recommends Flatpak)
* charles — mac + Windows only (Linux needs Charles's own apt/yum repo, not wired up)
* displaylink_manager — mac + Windows only (Linux needs Synaptics's own apt repo, not wired up)
* ghostty
  * set config with: shell-integration-features = ssh-terminfo,ssh-env
  * mac + Linux (only where the distro ships it in default repos, e.g. Ubuntu 26.04+ — gracefully no-ops elsewhere); no official Windows build (the "winghostty" winget package is an unrelated third-party project, deliberately not used)


### mac
* iterm
* betterdisplay
* stats
* appcleaner
* macs fan control
* iina
* raycast
* xcode
* utm
* battery



### linux
* gnome tweaks
* gnome shell extensions
    * dash to dock
    * clipboard indicator
    * user themes
    * system monitor
    * app indicator support
    * open weather
    * places status indicator
    * desktop icons NG

### windows
* wsl2
* windows terminal
* winget
* powershell


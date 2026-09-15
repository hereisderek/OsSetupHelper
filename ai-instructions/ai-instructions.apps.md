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
* ai
  * [claude](https://www.claude.com/)
  * [antigravity](https://antigravity.google/)
  * [codex](https://github.com/codex-ai/codex)
  * [opencode](https://opencode.com/)
  * [ollama](https://ollama.com/)
  * [omlx](https://github.com/jundot/omlx)
  * Skills
    * [agent-skills](https://github.com/addyosmani/agent-skills)
    * [ponytail](https://github.com/dietrichgebert/ponytail)
    * [headroom](https://github.com/headroomlabs-ai/headroom)
    * [taste-skill](https://github.com/leonxlnx/taste-skill)
    * [archify](https://github.com/tt-a1i/archify)
    * [codex-with-chatgpt](https://github.com/XiaoDuoYa/codex-with-chatgpt)
    * [reverse-skill](https://github.com/zhaoxuya520/reverse-skill)
  * Others
    [aoci-code](https://github.com/aoci-spec/aoci-code)
    [Symphony](https://github.com/openai/symphony)
    [codex-chatgpt-web](https://github.com/miuuyy/codex-chatgpt-web)
    [OmniRoute](https://github.com/diegosouzapw/OmniRoute)
    [graphify](https://github.com/Graphify-Labs/graphify)

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
* 


### mac
* iterm
* charles
* betterdisplay
* stats
* appcleaner
* macs fan control
* displaylink manager
* handbrake
* iina
* raycast
* xcode
* utm
* ghostty
  * set config with: shell-integration-features = ssh-terminfo,ssh-env
* battery
* wireguard
* [macshot](https://github.com/sw33tLie/macshot)
* [Crisp](https://github.com/didriksg/Crisp)
* [vorssaint](https://github.com/vorssaint/vorssaint-utils)
* [rectangleapp](https://rectangleapp.com/)
* [applite](https://github.com/milanvarady/applite)
* [otty](https://otty.sh/)





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


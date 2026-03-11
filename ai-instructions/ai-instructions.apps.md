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


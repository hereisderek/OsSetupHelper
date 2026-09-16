## settings 

### common
* setup ssh/git
    * specified through override config file
    * setup username, user email
    * other common global variables
    * trust ssh key from list of specified github account 
* setup environment
    * ~/.config/env/{env.sh, app/*}

### mac os
* clean dock icons (`clean_dock_icons`) — removes known Apple stock apps from the Dock (Safari, Mail, Messages, Maps, Photos, FaceTime, Phone, Calendar, Contacts, Reminders, Notes, Freeform, Music, TV, Podcasts, News, Games, App Store, iPhone Mirroring); keeps Finder, Launchpad/Apps, System Settings, Trash, and anything else (e.g. your own installed apps) — named-list based specifically so it's idempotent and never strips a real app back out on a re-run
* change dock location (`dock_location`) — 'left', 'bottom', or 'right'; supports on/off/skip (defaults to skip, 'left' in override)
* change dock size (`dock_size`) — icon size in pixels (e.g. 48); supports on/off/skip (defaults to skip, 48 in override)
* allow mouse right click
* swap external keyboard command key and option key
* allow tap to click (`allow_tap_to_click`) — supports enable (`true`), disable (`false`), or skip (defaults to skip, enabled in override)
* show hidden files in finder
* show all filename extensions in finder
* disable "are you sure" warning when renaming a file's extension
* allow three finger drag (`allow_three_finger_drag`) — supports enable (`true`), disable (`false`), or skip (defaults to false, enabled in override); sets TrackpadThreeFingerDrag, NSGlobalDomain currentHost threeFingerDragGesture, and clears conflicting 3-finger swipe gestures (sets Horiz/Vert swipes to 0 when enabled, 2 when disabled)
* folder defaults to list view, sorted by name, and show item info
* default finder location to home (`finder_default_location_home`) — opens new Finder window in `~` (`true`), Recents (`false`), or skip (defaults to skip, enabled in override)
* search defaults to current folder (`search_current_folder`) — search current folder (`true`), search this Mac (`false`), or skip (defaults to enabled, enabled in override)

* desktop icon defaults to showing hard disks, external disks, and removable media
* desktop icon labels position defaults to right, and show item info
* show battery percentage in menu bar
* show volume in menu bar
* set main display resolution to "More Space" (`display_more_space`) — installs `displayplacer` (Homebrew formula) and selects the largest `scaling:on` mode reported for the main display, since there's no `defaults write` key for this; opt-in like `clean_dock_icons`
* exclude safari from spotlight indexing
* touch key lock drag
* brew setting: HOMEBREW_AUTO_UPDATE_SECS
* remove show help menu shortcut (cmd + shift + /) due to conflict with ide shortcut
* time machine backup frequency and exclusions (`time_machine_frequency`, `time_machine_exclusions`):
    * backup frequency: `'hourly'`, `'daily'`, `'weekly'`, `'manual'` (disables AutoBackup), or custom seconds; omit/null/skip to skip
    * exclusions: fixed-path exclusions list via `tmutil addexclusion -p`, persisted in `/Library/Preferences/com.apple.TimeMachine.plist` `SkipPaths`, supporting `~` path expansion, idempotent check against existing exclusions, and removal via `state: absent` or `!` / `-` prefix
* **UI Reload Policy**: Handlers (`Restart Finder`, `Restart Dock`, `Restart SystemUIServer`, `Activate Settings`) are defined in `content/settings/mac/macos_tweaks/handlers/main.yml` (imported into `bootstrap.yml`) and run once at the end of the playbook run. Roles and subtasks must never call `flush_handlers` or execute standalone `killall` commands so that all system and app changes take place before UI services reload together.
### windows
* show hidden file
* show file extension
* show desktop icon (Computer, Rubish bin, etc.)
* disable auto play on removeable devices

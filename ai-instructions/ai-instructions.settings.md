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
* allow mouse right click
* swap external keyboard command key and option key
* allow tap to click
* show hidden files in finder
* show all filename extensions in finder
* disable "are you sure" warning when renaming a file's extension
* allow three finger drag
* folder defaults to list view, sorted by name, and show item info
* search defaults to current folder
* desktop icon defaults to showing hard disks, external disks, and removable media
* desktop icon labels position defaults to right, and show item info
* show battery percentage in menu bar
* show volume in menu bar
* set main display resolution to "More Space" (`display_more_space`) — installs `displayplacer` (Homebrew formula) and selects the largest `scaling:on` mode reported for the main display, since there's no `defaults write` key for this; opt-in like `clean_dock_icons`
* exclude safari from spotlight indexing
* touch key lock drag
* brew setting: HOMEBREW_AUTO_UPDATE_SECS
* remove show help menu shortcut (cmd + shift + /) due to conflict with ide shortcut
### windows
* show hidden file
* show file extension
* show desktop icon (Computer, Rubish bin, etc.)
* disable auto play on removeable devices

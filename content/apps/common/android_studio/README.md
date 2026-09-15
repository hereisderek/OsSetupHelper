# android_studio

Android IDE.

> **Note**: the installer task in `tasks/main.yml` is currently disabled (`when: false`) — the role only prints a manual-install reminder pointing at JetBrains Toolbox / the official site.

- **macOS**: Homebrew Cask `android-studio` (verified).
- **Windows**: winget `Google.AndroidStudio` (verified in winget-pkgs; official dl.google.com installer).
- **Linux**: not wired up. Google publishes no apt/yum repo for Android Studio — official Linux install is a direct .zip download (or the community AUR package/snap). Left blank deliberately.

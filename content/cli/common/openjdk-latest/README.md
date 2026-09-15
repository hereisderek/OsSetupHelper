# openjdk-latest

Latest OpenJDK via the centralized installer, plus macOS JVM symlink into `/Library/Java/JavaVirtualMachines`.

- **macOS**: Homebrew formula `openjdk` (tracks the current GA JDK).
- **Windows**: winget `Microsoft.OpenJDK.25`. Bare `Microsoft.OpenJDK` does not exist in winget — Microsoft publishes one id per LTS line (`.17`, `.21`, `.25`), and 25 is the current LTS. Bump this id when the next LTS ships; the brew formula may meanwhile be a newer non-LTS GA than the winget id.
- **Linux**: `default-jdk` (verified in Ubuntu main; Debian's equivalent meta-package). Fedora uses `java-latest-openjdk` and Arch `jdk-openjdk` — the installer can't express per-distro names, so expect the graceful manual-install message there.

# PowerShell

Cross-platform CLI role. Installs PowerShell 7.

- **macOS**: Homebrew **formula** `powershell` (verified via `brew info`; there is no `powershell` cask — this is why the role lives under `cli/`, whose macOS installer path uses formulas, rather than `apps/`, which installs casks).
- **Windows**: winget `Microsoft.PowerShell` (verified against the [winget-pkgs manifest](https://github.com/microsoft/winget-pkgs/tree/master/manifests/m/Microsoft/PowerShell)).
- **Linux**: not wired up. PowerShell is not in any distro's default repositories — it requires Microsoft's own apt/yum repo ([packages.microsoft.com](https://packages.microsoft.com)) to be added first. Left blank deliberately rather than half-implemented; the centralized installer gracefully no-ops on Linux. Enable later with a `setup_repo_*.yml` hook in this role.

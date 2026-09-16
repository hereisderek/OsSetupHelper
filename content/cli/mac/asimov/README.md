# asimov

Automatically exclude development dependencies (e.g. `node_modules`, `.venv`, `target`, `vendor`) from Apple Time Machine backups (https://github.com/AsimovMac/asimov).

- **macOS**: installed via Homebrew formula `asimov`.
- **Background Service**: optionally registers and starts the daily scheduled launchd job via `brew services start asimov` (`asimov_start_service: true` by default).
- **Windows/Linux**: not applicable (macOS Time Machine specific).

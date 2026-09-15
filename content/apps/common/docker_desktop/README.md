# docker_desktop

Docker Desktop.

- **macOS**: Homebrew Cask `docker`.
- **Windows**: winget `Docker.DockerDesktop`.
- **Linux**: not wired up. The old `docker-ce` key installed Docker *Engine* (a different product) and itself required Docker's own apt/yum repo; Docker *Desktop* for Linux is a separate `docker-desktop` package distributed only via download.docker.com. Neither is in any distro's default repos, so the key is blank rather than half-implemented — the centralized installer gracefully no-ops on Linux. Enable later with a `setup_repo_*.yml` hook in this role.

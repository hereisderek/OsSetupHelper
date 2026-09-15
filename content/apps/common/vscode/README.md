# VS Code Module

This folder is a self-contained Ansible role for installing and configuring Visual Studio Code.

## Inputs

The role reads its runtime values from `selections.apps.vscode` in the root config.

Supported fields:

- `enabled` (bool)
- `version` (string; currently informational)
- `custom_paths.install_dir`
- `custom_paths.config_dir`
- `settings` (mapping written to `settings.json`)
- `extensions` (list of extension IDs)
- `post_install` (list of hooks)
- `os_overrides.{mac|linux|win}`

Each post-install hook requires `blocking: true|false`.

## Idempotency

- Package install steps only run when the package is missing.
- `settings.json` is rendered via template and only updates on content change.
- Extensions are installed only if not already present.
- Hooks can use `creates` to prevent re-running.

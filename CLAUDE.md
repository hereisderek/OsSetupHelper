# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Read [ai-instructions/ai-instructions.md](ai-instructions/ai-instructions.md) first** — it is the canonical, up-to-date architecture/technical reference for this repo (orchestrator internals, Ansible playbook structure, config merge semantics, testing). Per-category implementation notes live alongside it (`ai-instructions/ai-instructions.apps.md`, `.settings.md`, `.cli.md`); open work and known issues are tracked in [ai-instructions/TODO.md](ai-instructions/TODO.md).

User-facing install/usage docs (not this file's concern) live in [README.md](README.md).

## Commands

```bash
python3 -m pip install -r requirements.txt   # setup
python3 orchestrator.py                      # interactive TUI
python3 orchestrator.py --resume             # resume last selection
python3 orchestrator.py --non-interactive --config config.yaml
python3 orchestrator.py --all -y             # install everything applicable, no prompts
python3 orchestrator.py --apps vscode chrome --tools zsh_ohmyzsh --settings macos_tweaks
python3 orchestrator.py --apps all --exclude steam discord   # 'all' for a category, minus exclusions
python3 orchestrator.py -K --tools zsh_ohmyzsh               # prompt for sudo password
./bootstrap.sh --sync                         # curl-able entrypoint; --sync updates remote config repo
python3 tests/test_deep_merge.py -v           # unit tests
```

There is no `venv/` dependency — do not add one; the checked-in `venv/` is a local artifact and should be ignored.

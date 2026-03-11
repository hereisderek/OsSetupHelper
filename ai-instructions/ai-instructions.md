Role: You are a Senior DevOps Engineer and Systems Administrator specializing in Ansible, cross-platform automation, and clean architecture.

Objective: I want to build a cross-platform OS initialization and setup utility for Windows, macOS, and Linux. It must prioritize code transparency so users can easily read and modify the source scripts. 

Tech Stack: 
* Execution Engine: Ansible (Playbooks and Roles).
* Frontend UI/Orchestrator: A lightweight Python TUI script (e.g., using InquirerPy, Rich, or Textual) that handles user interaction, parses configurations, and invokes ansible-playbook locally.
* Config Format: YAML.

Core Features Required:
1. Dynamic Configuration Loading: The Python frontend must load user preferences (what to install, paths, etc.) either from a local YAML file or fetched via a GitHub RAW link.
2. Interactive TUI: Present the user with interactive toggles to opt-in/out of specific apps, tools, and system optimizations based on their loaded config. 
3. Ansible Invocation: The frontend will take the user's selections and dynamically pass them to Ansible as extra-vars or generate a dynamic playbook run-list.
4. Idempotency: All Ansible tasks must be strictly idempotent (safe to run multiple times without breaking things).

5. Centralized Installer: All application installations (common, mac, linux, win) should use the centralized installer task located at `_shared_tasks/installer/main.yml`. Roles should simply include this task, and the installer will handle OS-specific package resolution.
6. OS-Aware Orchestration: The Python frontend detects the current OS and filters roles/prompts accordingly. It also checks for already installed apps and supports session resume via `~/.ossetup_resume.yaml`.

Directory Structure Constraint:
The project MUST adhere to the following directory structure, treating each app/tool as a self-contained module (similar to Ansible Roles):

root/
├── _shared_tasks/           # Centralized tasks shared across roles
│   └── installer/           # Platform-specific installation logic
│       ├── main.yml         # Entry point for all app installs
│       ├── mac_install_cask.yml
│       ├── win_install_package.yml
│       └── linux_install_package.yml
├── settings/                # OS optimization and cleanup scripts/tasks
│   ├── win/
│   ├── linux/
│   └── mac/
├── apps/                    # GUI Applications
│   ├── common/              # Cross-platform apps
│   ├── win/
│   ├── linux/
│   └── mac/
├── commandline_tools/       # CLI Tools
│   ├── common/
│   ├── win/
│   ├── linux/
│   └── mac/
└── orchestrator.py          # The Python UI frontend (OS-aware, Resume-enabled)

*Requirement:* Each app or tool under these directories must be in its own folder. That folder must contain all instructions for that specific software: how to download it, install it, configure it, and run post-install scripts (like adding to environment variables). 

First Step Request:
DO NOT generate the entire codebase yet. Please provide:
1. A detailed breakdown of how you would structure a single application folder (e.g., apps/common/vscode/) using Ansible best practices within my requested directory structure.
2. The proposed YAML schema for the user preference file. Show how an app with post-install hooks, custom paths, and OS-specific overrides would look.
3. A brief explanation of how the Python frontend will construct the ansible-playbook command based on the user's TUI selections.

Ask me for approval on the schema and folder structure before writing the execution logic.
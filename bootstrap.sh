#!/bin/bash
# 🚀 Universal OS Bootstrapper - OS Setup Helper
# This script automates the setup of the Python environment and runs the Ansible orchestrator.
# Usage: bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" [args...]

set -e

# Configuration
REPO_URL="${OS_SETUP_REPO_URL:-https://github.com/hereisderek/OsSetupHelper.git}"
DEFAULT_CLONE_DIR="$HOME/.config/ossetuphelper"

# --- Helper Functions (Must be defined before use) ---

# Function to find a working python3 interpreter
find_python() {
    if command -v python3 >/dev/null 2>&1; then
        echo "python3"
    elif command -v python >/dev/null 2>&1; then
        # Check if 'python' is actually version 3
        if python --version 2>&1 | grep -q "Python 3"; then
            echo "python"
        fi
    fi
}

# Function to ensure Homebrew is installed and in PATH
ensure_brew_installed() {
    local OS_TYPE=$(uname -s)
    if [ "$OS_TYPE" == "Darwin" ]; then
        echo "🔍 Checking for Homebrew..."

        if ! command -v brew >/dev/null 2>&1; then
            # Check standard paths first before installing
            if [[ -f /opt/homebrew/bin/brew ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [[ -f /usr/local/bin/brew ]]; then
                eval "$(/usr/local/bin/brew shellenv)"
            else
                echo "📦 Homebrew not found. Installing..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                if [[ -f /opt/homebrew/bin/brew ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [[ -f /usr/local/bin/brew ]]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi
        fi
        
        if command -v brew >/dev/null 2>&1; then
            echo "✅ Homebrew is ready."
        else
            echo "❌ Failed to initialize Homebrew."
            exit 1
        fi
    fi
}

# Function to safely and smartly sync submodules without crashing
smart_sync_submodules() {
    local SHOULD_FORCE_UPDATE=$1
    if [ ! -f ".gitmodules" ]; then return 0; fi

    echo "📂 Synchronizing submodules..."
    
    local CONFIG_URL=$(git config -f .gitmodules submodule.config.url || echo "https://github.com/hereisderek/OsSetupHelperConfig.git")
    
    if [ ! -d "config/.git" ]; then
        echo "  - Initializing config submodule..."
        rm -rf config
        git clone --quiet "$CONFIG_URL" config || echo "⚠️  Manual clone of config failed."
    elif [ "$SHOULD_FORCE_UPDATE" = true ]; then
        echo "  - Updating config submodule..."
        (cd config && git fetch --all && (git reset --hard origin/main || git reset --hard origin/master || git pull)) || echo "⚠️  Manual update of config failed."
    fi

    # Try standard sync for any other submodules, but suppress stderr to hide crashes
    git submodule sync >/dev/null 2>&1 || true
    git submodule update --init --quiet >/dev/null 2>&1 || true
}

# --- Initialization and Argument Parsing ---

# Detect if we are running from a local git repo of this project
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/.git" ] && git -C "$SCRIPT_DIR" remote -v | grep -q "OsSetupHelper"; then
    echo "🏠 Running from local project directory: $SCRIPT_DIR"
    CLONE_DIR="$SCRIPT_DIR"
    IS_LOCAL=true
else
    CLONE_DIR="${OS_SETUP_DIR:-$DEFAULT_CLONE_DIR}"
    IS_LOCAL=false
fi

# Check for --sync parameter
SHOULD_SYNC=false
REMAINING_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--sync" ]]; then
        SHOULD_SYNC=true
    else
        REMAINING_ARGS+=("$arg")
    fi
done

echo "----------------------------------------------------------------"
echo "  🛠️  OS Setup Helper: Automated Bootstrapper"
echo "----------------------------------------------------------------"

# Detect OS
OS_TYPE="$(uname -s)"
echo "📍 Detected OS: $OS_TYPE"

# 1. Prerequisites check & installation
if [ "$OS_TYPE" == "Darwin" ]; then
    echo "🔍 Checking for Xcode Command Line Tools..."
    if ! xcode-select -p >/dev/null 2>&1; then
        echo "📦 Xcode Command Line Tools not found. Installing..."
        touch /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
        PROD=$(softwareupdate -l | grep "\*.*Command Line" | head -n 1 | awk -F"*" '{print $2}' | sed -e 's/^ *//' | tr -d '\n')
        if [ -n "$PROD" ]; then
            softwareupdate -i "$PROD" --verbose
        else
            xcode-select --install
        fi
        
        echo "⏳ Waiting for Xcode Command Line Tools to finish installing..."
        until xcode-select -p >/dev/null 2>&1; do
            sleep 5
        done
        rm -f /tmp/.com.apple.dt.CommandLineTools.installondemand.in-progress
        echo "✅ Xcode Command Line Tools installed."
    else
        echo "✅ Xcode Command Line Tools already installed."
    fi
    
    # Ensure Homebrew is ready
    ensure_brew_installed
fi

echo "🔍 Checking for Python 3..."
PYTHON_CMD=$(find_python)

if [ -z "$PYTHON_CMD" ]; then
    echo "📦 Python 3 not found. Attempting to install..."
    case "$OS_TYPE" in
        Darwin)
            brew install python
            ;;
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update -y && sudo apt-get install -y git python3 python3-venv
            elif command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y git python3
            elif command -v pacman >/dev/null 2>&1; then
                sudo pacman -Sy --noconfirm git python
            fi
            ;;
        *)
            echo "❌ Could not automatically install Python for OS: $OS_TYPE"
            echo "Please install Python 3 manually and try again."
            exit 1
            ;;
    esac
    PYTHON_CMD=$(find_python)
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Python 3 is still not found after installation attempt."
    exit 1
fi

echo "✅ Using Python: $($PYTHON_CMD --version)"

# 2. Clone/Update Repository
if [ "$IS_LOCAL" = true ]; then
    if [ "$SHOULD_SYNC" = true ]; then
        echo "📂 Synchronizing local repository..."
        git fetch --all
        git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)
        smart_sync_submodules true
    else
        echo "📂 Using local files (skipping sync). Use --sync to update."
        smart_sync_submodules false
    fi
else
    if [ ! -d "$CLONE_DIR" ]; then
        echo "📂 Cloning repository to $CLONE_DIR..."
        git clone --recursive "$REPO_URL" "$CLONE_DIR"
        cd "$CLONE_DIR"
        smart_sync_submodules false
    else
        echo "📂 Found existing installation in $CLONE_DIR"
        cd "$CLONE_DIR"
        if [ "$SHOULD_SYNC" = true ]; then
            echo "📂 Synchronizing with $REPO_URL..."
            git remote set-url origin "$REPO_URL"
            git fetch --all
            git reset --hard origin/main || git reset --hard origin/master
            smart_sync_submodules true
        else
            echo "📂 Using existing files (skipping sync). Use --sync to update."
            smart_sync_submodules false
        fi
    fi
fi

cd "$CLONE_DIR"

# 3. Setup Virtual Environment
VENV_DIR="venv"
REBUILD_VENV=false

if [ -d "$VENV_DIR" ]; then
    # Determine the venv python path (handles Windows/Unix differences)
    if [ -f "$VENV_DIR/bin/python" ]; then
        VENV_PYTHON="$VENV_DIR/bin/python"
    elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
    else
        VENV_PYTHON=""
    fi

    if [ -n "$VENV_PYTHON" ] && "$VENV_PYTHON" -c "import sys; sys.exit(0)" >/dev/null 2>&1; then
        echo "♻️  Existing virtual environment is functional. Reusing it."
    else
        echo "⚠️  Existing virtual environment is broken or incomplete. Rebuilding..."
        rm -rf "$VENV_DIR"
        REBUILD_VENV=true
    fi
else
    REBUILD_VENV=true
fi

if [ "$REBUILD_VENV" = true ]; then
    echo "🐍 Creating Python virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    # Re-detect venv python
    if [ -f "$VENV_DIR/bin/python" ]; then VENV_PYTHON="$VENV_DIR/bin/python"
    else VENV_PYTHON="$VENV_DIR/Scripts/python.exe"; fi
fi

# Use venv python directly to run pip to avoid PATH issues
if [ "$REBUILD_VENV" = true ]; then
    echo "📦 Installing Python dependencies..."
    "$VENV_PYTHON" -m pip install --quiet --upgrade pip
    "$VENV_PYTHON" -m pip install --quiet -r requirements.txt
else
    echo "📦 Checking/Updating Python dependencies..."
    "$VENV_PYTHON" -m pip install --quiet -r requirements.txt
fi

# 4. Execute Orchestrator
echo "🎨 Starting the Orchestrator..."
echo "----------------------------------------------------------------"
"$VENV_PYTHON" orchestrator.py "${REMAINING_ARGS[@]}"

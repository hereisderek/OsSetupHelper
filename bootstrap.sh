#!/bin/bash
# 🚀 Universal OS Bootstrapper - OS Setup Helper
# This script automates the setup of the Python environment and runs the Ansible orchestrator.
# Usage: bash -c "$(curl -fsSL https://raw.githubusercontent.com/hereisderek/OsSetupHelper/main/bootstrap.sh)" [args...]

set -e

# Configuration
REPO_URL="${OS_SETUP_REPO_URL:-https://github.com/hereisderek/OsSetupHelper.git}"
DEFAULT_CLONE_DIR="$HOME/.config/ossetuphelper"

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
echo "🔍 Checking for Python 3..."

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

PYTHON_CMD=$(find_python)

if [ -z "$PYTHON_CMD" ]; then
    echo "📦 Python 3 not found. Attempting to install..."
    case "$OS_TYPE" in
        Darwin)
            if ! command -v brew >/dev/null 2>&1; then
                echo "📦 Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                if [[ -f /opt/homebrew/bin/brew ]]; then eval "$(/opt/homebrew/bin/brew shellenv)";
                elif [[ -f /usr/local/bin/brew ]]; then eval "$(/usr/local/bin/brew shellenv)"; fi
            fi
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
        echo "📂 Synchronizing submodules..."
        git submodule sync --recursive
        git submodule update --init --recursive --remote
    else
        echo "📂 Using local files (skipping sync). Use --sync to update."
        # Still ensure submodules are initialized if they exist
        if [ -f ".gitmodules" ]; then
            git submodule update --init --recursive
        fi
    fi
else
    if [ ! -d "$CLONE_DIR" ]; then
        echo "📂 Cloning repository to $CLONE_DIR..."
        git clone --recursive "$REPO_URL" "$CLONE_DIR"
        cd "$CLONE_DIR"
    else
        echo "📂 Found existing installation in $CLONE_DIR"
        cd "$CLONE_DIR"
        if [ "$SHOULD_SYNC" = true ]; then
            echo "📂 Synchronizing with $REPO_URL..."
            git remote set-url origin "$REPO_URL"
            git fetch --all
            git reset --hard origin/main || git reset --hard origin/master
            echo "📂 Synchronizing submodules..."
            git submodule sync --recursive
            git submodule update --init --recursive --remote
        else
            echo "📂 Using existing files (skipping sync). Use --sync to update."
            git submodule update --init --recursive
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
fi

# Locate activation script
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
elif [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
fi

if [ "$REBUILD_VENV" = true ]; then
    echo "📦 Installing Python dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
else
    echo "📦 Checking/Updating Python dependencies..."
    pip install --quiet -r requirements.txt
fi

# 4. Execute Orchestrator
echo "🎨 Starting the Orchestrator..."
echo "----------------------------------------------------------------"
# Pass all remaining arguments to orchestrator.py
python3 orchestrator.py "${REMAINING_ARGS[@]}"

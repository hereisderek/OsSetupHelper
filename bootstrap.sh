#!/bin/bash
# 🚀 Universal OS Bootstrapper - OS Setup Helper
# This script automates the setup of the Python environment and runs the Ansible orchestrator.
# Usage: bash -c "$(curl -fsSL https://raw.githubusercontent.com/derek/OsSetupHelper/main/bootstrap.sh)" [args...]

set -e

# Configuration
REPO_URL="${OS_SETUP_REPO_URL:-https://github.com/derek/OsSetupHelper.git}"
CLONE_DIR="${OS_SETUP_DIR:-$HOME/.ossetuphelper}"

echo "----------------------------------------------------------------"
echo "  🛠️  OS Setup Helper: Automated Bootstrapper"
echo "----------------------------------------------------------------"

# Detect OS
OS_TYPE="$(uname -s)"
echo "📍 Detected OS: $OS_TYPE"

# Check for Windows/WSL
if [[ "$OS_TYPE" == *"NT"* ]] || [[ "$OS_TYPE" == *"MSYS"* ]] || [[ "$OS_TYPE" == *"MINGW"* ]]; then
    # We are in Git Bash, MSYS or Windows PowerShell? (No, this is bash)
    # If we're here, we have bash. Let's check for python3.
    if ! command -v python3 >/dev/null 2>&1; then
        echo "❌ Python 3 is not found. Please install Python 3 from python.org or the Microsoft Store."
        exit 1
    fi
    # If in MSYS/MINGW (Git Bash), we should be careful about paths but orchestrator.py handles it
fi

# 1. Prerequisites check & installation
case "$OS_TYPE" in
    Darwin)
        if ! command -v brew >/dev/null 2>&1; then
            echo "📦 Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            # Ensure brew is available in current shell
            if [[ -f /opt/homebrew/bin/brew ]]; then
                eval "$(/opt/homebrew/bin/brew shellenv)"
            elif [[ -f /usr/local/bin/brew ]]; then
                eval "$(/usr/local/bin/brew shellenv)"
            fi
        fi
        if ! command -v git >/dev/null 2>&1; then
            echo "📦 Installing Git via Homebrew..."
            brew install git
        fi
        if ! command -v python3 >/dev/null 2>&1; then
            echo "📦 Installing Python via Homebrew..."
            brew install python
        fi
        ;;
    Linux)
        if command -v apt-get >/dev/null 2>&1; then
            echo "📦 Installing Git and Python via apt..."
            sudo apt-get update -y
            sudo apt-get install -y git python3 python3-venv
        elif command -v dnf >/dev/null 2>&1; then
            echo "📦 Installing Git and Python via dnf..."
            sudo dnf install -y git python3
        elif command -v pacman >/dev/null 2>&1; then
            echo "📦 Installing Git and Python via pacman..."
            sudo pacman -Sy --noconfirm git python
        else
            echo "⚠️  Unknown package manager. Please ensure git, python3 and venv are installed."
        fi
        ;;
    *)
        echo "❌ Unsupported OS type for this bootstrap script: $OS_TYPE"
        echo "Please install Git and Python manually and clone the repository."
        exit 1
        ;;
esac

# 2. Clone/Update Repository
if [ ! -d "$CLONE_DIR" ]; then
    echo "📂 Cloning repository to $CLONE_DIR..."
    git clone "$REPO_URL" "$CLONE_DIR"
else
    echo "📂 Updating existing repository in $CLONE_DIR..."
    cd "$CLONE_DIR"
    git pull
fi

cd "$CLONE_DIR"

# 3. Setup Virtual Environment
if [ ! -d "venv" ]; then
    echo "🐍 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "🐍 Activating virtual environment..."
source venv/bin/activate

echo "📦 Installing/Updating Python dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# 4. Execute Orchestrator
echo "🎨 Starting the Orchestrator..."
echo "----------------------------------------------------------------"
# Pass all arguments from this script to orchestrator.py
python3 orchestrator.py "$@"

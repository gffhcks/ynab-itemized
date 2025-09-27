#!/bin/bash
# YNAB Itemized - Unix/Linux/macOS Setup Script
# This script sets up the development environment on Unix-like systems

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
INSTALL_PYTHON=false
INSTALL_SYSTEM_DEPS=false
DEV_SETUP=false
SHOW_HELP=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-python)
            INSTALL_PYTHON=true
            shift
            ;;
        --install-system-deps)
            INSTALL_SYSTEM_DEPS=true
            shift
            ;;
        --dev-setup)
            DEV_SETUP=true
            shift
            ;;
        --help|-h)
            SHOW_HELP=true
            shift
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

show_help() {
    echo -e "${GREEN}YNAB Itemized - Unix/Linux/macOS Setup Script${NC}"
    echo ""
    echo -e "${YELLOW}Usage: ./scripts/setup-unix.sh [OPTIONS]${NC}"
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo "  --install-python      Install Python (if not available)"
    echo "  --install-system-deps Install system dependencies"
    echo "  --dev-setup           Set up development environment"
    echo "  --help, -h            Show this help message"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  ./scripts/setup-unix.sh --dev-setup"
    echo "  ./scripts/setup-unix.sh --install-system-deps --dev-setup"
    echo ""
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command_exists apt; then
            echo "ubuntu"
        elif command_exists yum; then
            echo "rhel"
        elif command_exists pacman; then
            echo "arch"
        else
            echo "linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    else
        echo "unknown"
    fi
}

install_system_deps() {
    echo -e "${BLUE}📦 Installing system dependencies...${NC}"

    OS=$(detect_os)

    case $OS in
        ubuntu)
            echo -e "${YELLOW}Installing dependencies for Ubuntu/Debian...${NC}"
            sudo apt update
            sudo apt install -y python3-dev python3-venv python3-pip build-essential git
            ;;
        rhel)
            echo -e "${YELLOW}Installing dependencies for RHEL/CentOS/Fedora...${NC}"
            if command_exists dnf; then
                sudo dnf install -y python3-devel python3-pip gcc gcc-c++ make git
            else
                sudo yum install -y python3-devel python3-pip gcc gcc-c++ make git
            fi
            ;;
        arch)
            echo -e "${YELLOW}Installing dependencies for Arch Linux...${NC}"
            sudo pacman -S --noconfirm python python-pip base-devel git
            ;;
        macos)
            echo -e "${YELLOW}Installing dependencies for macOS...${NC}"
            if command_exists brew; then
                brew install python git
            else
                echo -e "${RED}❌ Homebrew not found. Please install it first: https://brew.sh${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}❌ Unsupported operating system: $OSTYPE${NC}"
            echo "Please install Python 3.9+, pip, and git manually."
            exit 1
            ;;
    esac

    echo -e "${GREEN}✅ System dependencies installed${NC}"
}

install_python() {
    echo -e "${BLUE}🐍 Checking Python installation...${NC}"

    if command_exists python3; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        echo -e "${GREEN}✅ Python already installed: $PYTHON_VERSION${NC}"

        # Check if version is 3.9+
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

        if [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -ge 9 ]]; then
            echo -e "${GREEN}✅ Python version is compatible${NC}"
            return
        else
            echo -e "${YELLOW}⚠️  Python version $PYTHON_VERSION is too old. Need 3.9+${NC}"
        fi
    fi

    echo -e "${YELLOW}Installing Python...${NC}"
    install_system_deps
}

setup_development() {
    echo -e "${BLUE}🔧 Setting up development environment...${NC}"

    # Check prerequisites
    if ! command_exists python3; then
        echo -e "${RED}❌ Python not found. Run with --install-python first.${NC}"
        exit 1
    fi

    if ! command_exists git; then
        echo -e "${RED}❌ Git not found. Run with --install-system-deps first.${NC}"
        exit 1
    fi

    # Check if we're in the right directory
    if [[ ! -f "pyproject.toml" ]]; then
        echo -e "${RED}❌ pyproject.toml not found. Please run from the project root.${NC}"
        exit 1
    fi

    # Install nox
    echo -e "${YELLOW}📦 Installing nox...${NC}"
    python3 -m pip install --user nox

    # Add user bin to PATH if not already there
    USER_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
        echo -e "${YELLOW}Adding $USER_BIN to PATH...${NC}"
        export PATH="$USER_BIN:$PATH"

        # Add to shell profile
        if [[ -f "$HOME/.bashrc" ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        elif [[ -f "$HOME/.zshrc" ]]; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        fi
    fi

    # Run development setup
    echo -e "${YELLOW}🔧 Running development setup...${NC}"
    python3 -m nox -s dev_setup

    echo ""
    echo -e "${GREEN}✅ Development environment setup complete!${NC}"
    echo ""
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Set your YNAB API token: export YNAB_API_TOKEN=your_token_here"
    echo "  2. Initialize database: nox -s init_db"
    echo "  3. Run tests: nox -s tests"
    echo "  4. Format code: nox -s format"
    echo ""
    echo -e "${YELLOW}Available nox sessions:${NC}"
    python3 -m nox --list
}

# Main script logic
if [[ "$SHOW_HELP" == true ]]; then
    show_help
    exit 0
fi

if [[ "$INSTALL_PYTHON" == false && "$INSTALL_SYSTEM_DEPS" == false && "$DEV_SETUP" == false ]]; then
    echo -e "${RED}❌ No action specified. Use --help for usage information.${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 YNAB Itemized - Unix/Linux/macOS Setup${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

if [[ "$INSTALL_SYSTEM_DEPS" == true ]]; then
    install_system_deps
    echo ""
fi

if [[ "$INSTALL_PYTHON" == true ]]; then
    install_python
    echo ""
fi

if [[ "$DEV_SETUP" == true ]]; then
    setup_development
fi

echo -e "${GREEN}🎉 Setup complete!${NC}"

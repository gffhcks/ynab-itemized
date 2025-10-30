# YNAB Itemized - Windows Setup Script
# This script sets up the development environment on Windows

param(
    [switch]$InstallPython,
    [switch]$InstallGit,
    [switch]$DevSetup,
    [switch]$Help
)

function Show-Help {
    Write-Host "YNAB Itemized - Windows Setup Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\scripts\setup-windows.ps1 [OPTIONS]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -InstallPython    Install Python using winget"
    Write-Host "  -InstallGit       Install Git using winget"
    Write-Host "  -DevSetup         Set up development environment"
    Write-Host "  -Help             Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\scripts\setup-windows.ps1 -DevSetup"
    Write-Host "  .\scripts\setup-windows.ps1 -InstallPython -InstallGit -DevSetup"
    Write-Host ""
}

function Test-Command {
    param([string]$Command)
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Install-Python {
    Write-Host "🐍 Installing Python..." -ForegroundColor Blue

    if (Test-Command "python") {
        $version = python --version 2>&1
        Write-Host "✅ Python already installed: $version" -ForegroundColor Green
        return
    }

    if (Test-Command "winget") {
        Write-Host "Installing Python using winget..." -ForegroundColor Yellow
        winget install Python.Python.3.11
    }
    elseif (Test-Command "choco") {
        Write-Host "Installing Python using Chocolatey..." -ForegroundColor Yellow
        choco install python
    }
    else {
        Write-Host "❌ Neither winget nor Chocolatey found." -ForegroundColor Red
        Write-Host "Please install Python manually from https://python.org" -ForegroundColor Yellow
        exit 1
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    if (Test-Command "python") {
        $version = python --version 2>&1
        Write-Host "✅ Python installed successfully: $version" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Python installation failed. Please install manually." -ForegroundColor Red
        exit 1
    }
}

function Install-Git {
    Write-Host "📦 Installing Git..." -ForegroundColor Blue

    if (Test-Command "git") {
        $version = git --version 2>&1
        Write-Host "✅ Git already installed: $version" -ForegroundColor Green
        return
    }

    if (Test-Command "winget") {
        Write-Host "Installing Git using winget..." -ForegroundColor Yellow
        winget install Git.Git
    }
    elseif (Test-Command "choco") {
        Write-Host "Installing Git using Chocolatey..." -ForegroundColor Yellow
        choco install git
    }
    else {
        Write-Host "❌ Neither winget nor Chocolatey found." -ForegroundColor Red
        Write-Host "Please install Git manually from https://git-scm.com" -ForegroundColor Yellow
        exit 1
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    if (Test-Command "git") {
        $version = git --version 2>&1
        Write-Host "✅ Git installed successfully: $version" -ForegroundColor Green
    }
    else {
        Write-Host "❌ Git installation failed. Please install manually." -ForegroundColor Red
        exit 1
    }
}

function Setup-Development {
    Write-Host "🔧 Setting up development environment..." -ForegroundColor Blue

    # Check prerequisites
    if (-not (Test-Command "python")) {
        Write-Host "❌ Python not found. Run with -InstallPython first." -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Command "git")) {
        Write-Host "❌ Git not found. Run with -InstallGit first." -ForegroundColor Red
        exit 1
    }

    # Check if we're in the right directory
    if (-not (Test-Path "pyproject.toml")) {
        Write-Host "❌ pyproject.toml not found. Please run from the project root." -ForegroundColor Red
        exit 1
    }

    # Install uv
    Write-Host "📦 Installing uv..." -ForegroundColor Yellow
    if (-not (Test-Command "uv")) {
        powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
    else {
        Write-Host "✅ uv already installed" -ForegroundColor Green
    }

    # Install nox with uv
    Write-Host "📦 Installing nox..." -ForegroundColor Yellow
    uv tool install nox

    # Install pre-commit with uv
    Write-Host "📦 Installing pre-commit..." -ForegroundColor Yellow
    if (-not (Test-Command "pre-commit")) {
        uv tool install pre-commit
    }
    else {
        Write-Host "✅ pre-commit already installed" -ForegroundColor Green
    }

    # Run development setup
    Write-Host "🔧 Running development setup..." -ForegroundColor Yellow
    nox -s dev_setup

    # Install pre-commit hooks
    Write-Host "🪝 Installing pre-commit hooks..." -ForegroundColor Yellow
    pre-commit install

    Write-Host ""
    Write-Host "✅ Development environment setup complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Set your YNAB API token: set YNAB_API_TOKEN=your_token_here"
    Write-Host "  2. Initialize database: nox -s init_db"
    Write-Host "  3. Run tests: nox -s tests"
    Write-Host "  4. Run pre-commit: pre-commit run --all-files"
    Write-Host ""
    Write-Host "Available nox sessions:" -ForegroundColor Yellow
    nox --list
}

# Main script logic
if ($Help) {
    Show-Help
    exit 0
}

if (-not ($InstallPython -or $InstallGit -or $DevSetup)) {
    Write-Host "❌ No action specified. Use -Help for usage information." -ForegroundColor Red
    exit 1
}

Write-Host "🚀 YNAB Itemized - Windows Setup" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""

if ($InstallPython) {
    Install-Python
    Write-Host ""
}

if ($InstallGit) {
    Install-Git
    Write-Host ""
}

if ($DevSetup) {
    Setup-Development
}

Write-Host "🎉 Setup complete!" -ForegroundColor Green

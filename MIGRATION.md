# Migration Guide: Make to Nox

This project has migrated from Make to [Nox](https://nox.thea.codes/) for better cross-platform support. This guide helps you transition from the old Make-based workflow to the new Nox-based workflow.

## Why Nox?

- **Cross-Platform**: Works identically on Windows, macOS, and Linux
- **Isolated Environments**: Each task runs in its own virtual environment
- **Python-Native**: Better integration with Python tooling
- **Dependency Management**: Automatic handling of tool dependencies
- **CI/CD Friendly**: Consistent behavior between local and CI environments

## Command Migration

### Old Make Commands → New Nox Commands

| Old Make Command | New Nox Command | Description |
|------------------|-----------------|-------------|
| `make help` | `nox --list` | Show available tasks |
| `make setup` | `nox -s dev_setup` | Complete development setup |
| `make install` | `nox -s install` | Install package |
| `make build` | `nox -s build` | Build package |
| `make test` | `nox -s tests` | Run tests |
| `make test-cov` | `nox -s tests` | Run tests with coverage (default) |
| `make lint` | `nox -s lint` | Run linting |
| `make format` | `nox -s format` | Format code |
| `make clean` | `nox -s clean` | Clean build artifacts |

### New Nox-Only Commands

| Nox Command | Description |
|-------------|-------------|
| `nox -s type_check` | Run type checking with mypy |
| `nox -s format_check` | Check code formatting without changes |
| `nox -s pre_commit` | Run all pre-commit checks |
| `nox -s init_db` | Initialize database |
| `nox -s release_check` | Check if ready for release |

## Installation

### Prerequisites

1. **Install Nox:**
   ```bash
   pip install nox
   ```

2. **Verify Installation:**
   ```bash
   nox --version
   ```

### Quick Setup

Choose your platform:

#### Windows (PowerShell)
```powershell
.\scripts\setup-windows.ps1 -DevSetup
```

#### Linux/macOS (Bash)
```bash
./scripts/setup-unix.sh --dev-setup
```

#### Manual Setup (Any Platform)
```bash
pip install nox
nox -s dev_setup
```

## Common Workflows

### Development Setup
```bash
# Old way
make setup

# New way
nox -s dev_setup
```

### Running Tests
```bash
# Old way
make test

# New way
nox -s tests                    # Run on all Python versions
nox -s "tests-3.11"            # Run on specific Python version
```

### Code Quality Checks
```bash
# Old way
make lint
make format

# New way
nox -s lint type_check          # Run multiple sessions
nox -s format                   # Format code
nox -s format_check            # Check formatting only
```

### Building and Releasing
```bash
# Old way
make clean
make build

# New way
nox -s clean build             # Run multiple sessions
nox -s release_check           # Comprehensive release check
```

## Advanced Usage

### Running Multiple Sessions
```bash
# Run linting and type checking together
nox -s lint type_check

# Run tests on specific Python versions
nox -s "tests-3.10" "tests-3.11"
```

### Passing Arguments to Sessions
```bash
# Pass arguments to pytest
nox -s tests -- --verbose --maxfail=1

# Run specific test file
nox -s tests -- tests/unit/test_models.py
```

### Environment Variables
```bash
# Set environment variables for sessions
YNAB_API_TOKEN=your_token nox -s tests
```

## Troubleshooting

### Common Issues

1. **"Python interpreter X.Y not found"**
   - Install the required Python version or skip with `--skip-missing`
   - Example: `nox -s tests --skip-missing`

2. **Virtual environment creation fails**
   - Clear nox cache: `nox --clean`
   - Reinstall virtualenv: `pip install --upgrade virtualenv`

3. **Permission errors on Windows**
   - Run PowerShell as Administrator
   - Or use: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### Getting Help

```bash
# List all available sessions
nox --list

# Get help for nox
nox --help

# Verbose output for debugging
nox -s tests --verbose
```

## Backward Compatibility

The Makefile is still present for backward compatibility, but it's deprecated. It will be removed in a future version.

### Transition Period Commands

During the transition, you can still use Make commands, but you'll see deprecation warnings:

```bash
make test    # Still works, but shows deprecation warning
```

## Benefits of the Migration

### For Developers

- **Consistent Environment**: Same behavior across all platforms
- **Isolated Dependencies**: No conflicts between different tools
- **Better Error Messages**: Clear indication of what went wrong
- **Faster Iteration**: Reuse virtual environments for faster subsequent runs

### For CI/CD

- **Matrix Testing**: Easy testing across multiple Python versions
- **Reproducible Builds**: Identical behavior between local and CI
- **Better Caching**: Nox integrates well with CI caching systems

### For Contributors

- **Lower Barrier to Entry**: Works on any platform without additional setup
- **Self-Documenting**: `nox --list` shows all available tasks
- **Extensible**: Easy to add new development tasks

## Next Steps

1. **Install Nox**: `pip install nox`
2. **Try it out**: `nox --list` to see available sessions
3. **Run tests**: `nox -s tests` to verify everything works
4. **Update your workflow**: Replace Make commands with Nox equivalents
5. **Enjoy cross-platform development!** 🎉

For more information about Nox, visit the [official documentation](https://nox.thea.codes/).

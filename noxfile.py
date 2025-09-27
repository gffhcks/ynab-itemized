"""Nox configuration for cross-platform development tasks."""

import shutil
from pathlib import Path

import nox

# Python versions to test against
PYTHON_VERSIONS = ["3.9", "3.10", "3.11", "3.12"]

# Default sessions to run when just calling 'nox'
nox.options.sessions = ["tests", "lint", "type_check"]

# Reuse existing virtualenvs to speed up development
nox.options.reuse_existing_virtualenvs = True


@nox.session(python=PYTHON_VERSIONS)
def tests(session):
    """Run the test suite with coverage."""
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.install("-e", ".")

    # Run tests with coverage
    session.run(
        "pytest",
        "--cov=ynab_itemized",
        "--cov-report=term-missing",
        "--cov-report=html",
        *session.posargs,
    )


@nox.session
def lint(session):
    """Run linting checks."""
    session.install("flake8")
    session.run("flake8", "src/", "tests/")


@nox.session
def type_check(session):
    """Run type checking with mypy."""
    session.install(
        "mypy",
        "types-requests",
        "types-sqlalchemy",
        "types-pyyaml",
    )
    session.install("-e", ".")
    session.run("mypy", "src/")


@nox.session
def format(session):
    """Format code with black and isort."""
    session.install("black", "isort")
    session.run("black", "src/", "tests/")
    session.run("isort", "src/", "tests/")


@nox.session
def format_check(session):
    """Check code formatting without making changes."""
    session.install("black", "isort")
    session.run("black", "--check", "--diff", "src/", "tests/")
    session.run("isort", "--check-only", "--diff", "src/", "tests/")


@nox.session
def build(session):
    """Build the package."""
    session.install("build")

    # Clean previous builds
    clean_build_artifacts()

    # Build the package
    session.run("python", "-m", "build")


@nox.session
def install(session):
    """Install the package in development mode."""
    session.install("-e", ".")


@nox.session
def install_deps(session):
    """Install development dependencies."""
    session.install(
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "flake8",
        "mypy",
        "black",
        "isort",
        "build",
        "types-requests",
        "types-sqlalchemy",
        "types-pyyaml",
    )


@nox.session
def clean(session):
    """Clean build artifacts and cache files."""
    clean_build_artifacts()
    clean_cache_files()
    session.log("✅ Cleaned all build artifacts and cache files")


@nox.session
def init_db(session):
    """Initialize the database."""
    session.install("-e", ".")
    session.run("ynab-itemized", "init-db")


@nox.session
def dev_setup(session):
    """Set up development environment."""
    session.log("🔧 Setting up development environment...")

    # Install the package in development mode
    session.install("-e", ".")

    # Install development dependencies
    session.install(
        "pytest",
        "pytest-cov",
        "pytest-mock",
        "flake8",
        "mypy",
        "black",
        "isort",
        "build",
        "types-requests",
        "types-sqlalchemy",
        "types-pyyaml",
    )

    session.log("✅ Development environment ready!")
    session.log("💡 Run 'nox -s tests' to run tests")
    session.log("💡 Run 'nox -s lint' to check code style")
    session.log("💡 Run 'nox -s format' to format code")


@nox.session
def pre_commit(session):
    """Run all pre-commit checks."""
    session.log("🔍 Running pre-commit checks...")

    # Format check
    session.install("black", "isort")
    session.run("black", "--check", "src/", "tests/")
    session.run("isort", "--check-only", "src/", "tests/")

    # Linting
    session.install("flake8")
    session.run("flake8", "src/", "tests/")

    # Type checking
    session.install("mypy", "types-requests", "types-sqlalchemy", "types-pyyaml")
    session.install("-e", ".")
    session.run("mypy", "src/")

    # Tests
    session.install("pytest", "pytest-cov", "pytest-mock")
    session.run("pytest", "--cov=ynab_itemized")

    session.log("✅ All pre-commit checks passed!")


def clean_build_artifacts():
    """Remove build artifacts."""
    artifacts = [
        "build",
        "dist",
        "*.egg-info",
    ]

    for pattern in artifacts:
        if "*" in pattern:
            import glob

            for path in glob.glob(pattern):
                path_obj = Path(path)
                if path_obj.exists():
                    if path_obj.is_dir():
                        shutil.rmtree(path_obj)
                    else:
                        path_obj.unlink()
        else:
            path_obj = Path(pattern)
            if path_obj.exists():
                shutil.rmtree(path_obj)


def clean_cache_files():
    """Remove cache files and directories."""
    cache_patterns = [
        ".pytest_cache",
        ".mypy_cache",
        "htmlcov",
        ".coverage",
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
    ]

    for pattern in cache_patterns:
        if "**/" in pattern:
            # Recursive pattern
            for path in Path(".").rglob(pattern.replace("**/", "")):
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
        elif "*" in pattern:
            import glob

            for path_str in glob.glob(pattern):
                path = Path(path_str)
                if path.exists():
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
        else:
            path = Path(pattern)
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()


@nox.session
def docs(session):
    """Build documentation (placeholder for future)."""
    session.log("📚 Documentation building not yet implemented")
    session.log("💡 This is a placeholder for future documentation builds")


@nox.session
def release_check(session):
    """Check if the package is ready for release."""
    session.log("🚀 Checking release readiness...")

    # Run all quality checks
    session.install("black", "isort", "flake8", "mypy", "pytest", "pytest-cov", "build")
    session.install("types-requests", "types-sqlalchemy", "types-pyyaml")
    session.install("-e", ".")

    # Format check
    session.run("black", "--check", "src/", "tests/")
    session.run("isort", "--check-only", "src/", "tests/")

    # Linting
    session.run("flake8", "src/", "tests/")

    # Type checking
    session.run("mypy", "src/")

    # Tests with coverage
    session.run("pytest", "--cov=ynab_itemized", "--cov-fail-under=80")

    # Build check
    clean_build_artifacts()
    session.run("python", "-m", "build")

    session.log("✅ Package is ready for release!")

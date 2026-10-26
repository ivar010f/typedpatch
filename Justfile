# List available recipes.
default:
    @just --list

# Run the full local check.
build: deps lint test

# Install dependencies.
deps:
    uv sync --all-extras

# Upgrade locked dependencies and reinstall.
update-deps:
    uv lock --upgrade
    just deps

# Check lint, formatting and types.
lint:
    uv run ruff check
    uv run ruff format --check
    uv run pyrefly check
    uv run ty check

# Run unit tests and doctests.
test *args:
    uv run pytest {{ args }}

# Format source files.
format:
    uv run ruff format

# Apply safe lint fixes.
fix:
    uv run ruff check --fix

# Remove the virtual environment and caches.
clean:
    rm -rf .venv .pytest_cache .ruff_cache

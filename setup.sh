#!/bin/bash
set -e

# Install Poetry if not installed
if ! command -v poetry &> /dev/null; then
    echo "Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Install dependencies
echo "Installing project dependencies..."
poetry install

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
poetry run pre-commit install

# Create necessary directories
mkdir -p new_invoices

echo "Setup complete! You can now use the invoice converter."
echo ""
echo "Run tests with: poetry run pytest"
echo "Run pre-commit checks: poetry run pre-commit run --all-files"
echo "Run the converter: poetry run invoice-converter --existing <pdf> --new-dir new_invoices/ --output output.pdf"

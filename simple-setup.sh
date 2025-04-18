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

# Create necessary directories
mkdir -p new_invoices

echo "Setup complete! You can now use the invoice converter."
echo ""
echo "Run tests with: poetry run pytest"
echo "Run code formatting: poetry run black ."
echo "Run import sorting: poetry run isort ."
echo "Run linting: poetry run flake8"
echo "Run the converter: poetry run invoice-converter --existing <pdf> --new-dir new_invoices/ --output output.pdf"

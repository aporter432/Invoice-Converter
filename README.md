# Invoice Converter

A tool to update PDF invoice packages with new format invoices.

## Description

This utility helps when you have a PDF package of invoices and need to replace old format invoices with newer versions. It uses OCR to identify invoice numbers and formats, then creates a new PDF that:

1. Keeps invoices that are already in the new format
2. Replaces old format invoices with corresponding new versions
3. Adds any new invoices that weren't in the original package

## Requirements

- Python 3.13+
- Tesseract OCR must be installed on your system

## Quick Setup

Run one of the setup scripts to install all dependencies and configure the project:

```bash
# Standard setup (with pre-commit hooks)
./setup.sh

# OR Simple setup (without pre-commit hooks)
./simple-setup.sh
```

This will:
- Install Poetry (if not already installed)
- Install project dependencies
- Set up pre-commit hooks (standard setup only)
- Create the necessary directories

## Manual Installation

1. Install Tesseract OCR:
   - On macOS: `brew install tesseract`
   - On Ubuntu/Debian: `apt-get install tesseract-ocr`
   - On Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki

2. Install the package:
   ```
   # Install dependencies
   poetry install

   # Install pre-commit hooks (optional)
   poetry run pre-commit install
   ```

## Usage

### Command Line

```bash
poetry run invoice-converter --existing "PNW Open Invoices - unrevised 80.pdf" --new-dir "new_invoices/" --output "updated_package.pdf"
```

### As a Python Module

```python
from invoice_converter import update_pdf_package

update_pdf_package(
    existing_pdf="PNW Open Invoices - unrevised 80.pdf",
    new_invoices_dir="new_invoices/",
    output_pdf="updated_package.pdf"
)
```

## Development

### Running Tests

```bash
poetry run pytest
```

### Code Formatting and Linting

```bash
# If you installed pre-commit hooks:
poetry run pre-commit run --all-files

# Or run individual tools directly:
poetry run black .
poetry run isort .
poetry run flake8
```

### CI/CD Pipeline

This project has GitHub Actions workflows for:
- Running tests and linting on push and pull requests
- Building and publishing to PyPI on release

## License

MIT

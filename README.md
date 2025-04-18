# Invoice Converter

A tool for analyzing and converting PDF invoices based on template matching.

## Project Overview

Invoice Converter is a Python-based tool designed to identify PDF invoices that match a specific template format. The primary goals are:

1. Identify PDFs that match a template format
2. Extract structured data from fields in those PDFs
3. Compare invoice content against the template to determine similarity

## Installation

This project uses Poetry for dependency management:

```bash
# Install dependencies
poetry install

# Activate the virtual environment
poetry shell
```

## Usage

```bash
# Basic usage
poetry run invoice-converter /path/to/invoice.pdf

# With custom configuration
poetry run invoice-converter /path/to/invoice.pdf -c /path/to/config.toml

# Output to JSON file
poetry run invoice-converter /path/to/invoice.pdf -o results.json

# Verbose output
poetry run invoice-converter /path/to/invoice.pdf -v
```

## Template Fields

The system recognizes the following fields in the invoice template:

| Field Name      | Field Type | Description                           | Position (x1,y1,x2,y2)   |
|-----------------|------------|---------------------------------------|--------------------------|
| invoice_number  | text       | Unique invoice identifier             | (0.7, 0.1, 0.9, 0.15)    |
| date            | date       | Invoice issue date                    | (0.7, 0.15, 0.9, 0.2)    |
| customer_name   | text       | Name of the customer                  | (0.1, 0.2, 0.5, 0.25)    |
| total_amount    | amount     | Total invoice amount                  | (0.7, 0.8, 0.9, 0.85)    |

### Additional Invoice Template Elements

The template includes the following other elements:

- **Company Information**: Name, address, and contact details in the header
- **Bill To Section**: Customer billing information
- **Service Details**: Including customer ID, PO#, service period, and terms
- **Line Items**: Site name, item, quantity, rate, description, subtotal, and tax rate
- **Payment Information**: Total due amount and warranty information
- **Contact Information**: Phone numbers and email for service and billing inquiries

## Configuration

Configuration is stored in the `pyproject.toml` file under the `[tool.invoice_converter]` section:

- `template_path`: Path to the template PDF
- `fields`: List of field definitions with name, type, and region
- `confidence_threshold`: Minimum confidence level for field matching
- `use_fuzzy_matching`: Whether to use fuzzy text matching
- `threshold_for_fuzzy_match`: Minimum fuzzy match percentage

## Components

The system consists of several modules:

- **Field Recognition**: Extracts text from defined regions in the PDF
- **Layout Analysis**: Compares the structure of PDFs to the template
- **Text Recognition**: Extracts and processes text from PDFs
- **Structure Detection**: Identifies tables, lines, headers, and footers

## Field Identification Process

1. Template field locations are defined in the configuration
2. PDF text is extracted from these regions
3. Content is compared with the template using exact or fuzzy matching
4. Confidence scores determine if the document matches the expected format

## Development

```bash
# Run tests
poetry run pytest

# Run linting
poetry run black .
poetry run isort .
poetry run flake8 .
poetry run mypy .

# Install pre-commit hooks
pre-commit install
```

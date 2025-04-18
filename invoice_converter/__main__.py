#!/usr/bin/env python3
"""
Invoice Converter Main Module.

This is the main entry point for the invoice converter tool.
"""

import argparse
import json
import logging
import os
from typing import Any, Dict, Optional

# Import tomli for TOML parsing
try:
    import tomli
except ImportError:
    # Python 3.11+ has tomllib built-in
    import tomllib as tomli  # type: ignore

from invoice_converter.field_extraction import FieldExtractor
from invoice_converter.models import ExtractedData, InvoiceFieldData, LineItem
from invoice_converter.pdf_manipulation import PDFManipulator

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("invoice-converter")


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a TOML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, "rb") as f:
            config: Dict[str, Any] = tomli.load(f)
            return config
    except Exception as e:
        logger.error(f"Error loading configuration from {config_path}: {e}")
        return {}


def analyze_invoice(pdf_path: str, config: Optional[Dict[str, Any]] = None) -> ExtractedData:
    """
    Analyze an invoice to extract its data structure.

    Args:
        pdf_path: Path to the invoice PDF
        config: Optional configuration dictionary

    Returns:
        ExtractedData model containing analysis results
    """
    logger.info(f"Analyzing invoice: {pdf_path}")

    # Create a basic result dictionary for initial extraction
    metadata = {
        "filename": os.path.basename(pdf_path),
        "filepath": pdf_path,
    }

    try:
        # Create extractor with config
        extractor = FieldExtractor(config)

        # Extract fields and line items
        field_dict = extractor.extract_all_fields(pdf_path)
        line_item_dicts = extractor.extract_table(pdf_path)

        # Convert to Pydantic models
        fields = InvoiceFieldData.model_validate(field_dict)
        line_items = [LineItem.model_validate(item) for item in line_item_dicts]

        # Add extraction timestamp
        from datetime import datetime

        metadata["extraction_time"] = datetime.now().isoformat()

        # Create the final ExtractedData model
        result = ExtractedData(fields=fields, line_items=line_items)

        # Add metadata to fields
        for key, value in metadata.items():
            result.fields.additional_fields[key] = value

        logger.info(f"Extracted {len(field_dict)} fields and {len(line_items)} line items")

        return result
    except Exception as e:
        logger.error(f"Error analyzing invoice: {e}")
        # Return an empty model if extraction fails
        return ExtractedData(fields=InvoiceFieldData(additional_fields=metadata), line_items=[])


def convert_invoice(
    source_path: str, template_path: str, output_path: str, config: Optional[Dict[str, Any]] = None
) -> str:
    """
    Convert an invoice from source format to template format.

    Args:
        source_path: Path to the source invoice PDF
        template_path: Path to the template PDF
        output_path: Path where the converted invoice should be saved
        config: Optional configuration dictionary

    Returns:
        Path to the converted invoice
    """
    logger.info(f"Converting invoice: {source_path}")
    logger.info(f"Using template: {template_path}")
    logger.info(f"Output path: {output_path}")

    try:
        # First analyze the source invoice
        extracted_data = analyze_invoice(source_path, config)

        # Create PDF manipulator with template and config
        manipulator = PDFManipulator(template_path, config)

        # Convert the invoice
        result_path = manipulator.convert_invoice(source_path, output_path, extracted_data=extracted_data)

        logger.info(f"Successfully converted invoice to: {result_path}")
        return result_path
    except Exception as e:
        logger.error(f"Error converting invoice: {e}")
        # Return source path to indicate conversion failed
        return source_path


def process_batch(
    input_dir: str, template_path: str, output_dir: str, config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a batch of invoices in a directory.

    Args:
        input_dir: Directory containing source invoice PDFs
        template_path: Path to the template PDF
        output_dir: Directory where converted invoices should be saved
        config: Optional configuration dictionary

    Returns:
        Dictionary with processing statistics and results
    """
    logger.info(f"Processing batch of invoices from: {input_dir}")
    logger.info(f"Using template: {template_path}")
    logger.info(f"Output directory: {output_dir}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get list of PDF files in input directory
    input_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

    if not input_files:
        logger.warning(f"No PDF files found in {input_dir}")
        return {"total": 0, "success": 0, "failed": 0, "files": []}

    # Process each file
    results: Dict[str, Any] = {"total": len(input_files), "success": 0, "failed": 0, "files": []}

    for filename in input_files:
        source_path = os.path.join(input_dir, filename)
        output_path = os.path.join(output_dir, filename)

        try:
            # Extract data using Pydantic models
            extracted_data = analyze_invoice(source_path, config)

            # Convert the invoice
            result_path = convert_invoice(source_path, template_path, output_path, config)

            # Check if conversion was successful
            if result_path == output_path:
                results["success"] += 1
                status = "success"
            else:
                results["failed"] += 1
                status = "failed"

            results["files"].append(
                {
                    "filename": filename,
                    "status": status,
                    "source_path": source_path,
                    "output_path": result_path,
                    "field_count": len(extracted_data.fields.model_dump(exclude_none=True, exclude_unset=True)),
                }
            )

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            results["failed"] += 1
            results["files"].append(
                {"filename": filename, "status": "error", "source_path": source_path, "error": str(e)}
            )

    # Log summary
    logger.info(f"Batch processing complete: {results['success']} succeeded, {results['failed']} failed")

    return results


def main() -> None:
    """
    Execute the main command-line interface.

    This function is the entry point for the invoice converter tool.
    """
    parser = argparse.ArgumentParser(description="Convert invoice PDFs to a template format")

    # Command subparsers
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert a single invoice")
    convert_parser.add_argument("source", help="Path to the source invoice PDF")
    convert_parser.add_argument(
        "-t", "--template", default="template.pdf", help="Path to the template PDF (default: template.pdf)"
    )
    convert_parser.add_argument(
        "-o", "--output", help="Path where the converted invoice should be saved (default: source_converted.pdf)"
    )
    convert_parser.add_argument(
        "-c",
        "--config",
        default="invoice_template.toml",
        help="Path to the configuration file (default: invoice_template.toml)",
    )

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze an invoice without converting")
    analyze_parser.add_argument("source", help="Path to the invoice PDF to analyze")
    analyze_parser.add_argument(
        "-c",
        "--config",
        default="invoice_template.toml",
        help="Path to the configuration file (default: invoice_template.toml)",
    )
    analyze_parser.add_argument(
        "-o", "--output", help="Path where analysis results should be saved as JSON (default: source_analysis.json)"
    )

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Process a batch of invoices")
    batch_parser.add_argument("input_dir", help="Directory containing source invoice PDFs")
    batch_parser.add_argument(
        "-t", "--template", default="template.pdf", help="Path to the template PDF (default: template.pdf)"
    )
    batch_parser.add_argument(
        "-o",
        "--output_dir",
        default="converted",
        help="Directory where converted invoices should be saved (default: 'converted')",
    )
    batch_parser.add_argument(
        "-c",
        "--config",
        default="invoice_template.toml",
        help="Path to the configuration file (default: invoice_template.toml)",
    )
    batch_parser.add_argument("-r", "--report", help="Path where batch processing report should be saved as JSON")

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return

    # Load configuration
    config = {}
    if hasattr(args, "config") and os.path.exists(args.config):
        config = load_config(args.config)
        logger.info(f"Loaded configuration from {args.config}")

    # Execute command
    if args.command == "convert":
        # Determine output path
        if not args.output:
            source_name = os.path.basename(args.source)
            source_dir = os.path.dirname(args.source)
            source_base = os.path.splitext(source_name)[0]
            args.output = os.path.join(source_dir, f"{source_base}_converted.pdf")

        # Convert invoice
        convert_invoice(args.source, args.template, args.output, config)

    elif args.command == "analyze":
        # Analyze invoice
        extracted_data: ExtractedData = analyze_invoice(args.source, config)

        # Determine output path for analysis results
        if not args.output:
            source_name = os.path.basename(args.source)
            source_dir = os.path.dirname(args.source)
            source_base = os.path.splitext(source_name)[0]
            args.output = os.path.join(source_dir, f"{source_base}_analysis.json")

        # Save analysis results
        with open(args.output, "w") as f:
            # Convert Pydantic model to JSON serializable dict
            results_dict = extracted_data.model_dump()
            json.dump(results_dict, f, indent=2)

        logger.info(f"Saved analysis results to {args.output}")

    elif args.command == "batch":
        # Process batch of invoices
        batch_results: Dict[str, Any] = process_batch(args.input_dir, args.template, args.output_dir, config)

        # Save batch processing report if requested
        if args.report:
            with open(args.report, "w") as f:
                # Batch results are already a dictionary
                json.dump(batch_results, f, indent=2)

            logger.info(f"Saved batch processing report to {args.report}")


if __name__ == "__main__":
    main()

"""Invoice Converter package for template matching and field recognition in PDF invoices."""

__version__ = "0.1.0"

import argparse
import json
import sys
from typing import Any, Dict, Optional

from invoice_converter.field_recognition import recognize_fields
from invoice_converter.layout_analysis import analyze_layout
from invoice_converter.structure_detection import detect_structure


def analyze_invoice(pdf_path: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyze an invoice PDF and extract information based on template configuration.

    Args:
        pdf_path: Path to the PDF file to analyze.
        config_path: Optional path to configuration file.

    Returns:
        Dict containing analysis results including fields, layout, and structure.
    """
    # Extract fields
    fields = recognize_fields(pdf_path, config_path)

    # Analyze layout
    layout = analyze_layout(pdf_path, config_path)

    # Detect structure
    structure = detect_structure(pdf_path)

    # Combine results
    results = {
        "pdf_path": pdf_path,
        "fields": fields["fields"],
        "layout_similarity": layout["layout_similarity"],
        "is_similar_layout": layout["is_similar_layout"],
        "field_similarity": layout["field_similarity"],
        "is_similar_content": layout["is_similar_content"],
        "structure": {
            "tables": len(structure["tables"]),
            "lines": len(structure["lines"]),
            "header": structure["header"]["text"],
            "footer": structure["footer"]["text"],
            "fingerprint": structure["structural_fingerprint"],
        },
    }

    return results


def main() -> int:
    """Command-line interface for the invoice converter.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(description="Invoice Converter")
    parser.add_argument("pdf_path", help="Path to the PDF file to analyze")
    parser.add_argument("-c", "--config", help="Path to configuration file")
    parser.add_argument("-o", "--output", help="Output file path for results (JSON)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")

    args = parser.parse_args()

    try:
        # Analyze the invoice
        results = analyze_invoice(args.pdf_path, args.config)

        # Format results as JSON
        json_results = json.dumps(results, indent=2)

        # Output results
        if args.output:
            with open(args.output, "w") as f:
                f.write(json_results)

            if args.verbose:
                print(f"Results written to {args.output}")
        else:
            print(json_results)

        # Return success
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

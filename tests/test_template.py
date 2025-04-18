#!/usr/bin/env python3
"""Test script to analyze the template PDF."""

import json
import sys
from pathlib import Path

from invoice_converter import analyze_invoice


def main() -> int:
    """Analyze the template PDF and print the results.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    # Get the path to the template PDF
    template_path = Path("template.pdf").absolute()

    if not template_path.exists():
        print(f"Error: Template file not found: {template_path}")
        return 1

    print(f"Analyzing template: {template_path}")

    try:
        # Analyze the template
        results = analyze_invoice(str(template_path))

        # Print results
        print(json.dumps(results, indent=2))

        print("\nSuccessfully analyzed template!")
        return 0

    except Exception as e:
        print(f"Error analyzing template: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

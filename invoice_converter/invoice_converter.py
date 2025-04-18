"""Check if PDF pages match a template structure."""

import argparse
import logging

from field_recognition import DEFAULT_MARKERS
from template_comparison import check_pdf_against_template

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Process PDF and check against template."""
    parser = argparse.ArgumentParser(description="Check if PDF pages match a template structure")
    parser.add_argument(
        "--input",
        default="/Users/aaronporter/Desktop/R6 invoices/PNW Open Invoices - unrevised.pdf",
        help="Input PDF file path",
    )
    parser.add_argument(
        "--template",
        default="/Users/aaronporter/Projects/Invoice Converter/template.pdf",
        help="Template PDF file path",
    )
    parser.add_argument(
        "--save-snippets",
        action="store_true",
        help="Save text snippets from each page for analysis",
    )
    parser.add_argument(
        "--marker",
        action="append",
        dest="markers",
        help="Add a custom marker to search for (can be specified multiple times)",
    )
    parser.add_argument(
        "--required-marker",
        action="append",
        dest="required_markers",
        help="Add a marker that MUST be present for a match (can be specified multiple times)",
    )
    parser.add_argument(
        "--structure-only",
        action="store_true",
        help="Only use structural markers for matching (ignore content markers)",
    )
    parser.add_argument(
        "--layout-only",
        action="store_true",
        help="Only use layout-based detection (ignore content and structural markers)",
    )
    parser.add_argument(
        "--layout-weight",
        type=float,
        default=0.6,
        help="Weight for layout-based score in combined scoring (default: 0.6)",
    )
    parser.add_argument(
        "--calibrate-layout",
        action="store_true",
        help="Calibrate layout landmarks based on template",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable more verbose debugging output",
    )

    args = parser.parse_args()

    # Set log level based on debug flag
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting PDF template matching check")
    logger.info(f"Input PDF: {args.input}")
    logger.info(f"Template PDF: {args.template}")
    logger.info(f"Save snippets: {args.save_snippets}")
    logger.info(f"Structure only: {args.structure_only}")
    logger.info(f"Layout only: {args.layout_only}")
    logger.info(f"Layout weight: {args.layout_weight}")
    logger.info(f"Calibrate layout: {args.calibrate_layout}")

    # Use custom markers if provided, otherwise use defaults
    markers = args.markers if args.markers else DEFAULT_MARKERS
    required_markers = args.required_markers if args.required_markers else ["Site Name #"]

    # If structure-only is set, ignore content markers
    if args.structure_only:
        markers = []
        required_markers = []

    # If layout-only is set, we will ignore text-based markers
    if args.layout_only:
        logger.info("Using layout-only detection mode")

    try:
        # Run the check
        check_pdf_against_template(
            args.input,
            args.template,
            args.save_snippets,
            markers,
            required_markers,
            args.layout_only,
            args.layout_weight,
        )
        logger.info("Template matching check completed")
    except Exception as e:
        logger.error(f"Error during template matching: {e}")
        raise


if __name__ == "__main__":
    main()

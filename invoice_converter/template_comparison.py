"""Module for loading templates and comparing PDF documents against them."""

import logging
import os
from collections import defaultdict
from typing import Any, Dict, List

import pdfplumber
from pdfrw import PdfReader

from field_recognition import DEFAULT_MARKERS, STRUCTURAL_MARKERS, is_new_format
from layout_analysis import calibrate_landmarks, compare_layout, extract_layout_info, save_layout_info
from text_recognition import extract_text_from_page, save_page_snippet

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Global variables
TEMPLATE_TEXT = ""
TEMPLATE_LAYOUT = {}
LAYOUT_WEIGHT = 0.6  # Default weight for layout in combined scoring


def load_template(template_path: str, calibrate: bool = False) -> None:
    """Load the template PDF and extract its text for comparison.

    Args:
        template_path: Path to the template PDF
        calibrate: Whether to calibrate positional landmarks from the template
    """
    global TEMPLATE_TEXT, TEMPLATE_LAYOUT

    if not os.path.exists(template_path):
        logger.error(f"Template file does not exist: {template_path}")
        raise FileNotFoundError(f"Template not found: {template_path}")

    logger.info(f"Loading template from: {template_path}")

    # Extract text and layout from template
    with pdfplumber.open(template_path) as pdf:
        # Extract text
        template_pages = [page.extract_text() or "" for page in pdf.pages]
        TEMPLATE_TEXT = " ".join(template_pages)

        # Extract layout information from the first page
        if pdf.pages:
            TEMPLATE_LAYOUT = extract_layout_info(pdf.pages[0])
            logger.info(f"Template layout extracted with {len(TEMPLATE_LAYOUT['landmarks'])} landmarks")

            # Log landmark positions
            for landmark, pos in TEMPLATE_LAYOUT.get("landmarks", {}).items():
                logger.info(f"Template landmark: {landmark} at x={pos['x']:.1f}, y={pos['y']:.1f}")

            # Calibrate positional landmarks if requested
            if calibrate:
                calibrate_landmarks(TEMPLATE_LAYOUT)

    logger.info(f"Template loaded with {len(TEMPLATE_TEXT)} characters")

    # Print a snippet of the template
    snippet = TEMPLATE_TEXT[:200].replace("\n", " ")
    logger.info(f"Template text snippet: {snippet}...")


def print_marker_statistics(match_details: List[Dict[str, Any]], total_pages: int, layout_only: bool = False) -> None:
    """Print statistics about marker frequency across all pages.

    Args:
        match_details: List of dictionaries containing match details for each page
        total_pages: Total number of pages processed
        layout_only: Whether only layout-based detection was used
    """
    # Only show content and structural marker stats if not in layout-only mode
    if not layout_only:
        # Get all markers from the first page that has markers
        content_markers = set()
        for detail in match_details:
            if "markers" in detail:
                for marker in detail["markers"]:
                    if not marker.startswith("STRUCT_") and marker != "structural_score":
                        content_markers.add(marker)

        # Print a more detailed summary of which markers were most commonly found/missing
        # Process content markers
        logger.info("Content marker frequency across all pages:")
        marker_totals = {marker: 0 for marker in content_markers}
        for detail in match_details:
            for marker, found in detail.get("markers", {}).items():
                if marker in marker_totals and found and isinstance(found, bool):
                    marker_totals[marker] += 1

        for marker, count in marker_totals.items():
            logger.info(f"  - {marker}: {count}/{total_pages} pages ({(count/total_pages)*100:.1f}%)")

        # Process structural markers
        logger.info("Structural marker frequency across all pages:")
        struct_markers = {m["name"]: 0 for m in STRUCTURAL_MARKERS}
        for detail in match_details:
            for marker, found in detail.get("markers", {}).items():
                if marker.startswith("STRUCT_"):
                    key = marker.replace("STRUCT_", "")
                    if key in struct_markers and found and isinstance(found, bool):
                        struct_markers[key] += 1

        for marker_name, count in struct_markers.items():
            # Get the marker weight for reporting
            marker_weight = next((m["weight"] for m in STRUCTURAL_MARKERS if m["name"] == marker_name), 1.0)
            logger.info(
                f"  - {marker_name} (weight: {marker_weight:.1f}): {count}/{total_pages} pages "
                f"({(count/total_pages)*100:.1f}%)"
            )

    # Process layout markers - always show these
    logger.info("Layout marker frequency across all pages:")
    layout_markers: Dict[str, int] = defaultdict(int)
    for detail in match_details:
        for marker, found in detail.get("layout_details", {}).items():
            if found:
                layout_markers[marker] += 1

    for marker_name, count in layout_markers.items():
        logger.info(f"  - {marker_name}: {count}/{total_pages} pages ({(count/total_pages)*100:.1f}%)")


def check_pdf_against_template(
    input_pdf: str,
    template_pdf: str,
    save_snippets: bool = False,
    markers: List[str] | None = None,
    required_markers: List[str] | None = None,
    layout_only: bool = False,
    layout_weight: float = 0.6,
) -> None:
    """Check each page of the input PDF against the template.

    Args:
        input_pdf: Path to the PDF to check
        template_pdf: Path to the template PDF
        save_snippets: Whether to save text snippets for analysis
        markers: List of markers to search for (defaults to DEFAULT_MARKERS)
        required_markers: List of markers that MUST be present (default: ["Site Name #"])
        layout_only: Whether to use only layout-based detection
        layout_weight: Weight for layout-based score in combined scoring (default: 0.6)
    """
    # Set default markers if none provided
    if markers is None:
        markers = DEFAULT_MARKERS

    # Default required markers if none provided
    if required_markers is None:
        required_markers = ["Site Name #"]

    logger.info(f"Using {len(markers)} content markers for template matching")
    logger.info(f"Required content markers: {', '.join(required_markers)}")
    logger.info("Using positional landmarks for layout analysis")
    logger.info(f"Layout weight in combined scoring: {layout_weight}")

    if layout_only:
        logger.info("LAYOUT-ONLY MODE: Text and structural markers will be ignored")

    # Load the template
    load_template(template_pdf)

    # Check if input PDF exists
    if not os.path.exists(input_pdf):
        logger.error(f"Input PDF file does not exist: {input_pdf}")
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")

    logger.info(f"Processing input PDF: {input_pdf}")

    # Create a directory for snippets if saving them
    snippets_dir = None
    if save_snippets:
        base_dir = os.path.dirname(input_pdf)
        base_name = os.path.splitext(os.path.basename(input_pdf))[0]
        snippets_dir = os.path.join(base_dir, f"{base_name}_snippets")
        os.makedirs(snippets_dir, exist_ok=True)
        logger.info(f"Will save page snippets to {snippets_dir}")

    # Get the page count first
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    logger.info(f"Input PDF has {total_pages} pages")

    # Open with pdfplumber to extract text
    with pdfplumber.open(input_pdf) as pdf:
        match_count = 0
        match_details = []
        avg_score = 0.0
        min_score = 1.0
        max_score = 0.0
        avg_layout_score = 0.0

        for i, page in enumerate(pdf.pages):
            page_num = i + 1
            logger.info(f"Processing page {page_num}/{total_pages}")

            # Extract text from the page
            text = extract_text_from_page(page)
            logger.info(f"Page {page_num}: Extracted {len(text)} characters")

            # Extract layout information
            layout_info = extract_layout_info(page)
            logger.info(f"Page {page_num}: Extracted layout with {len(layout_info['landmarks'])} landmarks")

            # Compare layout to template
            layout_score, layout_details = compare_layout(TEMPLATE_LAYOUT, layout_info)
            logger.info(f"Page {page_num}: Layout similarity score: {layout_score*100:.1f}%")

            # In layout-only mode, we skip the text-based marker checks
            if layout_only:
                structural_score = 0.0
                matches_template = False
                marker_details: Dict[str, Any] = {"structural_score": 0.0}
            else:
                # Check if this page matches the template using text-based markers
                matches_template, marker_details = is_new_format(text, markers, required_markers)
                # Get the structural score
                structural_score = marker_details.get("structural_score", 0.0)

            # Combine structural and layout scores (using configurable weight)
            combined_score = (structural_score * (1 - layout_weight)) + (layout_score * layout_weight)

            # Determine match based on mode
            if layout_only:
                # In layout-only mode, match is based solely on layout score
                combined_match = layout_score >= 0.8
            else:
                # In normal mode, combine both scores
                layout_match = layout_score >= 0.8
                combined_match = (layout_match and structural_score >= 0.6) or matches_template

            # Store detailed results
            match_details.append(
                {
                    "page": page_num,
                    "matches": combined_match,
                    "markers": marker_details,
                    "struct_score": structural_score,
                    "layout_score": layout_score,
                    "combined_score": combined_score,
                    "layout_details": layout_details,
                }
            )

            # Track min/max/avg scores for reporting
            if combined_match:
                avg_score += structural_score
                avg_layout_score += layout_score
                min_score = min(min_score, structural_score)
                max_score = max(max_score, structural_score)
                match_count += 1

            # Format the log message based on the mode
            if layout_only:
                logger.info(
                    f"Page {page_num}: {'MATCHES' if combined_match else 'DOES NOT MATCH'} template "
                    f"(layout score: {layout_score*100:.1f}%)"
                )
            else:
                logger.info(
                    f"Page {page_num}: {'MATCHES' if combined_match else 'DOES NOT MATCH'} template "
                    f"(struct: {structural_score*100:.1f}%, layout: {layout_score*100:.1f}%, "
                    f"combined: {combined_score*100:.1f}%)"
                )

            # Save a snippet of the page text if requested
            if save_snippets and snippets_dir:
                save_page_snippet(page_num, text, combined_match, snippets_dir)
                # Also save layout info
                save_layout_info(page_num, layout_info, snippets_dir)

    # Calculate average scores
    avg_score = avg_score / match_count if match_count > 0 else 0
    avg_layout_score = avg_layout_score / match_count if match_count > 0 else 0

    # Summary
    logger.info(f"Summary: {match_count}/{total_pages} pages match the template format")
    logger.info(f"Percentage: {(match_count/total_pages)*100:.1f}%")

    if match_count > 0:
        if layout_only:
            logger.info("Matching pages score statistics:")
            logger.info(f"  - Avg Layout: {avg_layout_score*100:.1f}%")
        else:
            logger.info("Matching pages score statistics:")
            logger.info(f"  - Avg Structural: {avg_score*100:.1f}%")
            logger.info(f"  - Avg Layout: {avg_layout_score*100:.1f}%")
            logger.info(f"  - Min Structural: {min_score*100:.1f}%")
            logger.info(f"  - Max Structural: {max_score*100:.1f}%")

    # Calculate and print marker frequency statistics
    print_marker_statistics(match_details, total_pages, layout_only)

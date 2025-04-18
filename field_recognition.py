"""Module for identifying and processing fields and markers in PDF documents."""

import logging
import re
from typing import Any, Dict, List, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Default markers for content identification
DEFAULT_MARKERS = [
    "Site Name #",
    "Service Invoice",
    "American Millennium Corporation",
    "Total Due in US Dollars",
    "Amount Due",
    "Service Period",
]

# Structural markers that identify layout/format rather than content
STRUCTURAL_MARKERS = [
    # Exact header format with precise spacing for new invoice template
    {"pattern": r"American Millennium Corporation, Inc\s+Service Invoice", "name": "Header Format", "weight": 1.0},
    # Site Name Column is a distinctive feature of the new format - critical marker
    {
        "pattern": r"Site Name #\s+Item\s+Qty\s+Rate\s+Description\s+Subtotal\s+Tax Rate",
        "name": "New Format Column Headers",
        "weight": 2.0,
    },
    # Precise format of the Customer ID line
    {"pattern": r"Customer ID\s+PO#\s+Service Period\s+Terms", "name": "Header Row Format", "weight": 1.0},
    # Bill To format without Ship To (single address block)
    {"pattern": r"Bill To\s+(?!Ship To).{10,200}Customer ID", "name": "Single Address Block", "weight": 1.5},
    # Check for absence of AMCi Serial # which indicates new format
    {"pattern": r"AMCi Serial #", "name": "Old Serial Number Field", "negate": True, "weight": 1.0},
    # New format often has this total format
    {
        "pattern": r"Subtotal\s+[\d,.]+\s+Tax\s+[\d,.]+\s+Total Due in US Dollars\s+[\d,.]+",
        "name": "New Format Totals",
        "weight": 1.0,
    },
    # Check coordinates - new format has site name in specific position (would show up as beginning of line)
    {"pattern": r"^.{0,10}Site Name #", "name": "Site Name Left Position", "weight": 1.5, "multiline": True},
    # Absence of certain column headers that would be in old format
    {"pattern": r"\bSite Address\b", "name": "Old Site Address Column", "negate": True, "weight": 0.5},
    # Check for new format invoice date pattern at specific position
    {"pattern": r"Date\s+Invoice #\s*\n\d{1,2}/\d{1,2}/\d{4}\s+\d{7}", "name": "Date Invoice Format", "weight": 1.0},
]


def check_structural_markers(text: str) -> Tuple[bool, Dict[str, bool], float]:
    """Check if a page matches the structural template format.

    Args:
        text: Text content of the page

    Returns:
        Tuple of (match_result, detailed_markers, score)
        match_result: True if page matches template format, False otherwise
        detailed_markers: Dictionary of marker names and whether they were found
        score: Weighted score indicating confidence in the match
    """
    # Create a dictionary to track which markers are found
    marker_results: Dict[str, bool] = {}
    total_weight = 0
    weighted_score = 0

    for marker in STRUCTURAL_MARKERS:
        pattern = marker["pattern"]
        name = marker["name"]
        negate = marker.get("negate", False)
        weight = marker.get("weight", 1.0)
        multiline = marker.get("multiline", False)

        # Check if pattern exists in text
        flags = re.MULTILINE if multiline else 0
        match_found = bool(re.search(pattern, text, flags))

        # If negate is True, we want the pattern NOT to be found
        if negate:
            result = not match_found
        else:
            result = match_found

        marker_results[name] = result
        total_weight += weight

        # Add to weighted score if marker was found
        if result:
            weighted_score += weight

    # Calculate relative weighted score (0.0 to 1.0)
    relative_score = weighted_score / total_weight if total_weight > 0 else 0

    # For a match:
    # 1. Relative score must be at least 0.8 (80%)
    # 2. Critical markers must be present - "New Format Column Headers" is critical
    critical_marker = marker_results.get("New Format Column Headers", False)
    is_match = relative_score >= 0.8 and critical_marker

    # Log the detailed results
    logger.info(f"Structural format check result: {'MATCH' if is_match else 'NO MATCH'}")
    logger.info(f"Structural weighted score: {weighted_score:.1f}/{total_weight:.1f} ({relative_score*100:.1f}%)")

    for name, found in marker_results.items():
        marker_weight = next((m["weight"] for m in STRUCTURAL_MARKERS if m["name"] == name), 1.0)
        logger.info(f"  - {name} (weight: {marker_weight:.1f}): {'✓' if found else '✗'}")

    return is_match, marker_results, relative_score


def check_content_markers(
    text: str, markers: List[str], required_markers: List[str] | None = None
) -> Tuple[bool, Dict[str, bool]]:
    """Check if a page contains specified content markers.

    Args:
        text: Text content of the page
        markers: List of markers to search for
        required_markers: List of markers that MUST be present (default: ["Site Name #"])

    Returns:
        Tuple of (match_result, detailed_markers)
        match_result: True if page has required content markers, False otherwise
        detailed_markers: Dictionary of marker names and whether they were found
    """
    # If no required markers specified, default to Site Name #
    if required_markers is None:
        required_markers = ["Site Name #"]

    # Create a dictionary to track which markers are found
    marker_results: Dict[str, bool] = {marker: marker in text for marker in markers}

    # Count how many markers were found
    markers_found = sum(marker_results.values())
    total_markers = len(markers)

    # For a match:
    # 1. At least 60% of markers must be found
    # 2. All required markers must be found
    required_markers_found = all(marker_results.get(marker, False) for marker in required_markers)
    content_match = markers_found >= total_markers * 0.6 and required_markers_found

    # Log the detailed results
    logger.info(f"Content marker check result: {'MATCH' if content_match else 'NO MATCH'}")
    logger.info(f"Content markers found: {markers_found}/{total_markers}")

    # Log required markers separately
    if required_markers:
        logger.info("Required content markers:")
        for marker in required_markers:
            logger.info(f"  - {marker}: {'✓' if marker_results.get(marker, False) else '✗'}")

    # Log all markers
    logger.info("All content markers:")
    for marker, found in marker_results.items():
        if marker not in required_markers:
            logger.info(f"  - {marker}: {'✓' if found else '✗'}")

    return content_match, marker_results


def is_new_format(
    text: str, markers: List[str], required_markers: List[str] | None = None
) -> Tuple[bool, Dict[str, Any]]:
    """Check if a page matches the template format by combining structural and content checks.

    Args:
        text: Text content of the page
        markers: List of markers to search for
        required_markers: List of markers that MUST be present (default: ["Site Name #"])

    Returns:
        Tuple of (match_result, detailed_markers)
        match_result: True if page matches template format, False otherwise
        detailed_markers: Dictionary of marker names and whether they were found
    """
    # Check content markers
    content_match, content_results = check_content_markers(text, markers, required_markers)

    # Check structural markers
    struct_match, struct_results, struct_score = check_structural_markers(text)

    # Combined result - both content and structure should match
    # But we prioritize the structural match which is more precise
    combined_match = struct_match
    logger.info(f"COMBINED format check result: {'MATCH' if combined_match else 'NO MATCH'}")
    logger.info(f"Using structural match as primary indicator (score: {struct_score*100:.1f}%)")

    # Merge the results
    all_results: Dict[str, Any] = {**content_results, **{f"STRUCT_{k}": v for k, v in struct_results.items()}}
    all_results["structural_score"] = struct_score

    return combined_match, all_results

"""Module for analyzing and comparing layout information from PDF documents."""

import json
import logging
import os
from collections import defaultdict
from typing import Any, Dict, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Define positional markers for layout comparisons
POSITIONAL_LANDMARKS = {
    "Site Name #": {"x_range": (0, 100), "y_range": (300, 400), "weight": 2.0},
    "Bill To": {"x_range": (0, 100), "y_range": (150, 250), "weight": 1.5},
    "Customer ID": {"x_range": (0, 100), "y_range": (250, 350), "weight": 1.0},
    "Date": {"x_range": (300, 400), "y_range": (100, 200), "weight": 1.0},
    "Invoice #": {"x_range": (400, 500), "y_range": (100, 200), "weight": 1.0},
}


def extract_layout_info(page: Any) -> Dict[str, Any]:
    """Extract detailed layout information from a PDF page.

    Args:
        page: pdfplumber page object

    Returns:
        Dictionary containing layout information
    """
    layout_info: Dict[str, Any] = {
        "words": [],
        "lines": [],
        "tables": [],
        "text_blocks": defaultdict(list),
        "landmarks": {},
    }

    # Extract words with positions
    words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)
    layout_info["words"] = words

    # Extract lines
    layout_info["lines"] = page.lines

    # Try to extract tables
    try:
        tables = page.extract_tables()
        if tables:
            layout_info["tables"] = [
                {"rows": len(table), "cols": len(table[0]) if table and table[0] else 0, "content": table}
                for table in tables
            ]
    except Exception as e:
        logger.warning(f"Could not extract tables: {e}")

    # Group words by their y-position to identify text blocks
    for word in words:
        y_pos = int(word["top"])
        layout_info["text_blocks"][y_pos].append(word)

    # Convert defaultdict to regular dict for serialization
    layout_info["text_blocks"] = dict(layout_info["text_blocks"])

    # Find landmark positions
    for landmark, _ in POSITIONAL_LANDMARKS.items():
        for word in words:
            if landmark.lower() in word["text"].lower():
                layout_info["landmarks"][landmark] = {"x": word["x0"], "y": word["top"], "text": word["text"]}
                break

    return layout_info


def save_layout_info(page_num: int, layout_info: Dict[str, Any], output_dir: str) -> None:
    """Save layout information to a file for analysis.

    Args:
        page_num: Page number
        layout_info: Layout information dictionary
        output_dir: Directory to save layout info to
    """
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Define the layout file name
    layout_file = os.path.join(output_dir, f"page_{page_num:03d}_layout.json")

    # Convert defaultdict to dict for JSON serialization
    serializable_info = {
        "landmarks": layout_info["landmarks"],
        "text_blocks_count": len(layout_info["text_blocks"]),
        "words_count": len(layout_info["words"]),
        "tables_count": len(layout_info["tables"]),
    }

    # Save basic layout info (not the full structure which can be large)
    with open(layout_file, "w") as f:
        json.dump(serializable_info, f, indent=2)

    logger.info(f"Saved basic layout info to {layout_file}")


def compare_layout(template_layout: Dict[str, Any], page_layout: Dict[str, Any]) -> Tuple[float, Dict[str, bool]]:
    """Compare page layout to template layout to determine similarity.

    Args:
        template_layout: Layout information of the template
        page_layout: Layout information of the page to compare

    Returns:
        Tuple of (similarity_score, detailed_results)
        similarity_score: 0.0 to 1.0 score of layout similarity
        detailed_results: Dictionary of landmark names and whether they match
    """
    if not template_layout or not page_layout:
        return 0.0, {}

    results = {}
    total_weight = 0
    weighted_score = 0

    # Compare landmark positions
    template_landmarks = template_layout.get("landmarks", {})
    page_landmarks = page_layout.get("landmarks", {})

    for landmark, config in POSITIONAL_LANDMARKS.items():
        weight = config["weight"]
        total_weight += weight

        # Check if landmark exists in both layouts
        if landmark in template_landmarks and landmark in page_landmarks:
            template_pos = template_landmarks[landmark]
            page_pos = page_landmarks[landmark]

            # Calculate position difference
            x_diff = abs(template_pos["x"] - page_pos["x"])
            y_diff = abs(template_pos["y"] - page_pos["y"])

            # Define tolerance based on the configuration
            x_tolerance = abs(config["x_range"][1] - config["x_range"][0]) / 4
            y_tolerance = abs(config["y_range"][1] - config["y_range"][0]) / 4

            # Check if within tolerance
            x_match = x_diff <= x_tolerance
            y_match = y_diff <= y_tolerance

            # Both x and y must match
            match = x_match and y_match
            results[f"Landmark {landmark} Position"] = match

            if match:
                weighted_score += weight
        else:
            # Landmark not found in one or both
            results[f"Landmark {landmark} Missing"] = False

    # Compare overall structure
    # Table count similarity
    if "tables_count" in template_layout and "tables_count" in page_layout:
        table_match = template_layout["tables_count"] == page_layout["tables_count"]
        results["Table Count Match"] = table_match

        weight = 1.0
        total_weight += weight
        if table_match:
            weighted_score += weight

    # Text block count within 10% is considered similar
    if "text_blocks_count" in template_layout and "text_blocks_count" in page_layout:
        template_blocks = template_layout["text_blocks_count"]
        page_blocks = page_layout["text_blocks_count"]

        if template_blocks > 0:
            block_diff_pct = abs(template_blocks - page_blocks) / template_blocks
            block_match = block_diff_pct <= 0.1  # Within 10%

            results["Text Block Count Match"] = block_match
            weight = 1.0
            total_weight += weight
            if block_match:
                weighted_score += weight

    # Calculate overall similarity score
    similarity_score = weighted_score / total_weight if total_weight > 0 else 0

    return similarity_score, results


def calibrate_landmarks(template_layout: Dict[str, Any]) -> None:
    """Calibrate the positional landmarks based on the template layout.

    Args:
        template_layout: Layout information from the template
    """
    global POSITIONAL_LANDMARKS

    template_landmarks = template_layout.get("landmarks", {})
    if not template_landmarks:
        logger.warning("Cannot calibrate landmarks: no landmarks found in template")
        return

    logger.info("Calibrating positional landmarks based on template:")

    # For each landmark that exists in the template, update the positional range
    for landmark_name, config in POSITIONAL_LANDMARKS.items():
        if landmark_name in template_landmarks:
            pos = template_landmarks[landmark_name]
            x, y = pos["x"], pos["y"]

            # Create a range of +/- 15% around the position
            x_margin = 50  # pixels
            y_margin = 50  # pixels

            # Update the positional range
            new_x_range = (max(0, x - x_margin), x + x_margin)
            new_y_range = (max(0, y - y_margin), y + y_margin)

            # Log the update
            logger.info(
                f"  - {landmark_name}: Updated ranges "
                f"X: {config['x_range']} -> {new_x_range}, "
                f"Y: {config['y_range']} -> {new_y_range}"
            )

            # Update the configuration
            POSITIONAL_LANDMARKS[landmark_name]["x_range"] = new_x_range
            POSITIONAL_LANDMARKS[landmark_name]["y_range"] = new_y_range
        else:
            logger.warning(f"Landmark '{landmark_name}' not found in template, keeping default ranges")

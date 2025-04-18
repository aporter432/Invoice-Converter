"""Field Recognition module for extracting structured data from invoice pages."""

import os
from typing import Any, Dict, Optional, Tuple

import pdfplumber
import tomli
from rapidfuzz import fuzz


class FieldRecognizer:
    """Recognizes and extracts fields from PDF invoices based on template configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the field recognizer with configuration.

        Args:
            config_path: Path to pyproject.toml containing configuration.
                         If None, will look for pyproject.toml in current directory.
        """
        self.config = self._load_config(config_path)
        self.template_path = self.config["template"]["template_path"]
        self.fields = self.config["template"]["fields"]
        self.confidence_threshold = self.config["field_recognition"]["confidence_threshold"]
        self.use_fuzzy_matching = self.config["field_recognition"]["use_fuzzy_matching"]
        self.fuzzy_threshold = self.config["field_recognition"].get("threshold_for_fuzzy_match", 90)

        # Ensure template file exists
        if not os.path.exists(self.template_path):
            raise FileNotFoundError(f"Template file not found: {self.template_path}")

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from pyproject.toml.

        Args:
            config_path: Path to pyproject.toml file.

        Returns:
            Dict containing configuration.
        """
        if config_path is None:
            config_path = "pyproject.toml"

        with open(config_path, "rb") as f:
            all_config = tomli.load(f)

        # Extract invoice converter config
        if "tool" not in all_config or "invoice_converter" not in all_config["tool"]:
            raise ValueError("Missing [tool.invoice_converter] section in pyproject.toml")

        # Explicitly return the nested dictionary with proper type
        return Dict[str, Any](all_config["tool"]["invoice_converter"])

    def extract_field_from_pdf(self, pdf_path: str, field_name: str) -> Tuple[str, float]:
        """Extract a specific field from a PDF based on template configuration.

        Args:
            pdf_path: Path to the PDF file.
            field_name: Name of the field to extract.

        Returns:
            Tuple of (extracted text, confidence score)
        """
        # Find field configuration
        field_config = next((f for f in self.fields if f["name"] == field_name), None)
        if field_config is None:
            raise ValueError(f"Field '{field_name}' not defined in template configuration")

        # Extract region coordinates
        region = field_config["region"]

        # Open PDF and extract the page
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) < 1:
                raise ValueError("PDF has no pages")

            page = pdf.pages[0]  # Assume first page for now

            # Get page dimensions
            width = page.width
            height = page.height

            # Convert relative coordinates to absolute
            x1, y1, x2, y2 = region
            abs_x1 = int(x1 * width)
            abs_y1 = int(y1 * height)
            abs_x2 = int(x2 * width)
            abs_y2 = int(y2 * height)

            # Crop to the region
            crop = page.crop((abs_x1, abs_y1, abs_x2, abs_y2))

            # Extract text
            text = crop.extract_text() or ""

            # TODO: Implement confidence scoring based on OCR quality
            confidence = 1.0 if text else 0.0

            return text.strip(), confidence

    def extract_all_fields(self, pdf_path: str) -> Dict[str, Tuple[str, float]]:
        """Extract all fields from a PDF based on template configuration.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dict mapping field names to tuples of (extracted text, confidence score)
        """
        results = {}
        for field in self.fields:
            field_name = field["name"]
            try:
                text, confidence = self.extract_field_from_pdf(pdf_path, field_name)
                results[field_name] = (text, confidence)
            except Exception as e:
                print(f"Error extracting field '{field_name}': {e}")
                results[field_name] = ("", 0.0)

        return results

    def compare_with_template(self, pdf_path: str) -> Tuple[bool, float, Dict[str, Any]]:
        """Compare a PDF with the template to determine if it matches.

        Args:
            pdf_path: Path to the PDF to compare with template.

        Returns:
            Tuple of (is_match, match_score, field_details)
        """
        # Extract fields from the PDF
        fields = self.extract_all_fields(pdf_path)

        # Extract fields from the template for comparison
        template_fields = self.extract_all_fields(self.template_path)

        # Compare each field
        match_scores = []
        field_details = {}

        for field_name, (field_text, field_conf) in fields.items():
            template_text, _ = template_fields.get(field_name, ("", 0.0))

            # Skip empty fields for matching
            if not template_text or not field_text:
                continue

            # Compare text with fuzzy matching if enabled
            if self.use_fuzzy_matching:
                similarity = fuzz.ratio(field_text, template_text) / 100.0
            else:
                similarity = 1.0 if field_text == template_text else 0.0

            match_scores.append(similarity)
            field_details[field_name] = {"text": field_text, "similarity": similarity, "confidence": field_conf}

        # Calculate overall match score
        avg_match_score = sum(match_scores) / len(match_scores) if match_scores else 0.0
        is_match = avg_match_score >= self.confidence_threshold

        return is_match, avg_match_score, field_details


def recognize_fields(pdf_path: str, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Recognize fields in a PDF based on template configuration.

    Args:
        pdf_path: Path to the PDF file.
        config_path: Path to pyproject.toml containing configuration.

    Returns:
        Dict containing recognized fields and match information.
    """
    recognizer = FieldRecognizer(config_path)
    fields = recognizer.extract_all_fields(pdf_path)

    result: Dict[str, Any] = {"pdf_path": pdf_path, "fields": {}}

    for field_name, (text, confidence) in fields.items():
        result["fields"][field_name] = {"text": text, "confidence": confidence}

    return result

"""
Field Extraction Module.

This module handles extraction of text and data from specific regions of PDF documents.
"""

from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import pdfplumber
import pytesseract
from PIL import Image
from rapidfuzz import fuzz


class FieldExtractor:
    """Class for extracting fields from PDFs based on region definitions."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the field extractor.

        Args:
            config: Configuration dictionary with field definitions and options
        """
        self.config = config or {}
        self.confidence_threshold = self.config.get("field_recognition", {}).get("confidence_threshold", 0.85)
        self.use_fuzzy_matching = self.config.get("field_recognition", {}).get("use_fuzzy_matching", True)
        self.fuzzy_threshold = self.config.get("field_recognition", {}).get("threshold_for_fuzzy_match", 90)

    def extract_text_from_region(self, pdf_page: Any, region: List[float]) -> str:
        """
        Extract text from a region of a PDF page.

        Args:
            pdf_page: pdfplumber page object
            region: List of [x1, y1, x2, y2] coordinates as fractions of page dimensions

        Returns:
            Extracted text from the region
        """
        # Convert relative coordinates to absolute
        x1, y1, x2, y2 = region
        width, height = float(pdf_page.width), float(pdf_page.height)

        abs_x1, abs_y1 = int(x1 * width), int(y1 * height)
        abs_x2, abs_y2 = int(x2 * width), int(y2 * height)

        # Crop the page to the region of interest
        try:
            cropped = pdf_page.crop((abs_x1, abs_y1, abs_x2, abs_y2))
            text = cropped.extract_text() or ""
            return text.strip()
        except Exception as e:
            print(f"Error extracting text from region: {e}")
            return ""

    def enhance_image_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Enhance an image to improve OCR results.

        Args:
            image: PIL Image object

        Returns:
            Enhanced PIL Image
        """
        # Convert to OpenCV format
        img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Apply thresholding
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Noise removal
        kernel = np.ones((1, 1), np.uint8)
        opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

        # Convert back to PIL
        return Image.fromarray(opening)

    def extract_text_with_ocr(self, pdf_page: Any, region: List[float]) -> str:
        """
        Extract text from a region using OCR.

        Args:
            pdf_page: pdfplumber page object
            region: List of [x1, y1, x2, y2] coordinates as fractions of page dimensions

        Returns:
            OCR-extracted text from the region
        """
        # Convert relative coordinates to absolute
        x1, y1, x2, y2 = region
        width, height = float(pdf_page.width), float(pdf_page.height)

        abs_x1, abs_y1 = int(x1 * width), int(y1 * height)
        abs_x2, abs_y2 = int(x2 * width), int(y2 * height)

        try:
            # Get the image - pdfplumber returns a PageImage object
            img = pdf_page.to_image(resolution=300)

            # For pdfplumber's PageImage object, we need to use the correct approach
            # The bbox parameter is what we need instead of crop
            bbox = (abs_x1, abs_y1, abs_x2, abs_y2)

            # Convert to PIL Image and then crop
            pil_image = img.original
            cropped_pil = pil_image.crop(bbox)

            # Enhance for OCR
            enhanced_img = self.enhance_image_for_ocr(cropped_pil)

            # Perform OCR
            ocr_result = pytesseract.image_to_string(enhanced_img)
            # Ensure we return a string, even if OCR returns None
            return str(ocr_result).strip() if ocr_result is not None else ""
        except Exception as e:
            print(f"Error extracting text with OCR: {e}")
            return ""

    def extract_all_fields(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract all defined fields from a PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary of field names and their values, can be converted to InvoiceFieldData
        """
        result: Dict[str, Any] = {}
        fields = self.config.get("fields", [])

        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]

            for field in fields:
                field_name = field.get("name")
                field_type = field.get("type", "")  # Ensure we have a string default
                region = field.get("region")

                if not all([field_name, field_type, region]):
                    continue

                # Extract text from the region - ensure we have a string
                text = self.extract_text_from_region(first_page, region)
                text = "" if text is None else str(text)

                # If no text found with standard extraction, try OCR
                if not text:
                    text_ocr = self.extract_text_with_ocr(first_page, region)
                    text = "" if text_ocr is None else str(text_ocr)

                # Process based on field type
                if field_type == "date":
                    # Try to identify and format the date
                    # This is a simplified implementation
                    result[field_name] = self.process_date(text)
                elif field_type == "amount":
                    # Extract numeric values and format
                    result[field_name] = self.process_amount(text)
                else:
                    # Default text processing
                    result[field_name] = text

        return result

    def process_date(self, text: str) -> str:
        """
        Process and standardize a date string.

        Args:
            text: Extracted date text

        Returns:
            Standardized date string
        """
        # This is a simplified implementation
        # In a real system, you would use more sophisticated date parsing
        if text is None:
            return ""
        # Ensure we always return a string
        return str(text)

    def process_amount(self, text: str) -> str:
        """
        Process and standardize an amount string.

        Args:
            text: Extracted amount text

        Returns:
            Standardized amount string
        """
        # Remove non-numeric characters except dots and commas
        amount_text = "".join(c for c in text if c.isdigit() or c in ".,")

        # Try to convert to a float for validation
        try:
            # Replace comma with dot if needed
            if "," in amount_text and "." not in amount_text:
                amount_text = amount_text.replace(",", ".")

            # Convert to float and back to string for consistent formatting
            amount = float(amount_text)
            return f"{amount:.2f}"
        except (ValueError, TypeError):
            # If conversion fails, return the original text
            return amount_text

    def extract_table(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract a table of line items from the PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            List of dictionaries containing line item data, can be converted to LineItem models
        """
        line_items: List[Dict[str, Any]] = []
        table_config = self.config.get("table_extraction", {})
        table_region = table_config.get("table_region")
        column_mapping = table_config.get("column_mapping", [])

        if not table_region:
            return line_items

        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0]

            # Convert relative coordinates to absolute
            x1, y1, x2, y2 = table_region
            width, height = float(first_page.width), float(first_page.height)

            abs_x1, abs_y1 = int(x1 * width), int(y1 * height)
            abs_x2, abs_y2 = int(x2 * width), int(y2 * height)

            # Crop the page to the table region
            table_area = first_page.crop((abs_x1, abs_y1, abs_x2, abs_y2))

            # Extract tables from the cropped area
            tables = table_area.extract_tables()

            if not tables:
                # If no tables found with default settings, try with custom settings
                tables_result = table_area.find_tables(
                    table_settings={
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 5,
                    }
                )
                if tables_result:
                    tables = [table.extract() for table in tables_result]

            if not tables:
                # If still no tables, try OCR-based approach
                # This is a placeholder - real implementation would be more complex
                return line_items

            # Process the first table found
            table = tables[0]

            # Skip if empty
            if not table or len(table) <= 1:
                return line_items

            # Determine if the first row is a header
            has_header = table_config.get("header_row", True)
            start_row = 1 if has_header else 0

            # Process rows
            for row_idx, row in enumerate(table[start_row:], start=start_row):
                # Skip empty rows
                if not any(cell for cell in row if cell):
                    continue

                line_item: Dict[str, Any] = {}

                # Map columns based on configuration
                for col_map in column_mapping:
                    col_name = col_map.get("name")
                    col_idx = col_map.get("index")

                    if col_name and col_idx is not None and col_idx < len(row):
                        line_item[col_name] = row[col_idx] or ""

                # Only add if we have at least some data
                if line_item:
                    line_items.append(line_item)

        return line_items

    def compare_fields(self, source_fields: Dict[str, Any], target_fields: Dict[str, Any]) -> float:
        """
        Compare two sets of fields to determine similarity.

        Args:
            source_fields: Fields extracted from source document
            target_fields: Fields extracted from target document

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not source_fields or not target_fields:
            return 0.0

        total_score = 0.0
        count = 0

        for field_name, source_value in source_fields.items():
            if not source_value or field_name not in target_fields:
                continue

            target_value = target_fields[field_name]
            if not target_value:
                continue

            # Convert values to strings for comparison
            source_str = str(source_value)
            target_str = str(target_value)

            # Use fuzzy matching if enabled
            if self.use_fuzzy_matching:
                similarity = fuzz.ratio(source_str, target_str) / 100.0
            else:
                # Simple exact match
                similarity = 1.0 if source_str == target_str else 0.0

            total_score += similarity
            count += 1

        # Return average similarity
        return total_score / max(count, 1)

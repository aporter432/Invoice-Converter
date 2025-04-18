"""Module for detecting structural elements in PDF documents."""

from typing import Any, Dict, List

import camelot
import pdfplumber

from invoice_converter.text_recognition import TextRecognizer


class StructureDetector:
    """Detects and analyzes structural elements in invoice documents."""

    def __init__(self) -> None:
        """Initialize the structure detector."""
        self.text_recognizer = TextRecognizer()

    def detect_tables(self, pdf_path: str, page_num: int = 0) -> List[Dict[str, Any]]:
        """Detect tables in a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            page_num: Page number (0-indexed).

        Returns:
            List of detected tables with their properties.
        """
        # Use camelot for table detection
        try:
            # Add 1 to page_num because camelot uses 1-based indexing
            tables = camelot.read_pdf(pdf_path, pages=str(page_num + 1), flavor="lattice")

            results = []
            for i, table in enumerate(tables):
                # Get table dataframe
                df = table.df

                # Extract table metadata
                table_dict = {
                    "index": i,
                    "rows": len(df),
                    "columns": len(df.columns) if len(df) > 0 else 0,
                    "accuracy": table.accuracy,
                    "whitespace": table.whitespace,
                    "data": df.to_dict(orient="records"),
                }
                results.append(table_dict)

            return results

        except Exception as e:
            print(f"Error detecting tables: {e}")
            return []

    def detect_lines(self, pdf_path: str, page_num: int = 0) -> List[Dict[str, Any]]:
        """Detect lines in a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            page_num: Page number (0-indexed).

        Returns:
            List of detected lines with their properties.
        """
        with pdfplumber.open(pdf_path) as pdf:
            if page_num >= len(pdf.pages):
                raise ValueError(f"Page {page_num} does not exist in PDF with {len(pdf.pages)} pages")

            page = pdf.pages[page_num]

            # Get horizontal and vertical lines
            h_lines = page.horizontal_edges
            v_lines = page.vertical_edges

            # Process horizontal lines
            horizontal_lines = []
            for line in h_lines:
                horizontal_lines.append(
                    {
                        "x0": line["x0"],
                        "y0": line["top"],
                        "x1": line["x1"],
                        "y1": line["top"],
                        "width": line["width"],
                        "orientation": "horizontal",
                    }
                )

            # Process vertical lines
            vertical_lines = []
            for line in v_lines:
                vertical_lines.append(
                    {
                        "x0": line["x0"],
                        "y0": line["top"],
                        "x1": line["x0"],
                        "y1": line["bottom"],
                        "height": line["height"],
                        "orientation": "vertical",
                    }
                )

            return horizontal_lines + vertical_lines

    def detect_headers(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """Detect header section in a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            page_num: Page number (0-indexed).

        Returns:
            Dict containing header information.
        """
        # Extract text from the top portion of the document
        header_region = (0.0, 0.0, 1.0, 0.2)  # Top 20% of the page
        header_text, metadata = self.text_recognizer.extract_text_from_pdf_region(pdf_path, header_region, page_num)

        return {
            "region": header_region,
            "text": header_text,
            "confidence": metadata["confidence"],
            "word_count": metadata["word_count"],
        }

    def detect_footers(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """Detect footer section in a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            page_num: Page number (0-indexed).

        Returns:
            Dict containing footer information.
        """
        # Extract text from the bottom portion of the document
        footer_region = (0.0, 0.8, 1.0, 1.0)  # Bottom 20% of the page
        footer_text, metadata = self.text_recognizer.extract_text_from_pdf_region(pdf_path, footer_region, page_num)

        return {
            "region": footer_region,
            "text": footer_text,
            "confidence": metadata["confidence"],
            "word_count": metadata["word_count"],
        }

    def analyze_structure(self, pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
        """Analyze the structure of a PDF document.

        Args:
            pdf_path: Path to the PDF file.
            page_num: Page number (0-indexed).

        Returns:
            Dict containing structural analysis.
        """
        # Detect various structural elements
        tables = self.detect_tables(pdf_path, page_num)
        lines = self.detect_lines(pdf_path, page_num)
        header = self.detect_headers(pdf_path, page_num)
        footer = self.detect_footers(pdf_path, page_num)

        # Count structural elements
        num_tables = len(tables)
        num_horizontal_lines = sum(1 for line in lines if line["orientation"] == "horizontal")
        num_vertical_lines = sum(1 for line in lines if line["orientation"] == "vertical")

        # Create a structural fingerprint
        structural_fingerprint = {
            "num_tables": num_tables,
            "num_horizontal_lines": num_horizontal_lines,
            "num_vertical_lines": num_vertical_lines,
            "has_header": len(header["text"]) > 0,
            "has_footer": len(footer["text"]) > 0,
        }

        return {
            "pdf_path": pdf_path,
            "page": page_num,
            "tables": tables,
            "lines": lines,
            "header": header,
            "footer": footer,
            "structural_fingerprint": structural_fingerprint,
        }


def detect_structure(pdf_path: str, page_num: int = 0) -> Dict[str, Any]:
    """Detect and analyze the structure of a PDF document.

    Args:
        pdf_path: Path to the PDF file.
        page_num: Page number (0-indexed).

    Returns:
        Dict containing structural analysis.
    """
    detector = StructureDetector()
    return detector.analyze_structure(pdf_path, page_num)

"""
PDF Manipulation Module.

This module handles the creation and manipulation of PDF documents
for the invoice conversion process.
"""

import io
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
import pdfrw
from PIL import Image, ImageDraw, ImageFont  # noqa: F401
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter  # noqa: F401
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

from invoice_converter.models import (
    ExtractedData,
    FormField,
    InvoiceFieldData,
    LineItem,
    PageSize,
    PDFStructure,
    TableInfo,
    TextElement,
)


class PDFManipulator:
    """Class for manipulating PDFs in the invoice conversion process."""

    def __init__(self, template_path: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the PDF manipulator.

        Args:
            template_path: Path to the template PDF
            config: Configuration dictionary
        """
        self.template_path = template_path
        self.config = config or {}

    def create_filled_invoice(self, field_data: InvoiceFieldData, line_items: List[LineItem], output_path: str) -> str:
        """
        Create a new invoice by filling the template with data.

        Args:
            field_data: Pydantic model containing field names and values
            line_items: List of line item Pydantic models
            output_path: Path where the new PDF should be saved

        Returns:
            Path to the created PDF
        """
        # For a real implementation, you would need to choose one of several approaches:
        # 1. If the template is a fillable PDF form, use pdfrw to fill the form fields
        # 2. If the template is not a form, create a new PDF with reportlab and overlay it
        # 3. For more complex cases, you might use a combination of approaches

        # For this simplified example, we'll use approach #2
        # This is a basic implementation that would need enhancement for production

        # Create a new PDF with reportlab
        buffer = io.BytesIO()

        # Get page size from template
        with pdfplumber.open(self.template_path) as pdf:
            first_page = pdf.pages[0]
            page_width = float(first_page.width)
            page_height = float(first_page.height)

        # Create canvas with matching page size
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

        # Add all text fields based on configuration
        self._add_text_fields(c, field_data)

        # Add line items table
        self._add_line_items_table(c, line_items)

        # Finalize the PDF
        c.save()

        # Combine with template (optional - depends on approach)
        self._overlay_on_template(buffer, output_path)

        return output_path

    def _add_text_fields(self, c: canvas.Canvas, field_data: InvoiceFieldData) -> None:
        """
        Add text fields to the canvas.

        Args:
            c: ReportLab canvas object
            field_data: Pydantic model containing field data
        """
        fields = self.config.get("fields", [])

        for field in fields:
            field_name = field.get("name")
            region = field.get("region")

            if not field_name or not region:
                continue

            # Get field value - check if it's a direct attribute or in additional_fields
            if hasattr(field_data, field_name):
                value = getattr(field_data, field_name)
            else:
                value = field_data.additional_fields.get(field_name)

            if value is None:
                continue

            # Convert region to absolute coordinates
            x1, y1, x2, y2 = region
            page_width, page_height = c._pagesize

            # Calculate position (center of region)
            x_pos = x1 * page_width + (x2 - x1) * page_width / 2
            y_pos = page_height - (y1 * page_height + (y2 - y1) * page_height / 2)

            # Add text
            c.setFont("Helvetica", 10)
            c.drawString(x_pos, y_pos, str(value))

    def _add_line_items_table(self, c: canvas.Canvas, line_items: List[LineItem]) -> None:
        """
        Add a table of line items to the canvas.

        Args:
            c: ReportLab canvas object
            line_items: List of LineItem Pydantic models
        """
        if not line_items:
            return

        table_config = self.config.get("table_extraction", {})
        table_region = table_config.get("table_region")

        if not table_region:
            return

        # Convert region to absolute coordinates
        x1, y1, x2, y2 = table_region
        page_width, page_height = c._pagesize

        table_x = x1 * page_width
        table_y = page_height - y2 * page_height
        table_width = (x2 - x1) * page_width
        table_height = (y2 - y1) * page_height

        # Create column headers
        column_mapping = table_config.get("column_mapping", [])
        headers = []
        for col_map in sorted(column_mapping, key=lambda x: x.get("index", 0)):
            headers.append(col_map.get("name", "").title())

        # Prepare data for the table
        data = [headers]

        for item in line_items:
            row = []
            for col_map in sorted(column_mapping, key=lambda x: x.get("index", 0)):
                col_name = col_map.get("name")
                if col_name and hasattr(item, col_name):
                    row.append(getattr(item, col_name) or "")
                else:
                    row.append("")
            data.append(row)

        # Create the table
        table = Table(data, colWidths=[table_width / len(headers)] * len(headers))

        # Style the table
        style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ]
        )

        table.setStyle(style)

        # Draw the table on the canvas
        table.wrapOn(c, table_width, table_height)
        table.drawOn(c, table_x, table_y)

    def _overlay_on_template(self, content_buffer: io.BytesIO, output_path: str) -> None:
        """
        Overlay content on the template PDF.

        Args:
            content_buffer: Buffer containing the content to overlay
            output_path: Path where the new PDF should be saved
        """
        # Read the template
        template = pdfrw.PdfReader(self.template_path)

        # Read the content to overlay
        content_buffer.seek(0)
        overlay = pdfrw.PdfReader(content_buffer)

        # Check that both PDFs have pages
        template_pages = getattr(template, "pages", None)
        overlay_pages = getattr(overlay, "pages", None)

        if template_pages is None or overlay_pages is None:
            # Handle case where pages are missing
            raise ValueError("Invalid PDF structure: missing pages in template or overlay")

        # Type assertions to help static type checker
        from typing import List, cast

        template_pages = cast(List, template_pages)
        overlay_pages = cast(List, overlay_pages)

        # For each page in the template
        for i, page in enumerate(template_pages):
            if i < len(overlay_pages):
                # Merge the content onto the template
                page.Merge(overlay_pages[i])

        # Write the output
        pdfrw.PdfWriter().write(output_path, template)

    def extract_template_structure(self) -> PDFStructure:
        """
        Extract the structure of the template PDF for reference.

        Returns:
            PDFStructure model containing template structure information
        """
        structure = PDFStructure()

        # Extract basic structure using pdfplumber
        with pdfplumber.open(self.template_path) as pdf:
            structure.page_count = len(pdf.pages)

            for i, page in enumerate(pdf.pages):
                # Page size
                structure.page_sizes.append(PageSize(page=i + 1, width=float(page.width), height=float(page.height)))

                # Extract text elements
                words = page.extract_words()
                for word in words:
                    structure.text_elements.append(
                        TextElement(
                            page=i + 1,
                            text=word["text"],
                            x0=float(word["x0"]),
                            y0=float(word["top"]),
                            x1=float(word["x1"]),
                            y1=float(word["bottom"]),
                        )
                    )

                # Find tables
                tables = page.find_tables()
                for table_idx, table in enumerate(tables):
                    structure.tables.append(
                        TableInfo(
                            page=i + 1,
                            table_index=table_idx,
                            bbox=(
                                float(table.bbox[0]),
                                float(table.bbox[1]),
                                float(table.bbox[2]),
                                float(table.bbox[3]),
                            ),
                        )
                    )

        # Check for form fields using pdfrw
        reader = pdfrw.PdfReader(self.template_path)

        # Make sure reader.pages exists and is iterable
        pages = getattr(reader, "pages", None)
        if pages is not None:
            for i, page in enumerate(pages):
                annots = getattr(page, "Annots", None)
                if annots is not None:
                    for j, annot in enumerate(annots):
                        field_type = getattr(annot, "FT", None)
                        if field_type is not None:
                            # This is a form field
                            field_type_str = field_type[1:-1]  # Remove parentheses

                            # Get field name
                            field_name_obj = getattr(annot, "T", None)
                            field_name = field_name_obj[1:-1] if field_name_obj is not None else f"Field_{i}_{j}"

                            structure.form_fields.append(
                                FormField(page=i + 1, field_name=field_name, field_type=field_type_str)
                            )

        return structure

    def compare_structure(self, pdf_path: str) -> float:
        """
        Compare the structure of a PDF to the template.

        Args:
            pdf_path: Path to the PDF to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Extract structure of both PDFs
        template_structure = self.extract_template_structure()

        # Create a temporary structure for the target PDF
        target_structure = PDFStructure()

        # Extract basic structure of target PDF
        with pdfplumber.open(pdf_path) as pdf:
            target_structure.page_count = len(pdf.pages)

            # Only check first page for simplicity
            if len(pdf.pages) > 0:
                page = pdf.pages[0]

                # Page size
                target_structure.page_sizes.append(PageSize(page=1, width=float(page.width), height=float(page.height)))

                # Extract words
                words = page.extract_words()
                for word in words:
                    target_structure.text_elements.append(
                        TextElement(
                            page=1,
                            text=word["text"],
                            x0=float(word["x0"]),
                            y0=float(word["top"]),
                            x1=float(word["x1"]),
                            y1=float(word["bottom"]),
                        )
                    )

                # Find tables
                tables = page.find_tables()
                for table_idx, table in enumerate(tables):
                    target_structure.tables.append(
                        TableInfo(
                            page=1,
                            table_index=table_idx,
                            bbox=(
                                float(table.bbox[0]),
                                float(table.bbox[1]),
                                float(table.bbox[2]),
                                float(table.bbox[3]),
                            ),
                        )
                    )

        # Calculate similarity score
        # This is a simplified implementation - real implementation would be more sophisticated

        # 1. Compare page count
        if template_structure.page_count != target_structure.page_count:
            # Different page count means lower similarity
            page_count_similarity = 0.5
        else:
            page_count_similarity = 1.0

        # 2. Compare page sizes
        size_similarity = 0.0
        if len(template_structure.page_sizes) > 0 and len(target_structure.page_sizes) > 0:

            template_size = template_structure.page_sizes[0]
            target_size = target_structure.page_sizes[0]

            # Calculate size difference
            width_diff = abs(template_size.width - target_size.width) / max(template_size.width, 1)
            height_diff = abs(template_size.height - target_size.height) / max(template_size.height, 1)

            # Page size similarity
            size_similarity = 1.0 - (width_diff + height_diff) / 2

        # 3. Compare table structure
        table_similarity = 0.0
        template_table_count = len(template_structure.tables)
        target_table_count = len(target_structure.tables)

        if template_table_count == 0 and target_table_count == 0:
            # Both have no tables
            table_similarity = 1.0
        elif template_table_count == 0 or target_table_count == 0:
            # One has tables, the other doesn't
            table_similarity = 0.0
        else:
            # Both have tables
            count_similarity = min(template_table_count, target_table_count) / max(
                template_table_count, target_table_count
            )

            # Compare table positions
            position_similarity = 0.0
            if min(template_table_count, target_table_count) > 0:
                # For simplicity, just compare the first table
                template_table = template_structure.tables[0]
                target_table = target_structure.tables[0]

                # Calculate overlap
                overlap = self._calculate_bbox_overlap(template_table.bbox, target_table.bbox)

                position_similarity = overlap

            table_similarity = (count_similarity + position_similarity) / 2

        # Combine scores - weights can be adjusted based on importance
        final_score = page_count_similarity * 0.2 + size_similarity * 0.3 + table_similarity * 0.5

        return min(max(final_score, 0.0), 1.0)

    def _calculate_bbox_overlap(
        self, bbox1: Tuple[float, float, float, float], bbox2: Tuple[float, float, float, float]
    ) -> float:
        """
        Calculate the overlap between two bounding boxes.

        Args:
            bbox1: First bounding box (x0, y0, x1, y1)
            bbox2: Second bounding box (x0, y0, x1, y1)

        Returns:
            Overlap as a value between 0.0 and 1.0
        """
        # Calculate intersection area
        x_overlap = max(0, min(bbox1[2], bbox2[2]) - max(bbox1[0], bbox2[0]))
        y_overlap = max(0, min(bbox1[3], bbox2[3]) - max(bbox1[1], bbox2[1]))

        intersection_area = x_overlap * y_overlap

        # Calculate area of each box
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])

        # Calculate union area
        union_area = area1 + area2 - intersection_area

        # Calculate overlap ratio (Intersection over Union)
        if union_area == 0:
            return 0.0

        return intersection_area / union_area

    def convert_invoice(
        self, source_path: str, output_path: str, extracted_data: Optional[ExtractedData] = None
    ) -> str:
        """
        Convert an invoice from source format to the template format.

        Args:
            source_path: Path to the source invoice PDF
            output_path: Path where the converted invoice should be saved
            extracted_data: Optional pre-extracted data from the source as Pydantic model

        Returns:
            Path to the converted invoice
        """
        # Extract data from source if not provided
        if extracted_data is None:
            from invoice_converter.field_extraction import FieldExtractor

            # Create a field extractor
            extractor = FieldExtractor(self.config)

            # Extract fields and line items
            field_data = InvoiceFieldData.model_validate(extractor.extract_all_fields(source_path))

            # Convert list of dictionaries to list of LineItem models
            raw_line_items = extractor.extract_table(source_path)
            line_items = [LineItem.model_validate(item) for item in raw_line_items]
        else:
            # Use provided data
            field_data = extracted_data.fields
            line_items = extracted_data.line_items

        # Create new invoice with the extracted data
        return self.create_filled_invoice(field_data, line_items, output_path)

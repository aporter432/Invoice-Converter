"""
Data models for the invoice conversion process.

These models use Pydantic for data validation and type checking.
"""

from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, Field


class PageSize(BaseModel):
    """Model representing the size of a PDF page."""

    page: int
    width: float
    height: float


class TextElement(BaseModel):
    """Model representing a text element in a PDF."""

    page: int
    text: str
    x0: float
    y0: float  # top
    x1: float
    y1: float  # bottom


class TableInfo(BaseModel):
    """Model representing a table in a PDF."""

    page: int
    table_index: int
    bbox: Tuple[float, float, float, float]  # x0, y0, x1, y1


class FormField(BaseModel):
    """Model representing a form field in a PDF."""

    page: int
    field_name: str
    field_type: str


class PDFStructure(BaseModel):
    """Model representing the structure of a PDF document."""

    page_count: int = 0
    page_sizes: List[PageSize] = Field(default_factory=list)
    text_elements: List[TextElement] = Field(default_factory=list)
    form_fields: List[FormField] = Field(default_factory=list)
    images: List[Any] = Field(default_factory=list)
    tables: List[TableInfo] = Field(default_factory=list)


class LineItem(BaseModel):
    """Model representing a line item in an invoice."""

    site_name: Optional[str] = None
    item: Optional[str] = None
    quantity: Optional[Union[int, float, str]] = None
    rate: Optional[Union[float, str]] = None
    description: Optional[str] = None
    subtotal: Optional[Union[float, str]] = None
    tax_rate: Optional[Union[float, str]] = None


class InvoiceFieldData(BaseModel):
    """Model representing the extracted field data from an invoice."""

    invoice_number: Optional[str] = None
    date: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    po_number: Optional[str] = None
    service_period: Optional[str] = None
    terms: Optional[str] = None
    total_amount: Optional[Union[float, str]] = None

    # Additional fields can be added dynamically
    additional_fields: Dict[str, Any] = Field(default_factory=dict)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access to fields."""
        if hasattr(self, key):
            return getattr(self, key)
        return self.additional_fields.get(key)


class ColumnMapping(BaseModel):
    """Model representing a column mapping for table extraction."""

    name: str
    index: int


class TableExtractionConfig(BaseModel):
    """Configuration for table extraction from PDFs."""

    table_region: Tuple[float, float, float, float]  # x0, y0, x1, y1
    header_row: bool = True
    column_mapping: List[ColumnMapping] = Field(default_factory=list)


class FieldConfig(BaseModel):
    """Configuration for a field in a PDF template."""

    name: str
    type: Literal["text", "date", "amount"] = "text"
    region: Tuple[float, float, float, float]  # x0, y0, x1, y1
    description: Optional[str] = None


class FieldRecognitionConfig(BaseModel):
    """Configuration for field recognition in PDFs."""

    confidence_threshold: float = 0.85
    use_fuzzy_matching: bool = True
    allow_multiple_matches: bool = False
    threshold_for_fuzzy_match: int = 90  # Percentage


class InvoiceTemplateConfig(BaseModel):
    """Complete configuration for an invoice template."""

    template_path: str
    field_recognition: FieldRecognitionConfig = Field(default_factory=FieldRecognitionConfig)
    fields: List[FieldConfig] = Field(default_factory=list)
    table_extraction: TableExtractionConfig = Field(
        default_factory=lambda: TableExtractionConfig(table_region=(0.0, 0.0, 0.0, 0.0))
    )


class ExtractedData(BaseModel):
    """Model representing all extracted data from an invoice."""

    fields: InvoiceFieldData = Field(default_factory=InvoiceFieldData)
    line_items: List[LineItem] = Field(default_factory=list)

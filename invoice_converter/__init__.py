"""Invoice Converter - A tool to convert and process PDF invoices.

This package provides functionality for analyzing and converting PDF invoices
based on template matching. It can be used to standardize the format of invoices
from different sources.
"""

__version__ = "0.1.0"

# These imports are needed for the package API but not used directly in this file
# We use __all__ to make them part of the public API
from invoice_converter.field_extraction import FieldExtractor  # noqa: F401
from invoice_converter.pdf_manipulation import PDFManipulator  # noqa: F401

__all__ = ["FieldExtractor", "PDFManipulator"]


def main() -> None:
    """
    Execute the main command-line interface.

    This function is called when the package is run as a module.
    """
    from invoice_converter.__main__ import main as main_func

    main_func()

"""Basic tests for the invoice_converter module."""

import unittest

import invoice_converter


class TestInvoiceConverter(unittest.TestCase):
    """Tests for the invoice_converter module."""

    def test_extract_invoice_number(self) -> None:
        """Test extracting invoice number from text."""
        # Test with valid invoice number
        text = "Some text with Invoice # 12345 in it"
        result = invoice_converter.extract_invoice_number(text)
        self.assertEqual(result, "12345")

        # Test with no invoice number
        text = "Some text with no invoice number"
        result = invoice_converter.extract_invoice_number(text)
        self.assertIsNone(result)

    def test_is_new_format(self) -> None:
        """Test checking if an invoice is in the new format."""
        # Test with text containing all markers
        text = "Site Name # Item Qty Rate Description Subtotal Tax Rate"
        result = invoice_converter.is_new_format(text)
        self.assertTrue(result)

        # Test with text missing markers
        text = "Site Name # Item Description"
        result = invoice_converter.is_new_format(text)
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

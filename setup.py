"""Setup script for the invoice_converter package."""

from setuptools import find_packages, setup

setup(
    name="invoice_converter",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Pillow>=10.0.0",
        "pytesseract>=0.3.10",
        "pdfplumber>=0.9.0",
        "pdfrw>=0.4.0",
    ],
    entry_points={
        "console_scripts": [
            "invoice-converter=invoice_converter:main",
        ],
    },
)

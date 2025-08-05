#!/usr/bin/env python3
"""
Test script to verify Randolph parser fixes
"""

from game_scanner_app.utils.pdf_extractor import extract_text_from_pdf
from game_scanner_app.parsers.randolph import parse_randolph_invoice

def test_randolph_parser():
    # Test with one of the Randolph invoices
    pdf_path = 'invoices/Rnadolph/Invoice_INV_2025_07_1101.pdf'
    
    print("Testing Randolph parser...")
    print(f"Processing: {pdf_path}")
    
    with open(pdf_path, 'rb') as f:
        raw_text = extract_text_from_pdf(f)
    
    # Parse the invoice
    parsed_data = parse_randolph_invoice(raw_text)
    
    print(f"\nInvoice Number: {parsed_data.get('invoice_number')}")
    print(f"Invoice Date: {parsed_data.get('invoice_date')}")
    print(f"Total Items: {len(parsed_data.get('items', []))}")
    
    print("\nParsed Items:")
    for i, item in enumerate(parsed_data.get('items', []), 1):
        print(f"  {i}. SKU: {item.get('sku')}")
        print(f"     Name: {item.get('name')}")
        print(f"     Quantity: {item.get('quantity')}")
        print(f"     Unit Price: {item.get('unit_price')}")
        print()

if __name__ == "__main__":
    test_randolph_parser() 
import re
import pdfplumber
import fitz  # PyMuPDF
from datetime import datetime

def extract_lines_from_columns(pdf_path):
    """
    Extract text from PDF preserving column structure using PyMuPDF.
    This is better for invoices with tabular data.
    """
    doc = fitz.open(pdf_path)
    all_lines = []

    for page in doc:
        blocks = page.get_text("blocks")  # (x0, y0, x1, y1, "text", block_no, block_type)
        for b in sorted(blocks, key=lambda b: (b[1], b[0])):  # Sort by y, then x
            text = b[4]
            # Remove empty or very short lines
            if text.strip() and len(text.strip()) > 4:
                # Split multi-line blocks into lines
                lines = text.split('\n')
                all_lines.extend(lines)
    
    doc.close()
    return all_lines

def parse_quadsource_invoice(raw_text):
    """
    Parse Quad Source Canada INC. invoice format.
    
    Expected format:
    - Invoice number: NUMBER 0000244392
    - Invoice date: DATE July 30, 2025
    - Items in multi-line format where descriptions wrap and include serial numbers
    """
    
    invoice_data = {
        "distributor": "Quad Source",
        "invoice_number": "",
        "invoice_date": "",
        "items": []
    }
    
    # Extract invoice number
    invoice_match = re.search(r'NUMBER\s+(\d+)', raw_text)
    if invoice_match:
        invoice_data["invoice_number"] = invoice_match.group(1)
    
    # Extract invoice date
    date_match = re.search(r'DATE\s+([A-Za-z]+\s+\d+,\s+\d{4})', raw_text)
    if date_match:
        date_str = date_match.group(1)
        try:
            parsed_date = datetime.strptime(date_str, "%B %d, %Y")
            invoice_data["invoice_date"] = parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            try:
                parsed_date = datetime.strptime(date_str, "%b %d, %Y")
                invoice_data["invoice_date"] = parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                print(f"Warning: Could not parse date: {date_str}")
    
    # Split lines
    lines = raw_text.split('\n')
    print(f"[DEBUG] Processing {len(lines)} lines for Quad Source invoice")
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        if not line:
            i += 1
            continue

        if any(keyword in line.upper() for keyword in ['SUBTOTAL', 'TOTAL', 'BALANCE', 'HST', 'GST', 'CANADIAN', 'FREIGHT']):
            break

        # Skip known non-product keywords
        if line.upper().startswith(("INVOICE", "NUMBER", "CUSTOMER", "QUAD SOURCE", "HTTP", "BILL TO", "SHIP TO", "DATE", "ORDER", "REQ.", "BO", "PRICE", "EXTENDED", "PART NUMBER", "DESCRIPTION")):
            i += 1
            continue

        # Look for part number at start of line
        part_number_match = re.match(r'^([A-Z0-9\-\.]{5,})', line)
        if part_number_match:
            part_number = part_number_match.group(1).strip()
            
            # Validate that this looks like a real product
            if re.search(r'[A-Z]', part_number) and (re.search(r'[0-9]', part_number) or re.search(r'\-', part_number)):
                print(f"[DEBUG] Found part number: {part_number}")
                
                # Build description from current and next lines
                description_lines = []
                current_desc = line[len(part_number):].strip()
                if current_desc:
                    description_lines.append(current_desc)
                
                # Look ahead for more description lines and the numerical data
                quantity = None
                unit_price = None
                j = 1
                
                while i + j < len(lines) and j < 10:  # Look up to 10 lines ahead
                    next_line = lines[i + j].strip()
                    print(f"[DEBUG] Checking line {i+j}: '{next_line}'")
                    
                    # Check if this line has numerical data (quantity, backorder, unit_price, extended_price)
                    num_pattern = re.search(r'^\s*(\d+)\s+(\d+)\s+(\d+\.\d{1,2})\s+(\d+\.\d{1,2})\s*$', next_line)
                    
                    if num_pattern:
                        # Found the numerical data line
                        quantity = int(num_pattern.group(1))
                        backorder = int(num_pattern.group(2))
                        unit_price = float(num_pattern.group(3))
                        extended_price = float(num_pattern.group(4))
                        
                        print(f"[DEBUG] Found numerical data: qty={quantity}, bo={backorder}, unit={unit_price}, ext={extended_price}")
                        break
                    else:
                        # This is part of the description (including serial numbers)
                        # Skip if it's a new part number
                        if not re.match(r'^[A-Z0-9\-\.]{5,}', next_line):
                            description_lines.append(next_line)
                        j += 1
                
                # Combine description lines
                description = " ".join(description_lines).strip()
                
                # If we found numerical data, add the item
                if quantity is not None and unit_price is not None and description:
                    invoice_data["items"].append({
                        "sku": part_number,
                        "upc": "",
                        "name": description,
                        "quantity": quantity,
                        "unit_price": unit_price
                    })
                    print(f"[DEBUG] Parsed item: {part_number} - {description} (Qty: {quantity}, Price: {unit_price})")
                
                # Skip the lines we processed
                i += j
        
        i += 1
    
    print(f"Parsed {len(invoice_data['items'])} items from Quad Source invoice")
    return invoice_data

def parse_quadsource_pdf(pdf_path):
    """
    Parse Quad Source PDF invoice using PyMuPDF for better column structure preservation.
    """
    print(f"[DEBUG] Opening PDF with PyMuPDF: {pdf_path}")
    
    try:
        # Try PyMuPDF first for better column structure
        lines = extract_lines_from_columns(pdf_path)
        full_text = "\n".join(lines)
        print(f"[DEBUG] Extracted {len(full_text)} characters from PDF using PyMuPDF")
        print(f"[DEBUG] Found {len(lines)} structured lines")
        
        # Parse the extracted text
        return parse_quadsource_invoice(full_text)
        
    except Exception as e:
        print(f"[DEBUG] PyMuPDF failed, falling back to pdfplumber: {e}")
        
        # Fallback to pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            full_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        
        print(f"[DEBUG] Extracted {len(full_text)} characters from PDF using pdfplumber")
        
        # Parse the extracted text
        return parse_quadsource_invoice(full_text) 
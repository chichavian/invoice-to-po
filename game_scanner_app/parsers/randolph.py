# parsers/randolph.py
import re

def parse_randolph_invoice(text):
    invoice_data = {
        "distributor": "Groupe Randolph Inc.",
        "invoice_number": None,
        "invoice_date": None,
        "items": []
    }

    # Extract invoice number (Facture: INV/2025/06/1087)
    match = re.search(r"Facture\s*:\s*(INV/\d{4}/\d{2}/\d+)", text)
    if match:
        invoice_data["invoice_number"] = match.group(1)

    # Extract invoice date (Date de la facture: 2025-06-26)
    match = re.search(r"Date de la facture\s*:\s*(\d{4}-\d{2}-\d{2})", text)
    if match:
        invoice_data["invoice_date"] = match.group(1)

    # Find the line items - look for product codes in brackets [LKY AME-R02-FR]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    print(f"[DEBUG] Processing {len(lines)} lines for Randolph invoice")
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for product codes in brackets [CODE] - Randolph uses SKU format like [LKY AME-R02-FR]
        code_match = re.search(r"\[([A-Z0-9\s\-]+)\]", line)
        if code_match:
            try:
                sku = code_match.group(1).strip()  # Remove any extra spaces
                
                # Extract description (everything after the code)
                description = line[code_match.end():].strip()
                
                # Initialize quantity and price
                quantity = 1
                unit_price = 0.0
                
                # Look for quantity in the next line (format: "2,00" or "4,00")
                if i + 1 < len(lines):
                    qty_line = lines[i + 1].strip()
                    qty_match = re.search(r"^(\d+,\d{2})$", qty_line)
                    if qty_match:
                        try:
                            # Convert French decimal format (2,00) to float (2.00)
                            qty_str = qty_match.group(1).replace(',', '.')
                            quantity = float(qty_str)
                            print(f"[DEBUG] Found quantity: {quantity} from line: {qty_line}")
                        except ValueError:
                            print(f"[DEBUG] Could not parse quantity from: {qty_line}")
                
                # Look for unit price in the line after quantity (format: "27,0000" or "72,0000")
                if i + 2 < len(lines):
                    price_line = lines[i + 2].strip()
                    # Look for the first price number in the line (before MSRP)
                    price_match = re.search(r"^(\d+,\d{4})", price_line)
                    if price_match:
                        try:
                            # Convert French decimal format (27,0000) to float (27.00)
                            price_str = price_match.group(1).replace(',', '.')
                            unit_price = float(price_str)
                            print(f"[DEBUG] Found unit price: {unit_price} from line: {price_line}")
                        except ValueError:
                            print(f"[DEBUG] Could not parse price from: {price_line}")
                
                print(f"[DEBUG] Parsed Randolph item: sku={sku}, name={description}, qty={quantity}, price={unit_price}")
                
                # Only add items that have valid SKUs (not delivery fees)
                if sku and not sku.startswith('Frais'):
                    invoice_data["items"].append({
                        "sku": sku,
                        "upc": "",  # Randolph doesn't use UPCs
                        "name": description,
                        "quantity": quantity,
                        "unit_price": unit_price
                    })
                
            except Exception as e:
                print(f"[WARN] Exception parsing Randolph item at line {i}: {e}")
        
        # Stop parsing if we hit summary section
        if "Sous-total" in line or "Total" in line:
            break
            
        i += 1
    
    print(f"[DEBUG] Found {len(invoice_data['items'])} items in Randolph invoice")
    return invoice_data 
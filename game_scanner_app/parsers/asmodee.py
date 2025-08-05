# parsers/asmodee.py
import re

def parse_asmodee_invoice(text):
    invoice_data = {
        "distributor": "Asmodee Canada",
        "invoice_number": None,
        "invoice_date": None,
        "po_number": None,
        "items": []
    }

    # Extract invoice number with fallback pattern
    match = re.search(r"N\s*[°o]*\s*de\s*facture\s*\n?(\S+)", text)
    if match:
        invoice_data["invoice_number"] = match.group(1)

    # Extract invoice date
    match = re.search(r"Date de facture\s*\n?(\d{4}-\d{2}-\d{2})", text)
    if match:
        invoice_data["invoice_date"] = match.group(1)

    # Extract PO number
    match = re.search(r"# de bon de Commande\s*(\S+)", text)
    if match:
        invoice_data["po_number"] = match.group(1)

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        # Look for a line that's just a quantity (number)
        if re.fullmatch(r"\d+", lines[i]):
            try:
                quantity = int(lines[i])
                if i+1 < len(lines) and lines[i+1] == "EA":
                    sku = lines[i+2] if i+2 < len(lines) else ''
                    # Name may be 1 or 2 lines, until we hit a line starting with $
                    name_lines = []
                    for j in range(i+3, min(i+7, len(lines))):
                        if lines[j].startswith("$"):
                            break
                        name_lines.append(lines[j])
                    name = ' '.join(name_lines).replace('  ', ' ').strip()
                    # Find price (first $xx.xx after name)
                    price = 0.0
                    price_idx = None
                    for j in range(i+3+len(name_lines), min(i+10, len(lines))):
                        price_match = re.match(r"\$(\d+\.\d{2})", lines[j])
                        if price_match:
                            price = float(price_match.group(1))
                            price_idx = j
                            break
                    # Find UPC: first 12-13 digit number after price
                    upc = ''
                    for j in range((price_idx+1) if price_idx is not None else (i+3+len(name_lines)), min(i+15, len(lines))):
                        if re.fullmatch(r"\d{12,13}", lines[j]):
                            upc = lines[j]
                            break
                    print(f"[DEBUG] Parsed item: qty={quantity}, sku={sku}, name={name}, price={price}, upc={upc}")
                    invoice_data["items"].append({
                        "sku": sku,
                        "upc": upc,
                        "name": name,
                        "quantity": quantity,
                        "unit_price": price
                    })
                    # Move to line after UPC (or after price if no UPC found)
                    if upc:
                        # Find the index of the UPC line
                        for j in range((price_idx+1) if price_idx is not None else (i+3+len(name_lines)), min(i+15, len(lines))):
                            if lines[j] == upc:
                                i = j + 1
                                break
                        else:
                            i += 1
                    else:
                        i = (price_idx+1) if price_idx is not None else (i+3+len(name_lines))
                    continue
            except Exception as e:
                print(f"[WARN] Exception parsing item at line {i}: {e}")
        i += 1
    return invoice_data

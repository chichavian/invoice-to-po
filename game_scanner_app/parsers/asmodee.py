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

    # Extract product lines using a regex pattern or heuristic
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.search(r"\d+ EA", line):
            try:
                quantity = int(re.search(r"(\d+) EA", line).group(1))
                parts = line.split(" ")
                sku = parts[1]
                name = " ".join(parts[2:]).strip()
                unit_price = float(re.findall(r"\$(\d+\.\d{2})", lines[i + 1])[0])
                upc_match = re.search(r"\d{12,13}", lines[i + 2])
                upc = upc_match.group(0) if upc_match else ""
                invoice_data["items"].append({
                    "sku": sku,
                    "upc": upc,
                    "name": name,
                    "quantity": quantity,
                    "unit_price": unit_price
                })
            except Exception:
                continue

    return invoice_data

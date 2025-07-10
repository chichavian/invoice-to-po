# parsers/universal.py
import re

def parse_universal_invoice(text):
    invoice_data = {
        "distributor": "Universal Distribution",
        "invoice_number": None,
        "invoice_date": None,
        "items": []
    }

    match = re.search(r"Invoice\s*No[:\s]*\n?(SINV-\d+)", text)
    if match:
        invoice_data["invoice_number"] = match.group(1)

    match = re.search(r"Date[:\s]*\n?(\d{4}-\d{2}-\d{2})", text)
    if match:
        invoice_data["invoice_date"] = match.group(1)

    # Regex to extract item blocks
    item_lines = re.findall(r"(\d{12,13})\s+(\S+)\s+([A-Z0-9\-: &'\(\)\[\]/]+.*?)\s+14\.98 UNIT (\d+) \$(\d+\.\d{2}) \$(\d+\.\d{2})", text)

    for upc, sku, name, qty, unit_price, _ in item_lines:
        invoice_data["items"].append({
            "sku": sku,
            "upc": upc,
            "name": name.strip(),
            "quantity": int(qty),
            "unit_price": float(unit_price)
        })

    return invoice_data

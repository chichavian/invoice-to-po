import re

def parse_universal_invoice(text):
    invoice_data = {
        "distributor": "Universal Distribution",
        "invoice_number": re.search(r"Invoice No: (SINV-\d+)", text).group(1),
        "invoice_date": re.search(r"Date: (\d{4}-\d{2}-\d{2})", text).group(1),
        "items": []
    }

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

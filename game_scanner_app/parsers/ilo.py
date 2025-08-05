# parsers/ilo.py
import re

def parse_ilo_invoice(text):
    invoice_data = {
        "distributor": "ÎLO",
        "invoice_number": None,
        "invoice_date": None,
        "po_number": None,
        "items": []
    }

    match = re.search(r"Facture\s*-\s*\n?(FC\d+)", text)
    if match:
        invoice_data["invoice_number"] = match.group(1)

    match = re.search(r"Date\s*\n?(\d{4}-\d{2}-\d{2})", text)
    if match:
        invoice_data["invoice_date"] = match.group(1)

    match = re.search(r"Votre n\xba de commande\s*(\S+)", text)
    if match:
        invoice_data["po_number"] = match.group(1)

    # Updated pattern to capture SKU in bold + game name after it
    item_pattern = re.compile(
        r"(?P<sku>[A-Z0-9\-]+)\s+(?P<name>[A-Za-z0-9 :\-\(\)\[\]\'/éÉèÈàÀêÊçÇ]+)\s+\d+\.\d{2}\s+(?P<ordered>\d+)\s+(?P<shipped>\d+)\s+(?P<backordered>\d+)\s+(?P<unit_price>\d{1,3},\d{2})",
        re.MULTILINE
    )

    for match in item_pattern.finditer(text):
        data = match.groupdict()
        q_ordered = int(data["ordered"])
        q_shipped = int(data["shipped"])
        q_back = int(data["backordered"])

        if q_shipped > 0:
            invoice_data["items"].append({
                "sku": data["sku"],
                "name": data["name"].strip(),
                "quantity_ordered": q_ordered,
                "quantity_shipped": q_shipped,
                "quantity_backordered": q_back,
                "unit_price": float(data["unit_price"].replace(",", "."))
            })

    return invoice_data

import re

def parse_ilo_invoice(text):
    invoice_data = {
        "distributor": "ÎLO",
        "invoice_number": re.search(r"Facture - (FC\d+)", text).group(1),
        "invoice_date": re.search(r"Date (\d{4}-\d{2}-\d{2})", text).group(1),
        "po_number": re.search(r"Votre n\xba de commande (\S+)", text).group(1),
        "items": []
    }

    item_pattern = re.compile(
        r"(\S+)\s+([A-Za-z0-9 :\-\(\)\[\]\'/éÉèÈàÀêÊçÇ]+)\s+\d+\.\d{2}\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d{1,3},\d{2})",
        re.MULTILINE
    )

    for match in item_pattern.finditer(text):
        sku, name, q_ordered, q_shipped, q_back, unit_price = match.groups()
        q_ordered, q_shipped, q_back = int(q_ordered), int(q_shipped), int(q_back)
        if q_shipped > 0:
            invoice_data["items"].append({
                "sku": sku,
                "name": name.strip(),
                "quantity_ordered": q_ordered,
                "quantity_shipped": q_shipped,
                "quantity_backordered": q_back,
                "unit_price": float(unit_price.replace(",", "."))
            })
    return invoice_data

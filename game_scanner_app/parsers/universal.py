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

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    i = 0
    while i < len(lines):
        # Look for a line that is a UPC (12-13 digits)
        if re.fullmatch(r"\d{12,13}", lines[i]):
            try:
                upc = lines[i]
                vendor_no = lines[i+1] if i+1 < len(lines) else ''
                # Name may be 1 or 2 lines, until we hit a line that is a percent or 'UNIT'
                name_lines = []
                for j in range(i+2, min(i+6, len(lines))):
                    if re.fullmatch(r"\d+\.\d{2}", lines[j]) or lines[j] == 'UNIT':
                        break
                    name_lines.append(lines[j])
                name = ' '.join(name_lines).replace('  ', ' ').strip()
                # Find tax, unit, qty, price, total
                idx = i+2+len(name_lines)
                tax = float(lines[idx]) if idx < len(lines) and re.fullmatch(r"\d+\.\d{2}", lines[idx]) else 0.0
                unit = lines[idx+1] if idx+1 < len(lines) else ''
                qty = int(lines[idx+2]) if idx+2 < len(lines) and lines[idx+2].isdigit() else 1
                unit_price = float(lines[idx+3].replace('$','')) if idx+3 < len(lines) and lines[idx+3].startswith('$') else 0.0
                total = float(lines[idx+4].replace('$','')) if idx+4 < len(lines) and lines[idx+4].startswith('$') else 0.0
                print(f"[DEBUG] Parsed item: upc={upc}, vendor_no={vendor_no}, name={name}, qty={qty}, unit_price={unit_price}, total={total}")
                invoice_data["items"].append({
                    "upc": upc,
                    "vendor_no": vendor_no,
                    "name": name,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total": total
                })
                i = idx+5
                continue
            except Exception as e:
                print(f"[WARN] Exception parsing item at line {i}: {e}")
        i += 1
    return invoice_data

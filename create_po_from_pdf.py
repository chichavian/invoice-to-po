import sys
import requests
import json
from game_scanner_app.utils.pdf_extractor import extract_text_from_pdf
from game_scanner_app.parsers.asmodee import parse_asmodee_invoice
from game_scanner_app.parsers.universal import parse_universal_invoice
from game_scanner_app.parsers.ilo import parse_ilo_invoice

# ====== CONFIGURATION ======
ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'
ACCOUNT_ID = '266086'
SHOP_ID = 1  # Hardcoded shop
# ===========================

API_BASE = f'https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}'
headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json',
}

def auto_detect_and_parse(raw_text):
    if "Asmodee Canada" in raw_text:
        print("Asmodee invoice detected")
        return parse_asmodee_invoice(raw_text)
    elif "Invoice No: SINV" in raw_text or "universaldist.com" in raw_text:
        print("Universal Distribution invoice detected")
        return parse_universal_invoice(raw_text)
    elif "ilo307.com" in raw_text or "Île" in raw_text or "ÎLO" in raw_text:
        print("ÎLO invoice detected")
        return parse_ilo_invoice(raw_text)
    else:
        print("Distributor not recognized. Exiting.")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: python create_po_from_pdf.py <invoice.pdf>")
        sys.exit(1)
    pdf_path = sys.argv[1]
    with open(pdf_path, 'rb') as f:
        raw_text = extract_text_from_pdf(f)
    parsed_data = auto_detect_and_parse(raw_text)
    items = parsed_data.get('items', [])
    if not items:
        print("No items found in invoice. Exiting.")
        sys.exit(1)
    print(f"Extracted {len(items)} items from invoice.")
    vendor_id = input("Enter vendor ID for this PO: ").strip()
    if not vendor_id.isdigit():
        print("Invalid vendor ID.")
        sys.exit(1)
    vendor_id = int(vendor_id)
    # Step 1: Create the purchase order
    po_payload = {
        "vendorID": vendor_id,
        "shopID": SHOP_ID,
        "shipCost": 0.0
    }
    order_url = f"{API_BASE}/Order.json"
    order_resp = requests.post(order_url, headers=headers, json=po_payload)
    try:
        order_resp.raise_for_status()
        order_json = order_resp.json()
        print("Raw PO creation response:", order_json)
        if "Order" in order_json:
            print("Purchase Order created:")
            print(json.dumps(order_json["Order"], indent=2))
            order_id = int(order_json["Order"]["orderID"])
        else:
            print("No 'Order' key in response.")
            sys.exit(1)
    except Exception as e:
        print(f"Error creating purchase order: {e}")
        print("Response body:", order_resp.text)
        sys.exit(1)
    # Step 2: Add each item to the purchase order
    for idx, item in enumerate(items):
        print(f"Adding item {idx+1}/{len(items)}: {item}")
        # Try to get itemID, quantity, price from parsed item
        item_id = item.get('itemID') or item.get('id') or item.get('sku') or item.get('upc')
        # You may need to map SKU/UPC to itemID via another API call if not present
        if not str(item_id).isdigit():
            print(f"  Skipping: No valid itemID for item: {item}")
            continue
        quantity = int(item.get('quantity') or item.get('quantity_shipped') or 1)
        price = float(item.get('unit_price') or item.get('price') or 0.0)
        orderline_payload = {
            "quantity": quantity,
            "price": price,
            "originalPrice": price,
            "numReceived": 0,
            "itemID": int(item_id),
            "orderID": order_id
        }
        print("OrderLine payload:", json.dumps(orderline_payload, indent=2))
        orderline_url = f"{API_BASE}/OrderLine.json"
        try:
            orderline_resp = requests.post(orderline_url, headers=headers, json=orderline_payload)
            if orderline_resp.status_code == 200:
                print(f"✅ Item {item_id} added to PO.")
                print(json.dumps(orderline_resp.json(), indent=2))
            else:
                print(f"❌ Failed to add item {item_id}")
                print("Status:", orderline_resp.status_code)
                print("Response:", orderline_resp.text)
        except Exception as e:
            print(f"Error adding item {item_id} to purchase order: {e}")
            print("Response body:", orderline_resp.text)

if __name__ == "__main__":
    main() 
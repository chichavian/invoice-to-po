import os
import requests
import time

# Add rate limiting function
def rate_limit_pause():
    time.sleep(0.5)  # 0.5 seconds between API calls for item creation

def process_missing_items(missing_upcs_file, parsed_items=None, vendor_id=None, ACCOUNT_ID=None, headers=None):
    if not os.path.exists(missing_upcs_file):
        print(f"No missing UPCs file found at {missing_upcs_file}.")
        return
    
    # If no parsed_items provided, we'll work with just the missing items file
    if parsed_items is None:
        parsed_items = []
    
    with open(missing_upcs_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Processing {len(lines)} missing items...")
    
    for line in lines:
        parts = line.strip().split('\t')
        if not parts or not parts[0]:
            continue
        identifier = parts[0]  # Could be UPC or SKU
        name = parts[1] if len(parts) > 1 else ''
        
        # Determine if this is a UPC or SKU based on the identifier
        is_sku = not identifier.isdigit() or len(identifier) < 12  # SKUs are typically not all digits or shorter than UPCs
        
        # Try to find the item in parsed_items for additional details
        scanned_item = None
        if parsed_items:
            for item in parsed_items:
                if is_sku:
                    # For SKU-based items (like Randolph)
                    if str(item.get('sku', '')) == identifier:
                        scanned_item = item
                        break
                else:
                    # For UPC-based items
                    if str(item.get('upc', '')) == identifier:
                        scanned_item = item
                        break
        
        # Use scanned_item details if available, otherwise use basic info
        item_name = scanned_item.get('name', name) if scanned_item else name
        unit_price = scanned_item.get('unit_price', 0.00) if scanned_item else 0.00
        
        # Use defaults and parsed data
        item_payload = {
            "defaultCost": str(unit_price),
            "discountable": True,
            "tax": True,
            "itemType": "default",
            "serialized": False,
            "description": item_name,
            "publishToEcom": False,
            "categoryID": 17,  # Quad Source category
            "taxClassID": 1,
            "defaultVendorID": vendor_id,
            "Prices": {
                "ItemPrice": [
                    {
                        "amount": "0",
                        "useTypeID": 1,
                        "useType": "Default"
                    }
                ]
            },
            "Tags": {
                "Tag": [
                    {"tagID": 8, "name": "New"}
                ]
            }
        }
        
        # Set the appropriate identifier based on type
        if is_sku:
            # For SKU-based items (Randolph), use manufacturerSku
            item_payload["manufacturerSku"] = identifier
            print(f"🔧 Creating item with manufacturerSku: {identifier}")
        else:
            # For UPC-based items, use UPC
            item_payload["upc"] = identifier
            print(f"🔧 Creating item with UPC: {identifier}")
        
        create_item_url = f"https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}/Item.json"
        item_resp = requests.post(create_item_url, json=item_payload, headers=headers)
        if item_resp.status_code != 200:
            print("❌ Failed to create item:", item_resp.status_code, item_resp.text)
            continue
        item_data = item_resp.json()["Item"]
        item_id = item_data["itemID"]
        print(f"✅ Item created: {item_id} — {item_name}")
        # Add rate limiting pause after successful item creation
        rate_limit_pause()
        # --- Tag is now assigned at creation, no further tag logic needed --- 
# app.py
# This CLI-compatible fallback version avoids Streamlit dependency
# Interactive CLI app with menu-based PDF selection
import sys
import os
import requests
import json
from pathlib import Path
from game_scanner_app.utils.pdf_extractor import extract_text_from_pdf
from game_scanner_app.parsers.asmodee import parse_asmodee_invoice
from game_scanner_app.parsers.universal import parse_universal_invoice
from game_scanner_app.parsers.ilo import parse_ilo_invoice
from game_scanner_app.parsers.randolph import parse_randolph_invoice
from game_scanner_app.parsers.quadsource import parse_quadsource_invoice
import time
import subprocess
from process_missing_items import process_missing_items

UPC_CACHE_FILE = 'upc_itemid_map.json'

# Add rate limiting function for purchase order creation
def rate_limit_pause():
    time.sleep(2)  # 2 seconds between API calls when adding items to PO

def merge_items_by_sku(items):
    """
    Merge items with the same SKU by summing their quantities.
    For items with the same SKU, the first item's details are kept and quantities are summed.
    """
    merged_items = {}
    
    for item in items:
        sku = item.get('sku', '').strip()
        upc = item.get('upc', '').strip()
        
        # Use SKU as key if available, otherwise use UPC
        key = sku if sku else upc
        
        if not key:
            # If no SKU or UPC, keep the item as is (can't merge)
            merged_items[f"item_{len(merged_items)}"] = item
            continue
            
        if key in merged_items:
            # Merge with existing item - sum quantities
            existing_item = merged_items[key]
            existing_qty = existing_item.get('quantity', 1)
            new_qty = item.get('quantity', 1)
            merged_items[key]['quantity'] = existing_qty + new_qty
            
            print(f"[DEBUG] Merged {key}: {existing_qty} + {new_qty} = {existing_qty + new_qty}")
        else:
            # First occurrence of this SKU/UPC
            merged_items[key] = item.copy()
    
    return list(merged_items.values())

# ====== CONFIGURATION ======
ACCESS_TOKEN = '36126d0fa8fa67c1023b13be88d0ee03491589da'  # <-- Replace with your valid token
ACCOUNT_ID = '266086'
SHOP_ID = 1  # Hardcoded shop
CLIENT_ID = '47337600c27c58b94a523b4b70b82ed6ea4fe62b4e1afc094bb1b24de8d37234'  # Fill in your Lightspeed client_id
CLIENT_SECRET = '9d6986c05fd287c007e2795818484ed2855de264128af4526071a2a64e21987b'  # Fill in your Lightspeed client_secret
# ===========================

API_BASE = f'https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}'
headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json',
}

# Ensure current working directory is in sys.path to allow relative imports
# Ensure local imports work
current_dir = Path(__file__).parent if '__file__' in globals() else Path().resolve()
sys.path.append(str(current_dir))

def list_pdf_files(folder):
    return sorted([f for f in os.listdir(folder) if f.lower().endswith('.pdf')])

def choose_file_menu(pdf_files):
    print("\nAvailable Invoices:\n")
    for idx, fname in enumerate(pdf_files, start=1):
        print(f"[{idx}] {fname}")
    while True:
        try:
            choice = int(input(f"\nChoose a file [1-{len(pdf_files)}]: "))
            if 1 <= choice <= len(pdf_files):
                return pdf_files[choice - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")

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
    elif "Groupe Randolph" in raw_text or "Randolph" in raw_text:
        print("Randolph invoice detected")
        return parse_randolph_invoice(raw_text)
    elif "Quad Source" in raw_text or "QUAD SOURCE" in raw_text:
        print("Quad Source invoice detected")
        return parse_quadsource_invoice(raw_text)
    else:
        print("Distributor not recognized. Exiting.")
        sys.exit(1)

def fetch_item_by_upc(access_token, upc):
    url = f"https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}/Item.json"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'upc': upc}
    resp = requests.get(url, headers=headers, params=params)
    try:
        resp.raise_for_status()
    except Exception as e:
        print(f"[UPC Lookup] Error for UPC {upc}: {e}")
        print("Response body:", resp.text)
        return []
    data = resp.json()
    items = data.get("Item", [])
    if isinstance(items, dict):  # Only one item found
        items = [items]
    return items

def load_upc_cache():
    try:
        with open(UPC_CACHE_FILE, 'r') as f:
            upc_cache = json.load(f)
        print(f"Loaded {len(upc_cache)} UPC→itemID mappings from {UPC_CACHE_FILE}")
        return upc_cache
    except Exception as e:
        print(f"[INFO] UPC cache file '{UPC_CACHE_FILE}' not found. Building cache...")
        try:
            result = subprocess.run(['python', 'build_upc_cache.py'], check=True)
            with open(UPC_CACHE_FILE, 'r') as f:
                upc_cache = json.load(f)
            print(f"Loaded {len(upc_cache)} UPC→itemID mappings from {UPC_CACHE_FILE}")
            return upc_cache
        except Exception as e2:
            print(f"[ERROR] Could not build UPC cache: {e2}")
            return None

def find_item_id(item, upc_cache):
    """Find item ID by UPC or manufacturer SKU, prioritizing UPC.
    
    Args:
        item: Item dictionary with upc and/or sku
        upc_cache: UPC to item details mapping (contains both UPC and SKU data)
    """
    upc = str(item.get('upc', '')).strip()
    sku = str(item.get('sku', '')).strip()
    
    # First, try UPC lookup if available
    if upc:
        if upc in upc_cache:
            return upc_cache[upc]['itemID'], 'upc'
        else:
            return None, 'upc'
    
    # If no UPC, try SKU lookup
    if sku:
        print(f"[DEBUG] Looking for SKU: {sku}")
        # Search through UPC cache for matching manufacturer SKU
        for cache_key, item_data in upc_cache.items():
            if isinstance(item_data, dict):
                manufacturer_sku = item_data.get('manufacturerSKU', '')
                custom_sku = item_data.get('sku', '')
                
                if manufacturer_sku == sku:
                    print(f"[DEBUG] Found match in manufacturerSKU: {sku} -> itemID {item_data.get('itemID')}")
                    return item_data['itemID'], 'sku'
                elif custom_sku == sku:
                    print(f"[DEBUG] Found match in customSku: {sku} -> itemID {item_data.get('itemID')}")
                    return item_data['itemID'], 'sku'
        
        print(f"[DEBUG] No match found for SKU: {sku}")
        return None, 'sku'
    
    return None, None

def refresh_token():
    # Try to refresh the token using lightspeed_tokens.json
    try:
        with open('lightspeed_tokens.json', 'r') as f:
            tokens = json.load(f)
        refresh = tokens.get('refresh_token')
        if not refresh:
            print('[ERROR] No refresh token available.')
            return None
        if not CLIENT_ID or not CLIENT_SECRET:
            print('[ERROR] CLIENT_ID and CLIENT_SECRET must be set in the config.')
            return None
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh,
        }
        resp = requests.post('https://cloud.lightspeedapp.com/oauth/access_token.php', data=data)
        resp.raise_for_status()
        new_tokens = resp.json()
        with open('lightspeed_tokens.json', 'w') as f:
            json.dump(new_tokens, f)
        print('[INFO] Access token refreshed.')
        return new_tokens['access_token']
    except Exception as e:
        print(f'[ERROR] Failed to refresh token: {e}')
        return None

def main_menu():
    while True:
        print("\nWhat would you like to do?")
        print("[1] Process a new invoice (parse PDF, create PO, etc.)")
        print("[2] Process a folder of invoices (all from same vendor)")
        print("[3] Process missing items in Lightspeed")
        print("[4] Build or refresh UPC cache")
        print("[5] Exit")
        choice = input("Enter your choice [1-5]: ").strip()
        if choice == '1':
            process_invoice_workflow()
        elif choice == '2':
            process_folder_workflow()
        elif choice == '3':
            print("\nProcess Missing Items Options:")
            print("[1] Process missing items with invoice reference (for additional details)")
            print("[2] Process missing items directly from file")
            print("[3] Process missing items using all invoices from a folder")
            sub_choice = input("Enter your choice [1-3]: ").strip()
            
            vendor_id = input("Enter vendor ID for missing items: ").strip()
            if not vendor_id.isdigit():
                print("Invalid vendor ID.")
                continue
            vendor_id = int(vendor_id)
            
            if sub_choice == '1':
                # Try to load parsed items from last invoice (if available)
                folder = "invoices"
                os.makedirs(folder, exist_ok=True)
                pdf_files = list_pdf_files(folder)
                if not pdf_files:
                    print("[ERROR] No PDF files found in 'invoices/' folder.")
                    continue
                selected_file = choose_file_menu(pdf_files)
                pdf_path = os.path.join(folder, selected_file)
                with open(pdf_path, "rb") as f:
                    raw_text = extract_text_from_pdf(f)
                parsed_data = auto_detect_and_parse(raw_text)
                items = parsed_data.get('items', []) if isinstance(parsed_data, dict) else []
                process_missing_items('missing_upcs.txt', items, vendor_id, ACCOUNT_ID, headers)
            elif sub_choice == '2':
                # Process missing items directly from file
                process_missing_items('missing_upcs.txt', vendor_id=vendor_id, ACCOUNT_ID=ACCOUNT_ID, headers=headers)
            elif sub_choice == '3':
                # Process missing items using all invoices from a folder
                folder = "invoices"
                os.makedirs(folder, exist_ok=True)
                folders = list_folders(folder)
                if not folders:
                    print("[ERROR] No folders found in 'invoices/' directory.")
                    continue
                selected_folder = choose_folder_menu(folders)
                folder_path = os.path.join(folder, selected_folder)
                pdf_files = list_pdf_files(folder_path)
                if not pdf_files:
                    print(f"[ERROR] No PDF files found in '{selected_folder}' folder.")
                    continue
                
                print(f"Parsing {len(pdf_files)} invoices from '{selected_folder}' folder...")
                all_items = []
                for pdf_file in pdf_files:
                    pdf_path = os.path.join(folder_path, pdf_file)
                    try:
                        with open(pdf_path, "rb") as f:
                            raw_text = extract_text_from_pdf(f)
                        parsed_data = auto_detect_and_parse(raw_text)
                        items = parsed_data.get('items', []) if isinstance(parsed_data, dict) else []
                        all_items.extend(items)
                        print(f"  ✓ Parsed {pdf_file}: {len(items)} items")
                    except Exception as e:
                        print(f"  ✗ Error parsing {pdf_file}: {e}")
                
                print(f"Total items found: {len(all_items)}")
                process_missing_items('missing_upcs.txt', all_items, vendor_id, ACCOUNT_ID, headers)
            else:
                print("Invalid choice.")
        elif choice == '4':
            print("Building or refreshing UPC cache...")
            try:
                subprocess.run(['python', 'build_upc_cache.py'], check=True)
                print("UPC cache built/refreshed.")
            except Exception as e:
                print(f"[ERROR] Could not build UPC cache: {e}")
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1, 2, 3, 4, or 5.")

def list_folders(base_folder):
    """List all folders in the base folder that contain PDF files."""
    folders = []
    if not os.path.exists(base_folder):
        return folders
    
    for item in os.listdir(base_folder):
        item_path = os.path.join(base_folder, item)
        if os.path.isdir(item_path):
            # Check if folder contains PDF files
            pdf_files = list_pdf_files(item_path)
            if pdf_files:
                folders.append(item)
    return sorted(folders)

def choose_folder_menu(folders):
    print("\nAvailable Invoice Folders:\n")
    for idx, folder_name in enumerate(folders, start=1):
        pdf_count = len(list_pdf_files(os.path.join("invoices", folder_name)))
        print(f"[{idx}] {folder_name} ({pdf_count} PDF files)")
    while True:
        try:
            choice = int(input(f"\nChoose a folder [1-{len(folders)}]: "))
            if 1 <= choice <= len(folders):
                return folders[choice - 1]
        except ValueError:
            pass
        print("Invalid choice. Try again.")

def process_folder_workflow():
    """Process all invoices in a selected folder with the same vendor ID."""
    # Check API connectivity and token validity
    shop_url = f"{API_BASE}/Shop.json"
    try:
        resp = requests.get(shop_url, headers=headers)
        resp.raise_for_status()
        shop_data = resp.json()
        shop_info = shop_data.get('Shop')
        if shop_info:
            print(f"[API OK] Connected to shop: {shop_info.get('name', 'Unknown')} (ID: {shop_info.get('shopID', 'N/A')})")
        else:
            print("[WARN] Shop details response did not contain 'Shop' key.")
    except Exception as e:
        print(f"[FATAL] Could not connect to Lightspeed API or invalid token: {e}")
        if 'resp' in locals():
            print('Response:', resp.text)
        sys.exit(1)
    
    # Load UPC cache (contains both UPC and SKU data)
    upc_cache = load_upc_cache()
    if upc_cache is None:
        print("[ERROR] Could not load or build UPC cache. Exiting.")
        return
    
    # List available folders
    base_folder = "invoices"
    os.makedirs(base_folder, exist_ok=True)
    folders = list_folders(base_folder)
    
    if not folders:
        print("[ERROR] No folders with PDF files found in 'invoices/' folder.")
        return
    
    selected_folder = choose_folder_menu(folders)
    folder_path = os.path.join(base_folder, selected_folder)
    pdf_files = list_pdf_files(folder_path)
    
    print(f"\nProcessing folder: {selected_folder}")
    print(f"Found {len(pdf_files)} PDF files")
    
    # Get vendor ID for all invoices in this folder
    vendor_id = input("Enter vendor ID for all invoices in this folder: ").strip()
    if not vendor_id.isdigit():
        print("Invalid vendor ID.")
        return
    vendor_id = int(vendor_id)
    
    # Collect all items from all invoices
    all_items = []
    all_invoice_data = []
    
    print(f"\nProcessing {len(pdf_files)} invoices...")
    for i, pdf_file in enumerate(pdf_files, 1):
        pdf_path = os.path.join(folder_path, pdf_file)
        print(f"\n[{i}/{len(pdf_files)}] Processing: {pdf_file}")
        
        try:
            with open(pdf_path, "rb") as f:
                raw_text = extract_text_from_pdf(f)
            
            parsed_data = auto_detect_and_parse(raw_text)
            items = parsed_data.get('items', []) if isinstance(parsed_data, dict) else []
            
            if items:
                all_items.extend(items)
                all_invoice_data.append({
                    'file': pdf_file,
                    'data': parsed_data,
                    'items': items
                })
                print(f"  ✓ Extracted {len(items)} items")
            else:
                print(f"  ⚠ No items found in {pdf_file}")
                
        except Exception as e:
            print(f"  ❌ Error processing {pdf_file}: {e}")
            continue
    
    if not all_items:
        print("No items found in any invoice. Exiting.")
        return
    
    print(f"\nTotal items collected: {len(all_items)}")
    
    # Merge items with the same SKU
    merged_items = merge_items_by_sku(all_items)
    print(f"\nMerged {len(all_items)} items down to {len(merged_items)} unique items by SKU.")
    
    # Handle missing_upcs.txt overwrite logic
    missing_upcs_file = 'missing_upcs.txt'
    if os.path.exists(missing_upcs_file):
        resp = input(f"{missing_upcs_file} already exists. Overwrite with new missing items? (y/n): ").strip().lower()
        if resp == 'y':
            open(missing_upcs_file, 'w', encoding='utf-8').close()  # Clear file
            print(f"{missing_upcs_file} cleared.")
        else:
            print(f"Appending new missing items to {missing_upcs_file}.")
    
    # Create purchase order
    po_payload = {
        "vendorID": vendor_id,
        "shopID": SHOP_ID,
        "shipCost": 0.0
    }
    
    # Add folder name as reference
    po_payload["reference"] = f"Folder: {selected_folder}"
    
    order_url = f"{API_BASE}/Order.json"
    
    # Automatic token refresh logic for PO creation
    global ACCESS_TOKEN
    for attempt in range(2):
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
        order_resp = requests.post(order_url, headers=headers, json=po_payload)
        if order_resp.status_code == 401:
            print("[WARN] 401 Unauthorized when creating PO. Attempting token refresh...")
            new_token = refresh_token()
            if new_token:
                ACCESS_TOKEN = new_token
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                continue
            else:
                print("[ERROR] Could not refresh token. Exiting.")
                return
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
                return
            break
        except Exception as e:
            print(f"Error creating purchase order: {e}")
            print("Response body:", order_resp.text)
            return
    else:
        print("[ERROR] Failed to create PO after token refresh attempts.")
        return
    
    # Add all items to the purchase order
    any_missing = False
    for idx, item in enumerate(merged_items):
        print(f"\nProcessing item {idx + 1}/{len(merged_items)}: {item.get('name', 'Unknown')}")
        
        # Find item ID using UPC or SKU
        item_id, lookup_type = find_item_id(item, upc_cache)
        
        if item_id:
            identifier = item.get('upc', '') if lookup_type == 'upc' else item.get('sku', '')
            print(f"  ✓ Found existing item (ID: {item_id}) for {lookup_type.upper()}: {identifier}")
        else:
            identifier = item.get('upc', '') if lookup_type == 'upc' else item.get('sku', '')
            print(f"  ❌ Item not found in Lightspeed for {lookup_type.upper()}: {identifier}")
            any_missing = True
            # Add to missing items file
            with open(missing_upcs_file, 'a', encoding='utf-8') as f:
                f.write(f"{identifier}\t{item.get('name', 'Unknown')}\n")
            continue
        
        # Add item to purchase order
        order_line_payload = {
            "itemID": item_id,
            "quantity": item.get('quantity', 1),
            "price": item.get('unit_price', 0.0),
            "originalPrice": item.get('unit_price', 0.0),
            "numReceived": 0,
            "orderID": order_id
        }
        
        order_line_url = f"{API_BASE}/OrderLine.json"
        
        # Token refresh logic for order line creation
        for attempt in range(2):
            headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
            line_resp = requests.post(order_line_url, headers=headers, json=order_line_payload)
            if line_resp.status_code == 401:
                print("  [WARN] 401 Unauthorized when adding item to PO. Attempting token refresh...")
                new_token = refresh_token()
                if new_token:
                    ACCESS_TOKEN = new_token
                    headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                    continue
                else:
                    print("  [ERROR] Could not refresh token. Skipping item.")
                    break
            try:
                line_resp.raise_for_status()
                print(f"  ✓ Added to PO: {item.get('name', 'Unknown')} (Qty: {item.get('quantity', 1)})")
                # Add rate limiting pause after successful API call
                rate_limit_pause()
                break
            except Exception as e:
                print(f"  ❌ Error adding item to PO: {e}")
                print("  Response body:", line_resp.text)
                break
        else:
            print("  [ERROR] Failed to add item to PO after token refresh attempts.")
    
    if any_missing:
        print(f"\n⚠ Some items were not found in Lightspeed and have been added to {missing_upcs_file}")
        print("You can process these missing items later using option 2.")
    else:
        print(f"\n✅ All {len(merged_items)} items were successfully added to the purchase order!")
    
    print(f"\nPurchase Order Summary:")
    print(f"  Order ID: {order_id}")
    print(f"  Vendor ID: {vendor_id}")
    print(f"  Folder: {selected_folder}")
    print(f"  Total Items: {len(merged_items)}")
    print(f"  Invoices Processed: {len(all_invoice_data)}")

def process_invoice_workflow():
    # Check API connectivity and token validity by requesting shop details
    shop_url = f"{API_BASE}/Shop.json"
    try:
        resp = requests.get(shop_url, headers=headers)
        resp.raise_for_status()
        shop_data = resp.json()
        shop_info = shop_data.get('Shop')
        if shop_info:
            print(f"[API OK] Connected to shop: {shop_info.get('name', 'Unknown')} (ID: {shop_info.get('shopID', 'N/A')})")
        else:
            print("[WARN] Shop details response did not contain 'Shop' key.")
    except Exception as e:
        print(f"[FATAL] Could not connect to Lightspeed API or invalid token: {e}")
        if 'resp' in locals():
            print('Response:', resp.text)
        sys.exit(1)
    # Load UPC cache (contains both UPC and SKU data)
    upc_cache = load_upc_cache()
    if upc_cache is None:
        print("[ERROR] Could not load or build UPC cache. Exiting.")
        return
    prompted_upcs = set()
    folder = "invoices"
    os.makedirs(folder, exist_ok=True)
    pdf_files = list_pdf_files(folder)
    if not pdf_files:
        print("[ERROR] No PDF files found in 'invoices/' folder.")
        return
    selected_file = choose_file_menu(pdf_files)
    pdf_path = os.path.join(folder, selected_file)
    with open(pdf_path, "rb") as f:
        raw_text = extract_text_from_pdf(f)
    print("\n--- RAW TEXT PREVIEW ---\n")
    print(raw_text[:1000])
    parsed_data = auto_detect_and_parse(raw_text)
    items = parsed_data.get('items', []) if isinstance(parsed_data, dict) else []
    if not items:
        print("No items found in invoice. Exiting.")
        return
    print(f"Extracted {len(items)} items from invoice.")
    vendor_id = input("Enter vendor ID for this PO: ").strip()
    if not vendor_id.isdigit():
        print("Invalid vendor ID.")
        return
    vendor_id = int(vendor_id)

    # --- Handle missing_upcs.txt overwrite logic ---
    missing_upcs_file = 'missing_upcs.txt'
    missing_this_run = set()
    print(f"[DEBUG] Missing items file path: {os.path.abspath(missing_upcs_file)}")
    if os.path.exists(missing_upcs_file):
        resp = input(f"{missing_upcs_file} already exists. Overwrite with new missing items? (y/n): ").strip().lower()
        if resp == 'y':
            open(missing_upcs_file, 'w', encoding='utf-8').close()  # Clear file
            print(f"{missing_upcs_file} cleared.")
        else:
            print(f"Appending new missing items to {missing_upcs_file}.")

    # Step 1: Create the purchase order
    po_payload = {
        "vendorID": vendor_id,
        "shopID": SHOP_ID,
        "shipCost": 0.0
    }
    # Add invoice number and date if available
    if isinstance(parsed_data, dict):
        invoice_number = parsed_data.get('invoice_number')
        invoice_date = parsed_data.get('invoice_date')
    else:
        invoice_number = None
        invoice_date = None
    if invoice_number:
        po_payload["reference"] = invoice_number
    if invoice_date:
        po_payload["dateReceived"] = invoice_date
    order_url = f"{API_BASE}/Order.json"
    # --- Automatic token refresh logic for PO creation ---
    global ACCESS_TOKEN
    for attempt in range(2):
        headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
        order_resp = requests.post(order_url, headers=headers, json=po_payload)
        if order_resp.status_code == 401:
            print("[WARN] 401 Unauthorized when creating PO. Attempting token refresh...")
            new_token = refresh_token()
            if new_token:
                ACCESS_TOKEN = new_token
                headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                continue
            else:
                print("[ERROR] Could not refresh token. Exiting.")
                return
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
                return
            break
        except Exception as e:
            print(f"Error creating purchase order: {e}")
            print("Response body:", order_resp.text)
            return
    else:
        print("[ERROR] Failed to create PO after token refresh attempts.")
        return
    # Step 2: Add each item to the purchase order
    any_missing = False
    items_found_count = 0
    items_missing_count = 0
    
    for idx, item in enumerate(items):
        print(f"Adding item {idx+1}/{len(items)}: {item}")
        item_id = item.get('itemID') or item.get('id')
        item_details = None
        missing_identifier = False
        missing_identifier_val = None
        missing_name_val = None
        
        # If no itemID, try to look up by UPC or SKU in local cache
        if not item_id:
            # Find item ID using UPC or SKU
            item_id, lookup_type = find_item_id(item, upc_cache)
            
            if item_id:
                identifier = item.get('upc', '') if lookup_type == 'upc' else item.get('sku', '')
                print(f"  Found itemID {item_id} for {lookup_type.upper()} {identifier} (from cache)")
            else:
                identifier = item.get('upc', '') or item.get('sku', '')
                name = item.get('name') or item.get('description') or ''
                print(f"  Skipping: No valid item details for {lookup_type.upper()} {identifier} in cache.")
                missing_identifier = True
                missing_identifier_val = identifier
                missing_name_val = name
                any_missing = True
                items_missing_count += 1
                # Add to missing items file with debug output
                print(f"  [DEBUG] Writing missing item to {missing_upcs_file}: {identifier}\t{name}")
                with open(missing_upcs_file, 'a', encoding='utf-8') as f:
                    f.write(f"{identifier}\t{name}\n")
                continue
        else:
            # Item already has itemID, use it directly
            identifier = item.get('upc', '') or item.get('sku', '')
            lookup_type = 'upc' if item.get('upc') else 'sku'
        
        # Handle missing items
        if missing_identifier:
            if identifier not in prompted_upcs:
                # Save to missing_upcs.txt before prompting
                if identifier not in missing_this_run:
                    print(f"  [DEBUG] Writing missing item to {missing_upcs_file}: {identifier}\t{missing_name_val}")
                    with open(missing_upcs_file, 'a', encoding='utf-8') as f:
                        f.write(f"{identifier}\t{missing_name_val}\n")
                    missing_this_run.add(identifier)
                resp = input(f"{lookup_type.upper()} {identifier} ({missing_name_val}) not found in cache. Refresh cache and retry? (y/n): ").strip().lower()
                prompted_upcs.add(identifier)
                if resp == 'y':
                    upc_cache = load_upc_cache()
                    if upc_cache is not None:
                        # Try lookup again after cache refresh
                        item_id, lookup_type = find_item_id(item, upc_cache)
                        if item_id:
                            identifier = item.get('upc', '') if lookup_type == 'upc' else item.get('sku', '')
                            print(f"  Found itemID {item_id} for {lookup_type.upper()} {identifier} (after cache refresh)")
                        else:
                            print(f"  Skipping: No valid item details for {lookup_type.upper()} {identifier} after refresh.")
                            continue
                    else:
                        print("  Skipping: Could not refresh cache.")
                        continue
                else:
                    continue

        # Add item to purchase order
        order_line_payload = {
            "itemID": item_id,
            "quantity": item.get('quantity', 1),
            "price": item.get('unit_price', 0.0),
            "originalPrice": item.get('unit_price', 0.0),
            "numReceived": 0,
            "orderID": order_id
        }
        
        order_line_url = f"{API_BASE}/OrderLine.json"
        
        # Token refresh logic for order line creation
        for attempt in range(2):
            headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
            line_resp = requests.post(order_line_url, headers=headers, json=order_line_payload)
            if line_resp.status_code == 401:
                print("  [WARN] 401 Unauthorized when adding item to PO. Attempting token refresh...")
                new_token = refresh_token()
                if new_token:
                    ACCESS_TOKEN = new_token
                    headers["Authorization"] = f"Bearer {ACCESS_TOKEN}"
                    continue
                else:
                    print("  [ERROR] Could not refresh token. Skipping item.")
                    break
            try:
                line_resp.raise_for_status()
                print(f"  ✓ Added to PO: {item.get('name', 'Unknown')} (Qty: {item.get('quantity', 1)})")
                items_found_count += 1
                # Add rate limiting pause after successful API call
                rate_limit_pause()
                break
            except Exception as e:
                print(f"  ❌ Error adding item to PO: {e}")
                print("  Response body:", line_resp.text)
                break
        else:
            print("  [ERROR] Failed to add item to PO after token refresh attempts.")
    
    if any_missing:
        print(f"\n⚠ {items_missing_count} items were not found in Lightspeed and have been added to {missing_upcs_file}")
        print("You can process these missing items later using option 3.")
    else:
        print(f"\n✅ All {len(items)} items were successfully added to the purchase order!")
    
    print(f"\nPurchase Order Summary:")
    print(f"  Order ID: {order_id}")
    print(f"  Vendor ID: {vendor_id}")
    print(f"  Items Added to PO: {items_found_count}")
    print(f"  Items Not Found: {items_missing_count}")
    print(f"  Total Items Processed: {len(items)}")

if __name__ == "__main__":
    main_menu()
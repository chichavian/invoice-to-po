import requests
import json
import time
import os
import shutil
from datetime import datetime
from app import ACCESS_TOKEN, ACCOUNT_ID, headers

# Add rate limiting function
def rate_limit_pause():
    time.sleep(0.5)  # 0.2 seconds between API calls for cache building

# ====== CONFIGURATION ======
# Remove the local ACCESS_TOKEN, ACCOUNT_ID, API_BASE, and headers definitions
# ===========================

CACHE_FILE = 'upc_itemid_map.json'
PAGE_SIZE = 100
DELAY_BETWEEN_REQUESTS = 0.2  # seconds
MAX_RETRIES_ON_429 = 3
BACKOFF_ON_429 = 2.0  # seconds

# Try to load access token from lightspeed_tokens.json if ACCESS_TOKEN is not set
if ACCESS_TOKEN == 'YOUR_ACCESS_TOKEN' or not ACCESS_TOKEN:
    if os.path.exists('lightspeed_tokens.json'):
        with open('lightspeed_tokens.json', 'r') as f:
            tokens = json.load(f)
            ACCESS_TOKEN = tokens.get('access_token')
            headers['Authorization'] = f'Bearer {ACCESS_TOKEN}'
        print('[INFO] Loaded access token from lightspeed_tokens.json')
    else:
        print('[ERROR] No valid ACCESS_TOKEN set and lightspeed_tokens.json not found!')
        exit(1)

def extract_price(item):
    # Try top-level price
    price = item.get('price')
    if price is not None:
        return price
    # Try ItemShops/ItemShop
    itemshops = item.get('ItemShops', {}).get('ItemShop')
    if isinstance(itemshops, dict):
        return itemshops.get('price')
    elif isinstance(itemshops, list) and itemshops:
        return itemshops[0].get('price')
    return None

def extract_tags(item):
    tags = []
    tags_obj = item.get('Tags', {}).get('Tag')
    if isinstance(tags_obj, dict):
        tags.append(tags_obj.get('name'))
    elif isinstance(tags_obj, list):
        for tag in tags_obj:
            tags.append(tag.get('name'))
    return tags if tags else None

def main():
    # Ask user if they want debug mode
    print("UPC Cache Builder")
    print("Debug mode will show field details for the first few items only.")
    debug_mode = input("Run in debug mode? (y/n): ").strip().lower() == 'y'
    
    if debug_mode:
        print("Running in DEBUG mode - will show field details for first few items only")
    else:
        print("Running in NORMAL mode - processing all items")
    
    upc_map = fetch_all_items(debug_mode)
    print(f"Fetched {len(upc_map)} items with UPCs.")
    # Backup existing cache file if it exists
    if os.path.exists(CACHE_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f"upc_itemid_map_backup_{timestamp}.json"
        shutil.copy2(CACHE_FILE, backup_file)
        print(f"Backup of previous cache saved as {backup_file}")
    with open(CACHE_FILE, 'w') as f:
        json.dump(upc_map, f, indent=2)
    print(f"UPC→item details map saved to {CACHE_FILE}")

    # Compare with previous cache (if backup exists)
    prev_cache_file = CACHE_FILE + '.bak'
    if os.path.exists(prev_cache_file):
        with open(prev_cache_file, 'r', encoding='utf-8') as f:
            prev_cache = json.load(f)
        prev_upcs = set(prev_cache.keys())
        new_upcs = set(upc_map.keys())
        new_entries = new_upcs - prev_upcs
        print(f"[INFO] {len(new_entries)} new UPC entries added compared to previous cache.")
    else:
        print("[INFO] No previous cache to compare for new entries.")

def fetch_all_items(debug_mode=False):
    upc_map = {}
    url = f"https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}/Item.json?limit={PAGE_SIZE}"
    total = None
    page = 1
    print('Fetching items from Lightspeed...')
    while url:
        retries = 0
        while retries <= MAX_RETRIES_ON_429:
            resp = requests.get(url, headers=headers)
            if resp.status_code == 429:
                print(f"[WARN] 429 Too Many Requests on page {page}. Backing off for {BACKOFF_ON_429} seconds (retry {retries+1}/{MAX_RETRIES_ON_429})...")
                time.sleep(BACKOFF_ON_429)
                retries += 1
                continue
            try:
                resp.raise_for_status()
            except Exception as e:
                print(f"Error fetching items on page {page}: {e}")
                print("Response body:", resp.text)
                return upc_map
            break  # Success, exit retry loop
        else:
            print(f"[ERROR] Too many 429 errors on page {page}. Aborting.")
            return upc_map
        data = resp.json()
        items = data.get('Item', [])
        if isinstance(items, dict):
            items = [items]
        for item in items:
            upc = item.get('upc')
            item_id = item.get('itemID')
            price = extract_price(item)
            tags = extract_tags(item)
            
            # Debug: Show available fields for first few items (only in debug mode)
            if debug_mode and len(upc_map) < 3:
                print(f"[DEBUG] Item {item_id} available fields:")
                for key, value in item.items():
                    print(f"  {key}: {value}")
                print("---")
            
            if not debug_mode:
                print(f"Fetched itemID={item_id}, UPC={upc}, Description={item.get('description')}, Price={price}, Tags={tags}")
            
            if item_id:  # Only require itemID, UPC is optional
                # Create item data
                item_data = {
                    'itemID': item_id,
                    'description': item.get('description'),
                    'sku': item.get('customSku') or item.get('systemSku'),
                    'price': price,
                    'manufacturerSKU': item.get('manufacturerSku'),
                    'defaultCost': item.get('defaultCost'),
                    'archived': item.get('archived'),
                    'categoryID': item.get('categoryID'),
                    'tag': tags,
                    # Add more fields as needed
                }
                
                # Store item using UPC as key if available, otherwise use itemID
                if upc:
                    upc_map[upc] = item_data
                    if not debug_mode:
                        print(f"  ✓ Stored item {item_id} with UPC {upc}")
                else:
                    # For items without UPC, use itemID as key with a prefix to distinguish from UPCs
                    item_key = f"ITEM_{item_id}"
                    upc_map[item_key] = item_data
                    if not debug_mode:
                        print(f"  ✓ Stored item {item_id} without UPC using key {item_key}")
                
                # Debug: Show what we're storing for manufacturerSKU (only in debug mode)
                if debug_mode and len(upc_map) < 3:
                    print(f"[DEBUG] Stored manufacturerSKU: {item.get('manufacturerSku')}")
            else:
                if not debug_mode:
                    print(f"[WARN] Skipping item with no itemID")
        
        # In debug mode, stop after first page
        if debug_mode:
            print(f"[DEBUG] Stopping after first page in debug mode. Found {len(upc_map)} items.")
            break
            
        if total is None:
            total = int(data.get('@attributes', {}).get('count', 0))
            print(f"Total items to fetch: {total}")
        print(f"Fetched page {page}...")
        # Pagination: use @attributes['next'] if present
        next_url = data.get('@attributes', {}).get('next')
        url = next_url if next_url else None
        page += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)  # Be nice to the API
    return upc_map

if __name__ == '__main__':
    main() 
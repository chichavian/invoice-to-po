import requests
import webbrowser
import json

# ====== USER: FILL THESE IN ======
CLIENT_ID = '47337600c27c58b94a523b4b70b82ed6ea4fe62b4e1afc094bb1b24de8d37234'
CLIENT_SECRET = '9d6986c05fd287c007e2795818484ed2855de264128af4526071a2a64e21987b'
REDIRECT_URI = 'YOUR_REGISTERED_REDIRECT_URI'  # Fill in your actual redirect URI
ACCOUNT_ID = '266086'
LS_REFRESH_TOKEN = 'c4ad8e292664b8bd687a30298009051dc5b37925'  # Optional: use if you have one
# =================================

# Lightspeed OAuth endpoints
AUTH_URL = 'https://cloud.lightspeedapp.com/oauth/authorize.php'
TOKEN_URL = 'https://cloud.lightspeedapp.com/oauth/access_token.php'
API_BASE = 'https://api.lightspeedapp.com/API/V3'

# Step 1: Get authorization code (manual, one-time)
def get_authorization_code():
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'employee:all inventory:all',  # Adjust scopes as needed
    }
    url = AUTH_URL + '?' + '&'.join(f"{k}={v}" for k, v in params.items())
    print(f"Go to this URL and authorize the app:\n{url}")
    webbrowser.open(url)
    code = input('Paste the authorization code here: ')
    return code.strip()

# Step 2: Exchange code for access token
def get_tokens(auth_code):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code',
        'code': auth_code,
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()

# Step 3: Refresh access token
def refresh_token(refresh_token):
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    resp = requests.post(TOKEN_URL, data=data)
    resp.raise_for_status()
    return resp.json()

# Step 4: Fetch product details
def fetch_item(access_token, item_id):
    url = f"{API_BASE}/Account/{ACCOUNT_ID}/Item/{item_id}.json"
    headers = {'Authorization': f'Bearer {access_token}'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

# Step 5: Update product quantity
def update_item_quantity(access_token, item_id, new_qty):
    url = f"{API_BASE}/Account/{ACCOUNT_ID}/Item/{item_id}.json"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    data = {
        "Item": {
            "qoh": new_qty  # Quantity on hand
        }
    }
    resp = requests.put(url, headers=headers, data=json.dumps(data))
    resp.raise_for_status()
    return resp.json()

def fetch_item_by_upc(access_token, upc):
    url = f"{API_BASE}/Account/{ACCOUNT_ID}/Item.json"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'upc': upc}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("Item", [])
    if isinstance(items, dict):  # Only one item found
        items = [items]
    return items

def list_first_10_items(access_token):
    url = f"{API_BASE}/Account/{ACCOUNT_ID}/Item.json"
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'limit': 10}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    data = resp.json()
    items = data.get("Item", [])
    if isinstance(items, dict):
        items = [items]
    for item in items:
        print(f"ID: {item.get('itemID')}, UPC: {item.get('upc')}, Description: {item.get('description')}")

def add_new_item(access_token):
    url = f"{API_BASE}/Account/{ACCOUNT_ID}/Item.json"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    print("Enter new item details:")
    description = input("Description: ").strip()
    upc = input("UPC: ").strip()
    default_cost = float(input("Default Cost: ").strip())
    price = float(input("Price: ").strip())
    qoh = int(input("Initial Quantity (total, all shops): ").strip())
    manufacturer_sku = input("Manufacturer SKU: ").strip()
    data = {
        "Item": {
            "description": description,
            "upc": upc,
            "defaultCost": default_cost,
            "price": price,
            "manufacturerSKU": manufacturer_sku,
            "ItemShops": {
                "ItemShop": {
                    "shopID": 0,
                    "qoh": qoh
                }
            }
        }
    }
    resp = requests.post(url, headers=headers, data=json.dumps(data))
    try:
        resp.raise_for_status()
        print("Item created successfully!")
        print(json.dumps(resp.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}")
        print(resp.text)

if __name__ == "__main__":
    # === AUTH ===
    try:
        with open('lightspeed_tokens.json', 'r') as f:
            tokens = json.load(f)
    except FileNotFoundError:
        if LS_REFRESH_TOKEN:
            print("Using provided refresh token to obtain access token...")
            tokens = refresh_token(LS_REFRESH_TOKEN)
            with open('lightspeed_tokens.json', 'w') as f:
                json.dump(tokens, f)
        else:
            code = get_authorization_code()
            tokens = get_tokens(code)
            with open('lightspeed_tokens.json', 'w') as f:
                json.dump(tokens, f)

    access_token = tokens['access_token']
    refresh = tokens.get('refresh_token')

    # === MAIN MENU ===
    while True:
        print("\n1. Fetch item details by ID\n2. Update item quantity\n3. Refresh token\n4. Search item by UPC\n5. List first 10 items\n6. Exit\n7. Add new item")
        choice = input("Choose an option: ").strip()
        if choice == '1':
            iid = input("Enter Item ID: ").strip()
            try:
                item = fetch_item(access_token, iid)
                print(json.dumps(item, indent=2))
            except Exception as e:
                print(f"Error: {e}")
        elif choice == '2':
            iid = input("Enter Item ID: ").strip()
            qty = int(input("Enter new quantity: ").strip())
            try:
                result = update_item_quantity(access_token, iid, qty)
                print("Update successful! Response:")
                print(json.dumps(result, indent=2))
            except Exception as e:
                print(f"Error: {e}")
        elif choice == '3':
            if not refresh:
                print("No refresh token available.")
            else:
                tokens = refresh_token(refresh)
                access_token = tokens['access_token']
                refresh = tokens.get('refresh_token')
                with open('lightspeed_tokens.json', 'w') as f:
                    json.dump(tokens, f)
                print("Token refreshed!")
        elif choice == '4':
            upc = input("Enter UPC: ").strip()
            try:
                items = fetch_item_by_upc(access_token, upc)
                if not items:
                    print("No item found with that UPC.")
                else:
                    for item in items:
                        print(json.dumps(item, indent=2))
                        iid = item.get('itemID')
                        print(f"Item ID: {iid}")
                        update = input("Update quantity for this item? (y/n): ").strip().lower()
                        if update == 'y' and iid:
                            qty = int(input("Enter new quantity: ").strip())
                            try:
                                result = update_item_quantity(access_token, iid, qty)
                                print("Update successful! Response:")
                                print(json.dumps(result, indent=2))
                            except Exception as e:
                                print(f"Error: {e}")
            except Exception as e:
                print(f"Error: {e}")
        elif choice == '5':
            try:
                list_first_10_items(access_token)
            except Exception as e:
                print(f"Error: {e}")
        elif choice == '6':
            break
        elif choice == '7':
            try:
                add_new_item(access_token)
            except Exception as e:
                print(f"Error: {e}")
        else:
            print("Invalid choice.") 
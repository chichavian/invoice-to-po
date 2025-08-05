import requests
import json

# Replace with your actual values
ACCESS_TOKEN = '341f6d2317325560e87308296b90c34cfbdb2bd0'
ACCOUNT_ID = '266086'
SHOP_ID = 1
VENDOR_ID = 95

BASE_URL = f'https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}'

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json',
}

# Correct payload format: fields at the root level
payload = {
    "vendorID": VENDOR_ID,
    "shopID": SHOP_ID,
    "shipCost": 7.50
}

order_url = f"{BASE_URL}/Order.json"
order_resp = requests.post(order_url, headers=headers, data=json.dumps(payload))
try:
    order_resp.raise_for_status()
    order_json = order_resp.json()
    print("Raw PO creation response:", order_json)
    if "Order" in order_json:
        print("Purchase Order created:")
        print(json.dumps(order_json["Order"], indent=2))
    else:
        print("No 'Order' key in response.")
except Exception as e:
    print(f"Error creating purchase order: {e}")
    print("Response body:", order_resp.text) 
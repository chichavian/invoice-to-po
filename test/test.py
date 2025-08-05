import requests
import json

# Replace with your values
ACCESS_TOKEN = '3024593ebf06fd5ae0a9e0436a2d4da3145b9852'
ACCOUNT_ID = '266086'
ORDER_ID = 12        # Replace with the order you just created
ITEM_ID = 5551         # Replace with a valid item ID from your inventory
QUANTITY = 3
PRICE = 25.00

url = f"https://api.lightspeedapp.com/API/V3/Account/{ACCOUNT_ID}/OrderLine.json"

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

payload = {
    "quantity": QUANTITY,
    "price": PRICE,
    "originalPrice": PRICE,
    "numReceived": 0,
    "itemID": ITEM_ID,
    "orderID": ORDER_ID
}

response = requests.post(url, headers=headers, json=payload)

if response.status_code == 200:
    print("✅ Item added to PO:")
    print(json.dumps(response.json(), indent=2))
else:
    print("❌ Failed to add item")
    print("Status:", response.status_code)
    print("Response:", response.text)

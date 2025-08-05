import requests
import json

# ====== HARDCODED CREDENTIALS & IDs FOR TESTING ======
ACCOUNT_ID = '266086'
SHOP_ID = 1
VENDOR_ID = 95
ITEM_ID = 5551
QUANTITY = 5
PRICE = 10.00
ACCESS_TOKEN = '3024593ebf06fd5ae0a9e0436a2d4da3145b9852'
# =====================================================

API_BASE = 'https://api.lightspeedapp.com/API/V3'

headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}',
    'Content-Type': 'application/json',
}

print("Select an option:")
print("1. Print all shops")
print("2. Create purchase order and add item")
choice = input("Enter option number: ").strip()

if choice == '1':
    shops_url = f"{API_BASE}/Account/{ACCOUNT_ID}/Shop.json"
    shops_resp = requests.get(shops_url, headers=headers)
    shops_resp.raise_for_status()
    shops_data = shops_resp.json().get('Shop', [])
    if isinstance(shops_data, dict):
        shops_data = [shops_data]
    print("Available Shops:")
    for shop in shops_data:
        print(f"Shop ID: {shop.get('shopID')}, Name: {shop.get('name')}, Archived: {shop.get('archived')}")
elif choice == '2':
    # Check shop archived status
    shop_url = f"{API_BASE}/Account/{ACCOUNT_ID}/Shop/{SHOP_ID}.json"
    shop_resp = requests.get(shop_url, headers=headers)
    shop_resp.raise_for_status()
    shop_data = shop_resp.json().get('Shop', {})
    archived = shop_data.get('archived')
    print(f"Shop ID: {shop_data.get('shopID')}, Name: {shop_data.get('name')}, Archived: {archived}")
    if archived is True or archived == 'true' or archived == 'True':
        print("ERROR: The selected shop is archived and cannot be used for purchase orders.")
        exit(1)

    # Step 1: Create the purchase order (fields at root level)
    payload = {
        "vendorID": VENDOR_ID,
        "shopID": SHOP_ID,
        "shipCost": 7.50
    }
    order_url = f"{API_BASE}/Account/{ACCOUNT_ID}/Order.json"
    order_resp = requests.post(order_url, headers=headers, data=json.dumps(payload))
    try:
        order_resp.raise_for_status()
        order_json = order_resp.json()
        print("Raw PO creation response:", order_json)
        if "Order" in order_json:
            print("Purchase Order created:")
            print(json.dumps(order_json["Order"], indent=2))
            order_id = int(order_json["Order"]["orderID"])  # Ensure orderID is an integer
        else:
            print("No 'Order' key in response.")
            exit(1)
    except Exception as e:
        print(f"Error creating purchase order: {e}")
        print("Response body:", order_resp.text)
        exit(1)

    # Step 2: Add item 5551 to the purchase order
    orderline_payload = {
        "quantity": QUANTITY,
        "price": PRICE,
        "originalPrice": PRICE,
        "numReceived": 0,
        "itemID": ITEM_ID,
        "orderID": order_id
    }
    print("Using order_id for OrderLine:", order_id, type(order_id))
    print("OrderLine payload:", json.dumps(orderline_payload, indent=2))
    orderline_url = f"{API_BASE}/Account/{ACCOUNT_ID}/OrderLine.json"
    try:
        orderline_resp = requests.post(orderline_url, headers=headers, json=orderline_payload)
        if orderline_resp.status_code == 200:
            print("✅ Item added to PO:")
            print(json.dumps(orderline_resp.json(), indent=2))
        else:
            print("❌ Failed to add item")
            print("Status:", orderline_resp.status_code)
            print("Response:", orderline_resp.text)
    except Exception as e:
        print(f"Error adding item to purchase order: {e}")
        print("Response body:", orderline_resp.text)
else:
    print("Invalid option.") 
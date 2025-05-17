import os
import requests
import logging

def fetch_servus_speed_offers(address):
    username = os.getenv("SERVUS_SPEED_USERNAME")
    password = os.getenv("SERVUS_SPEED_PASSWORD")
    base_url = "https://servusspeed.gendev7.check24.fun"


    try:
        # Step 1: Get available products
        params = {
            "street": address.get("street"),
            "houseNumber": address.get("houseNumber"),
            "city": address.get("city"),
            "plz": address.get("plz"),
            "countryCode": "DE"
        }
        print("🔎 Requesting available products with params:", params)
        auth = (username, password)
        resp = requests.get(f"{base_url}/available-products", params=params, auth=auth, timeout=5)
        print("📡 Available products response:", resp.status_code, resp.text)
        resp.raise_for_status()
        product_ids = resp.json().get("productIds", [])
        if not product_ids:
            print("⚠️ No product IDs returned.")
            return []

        offers = []
        for pid in product_ids:
            print(f"📦 Fetching product details for ID: {pid}")
            detail_resp = requests.get(f"{base_url}/product-details/{pid}", auth=auth, timeout=5)
            detail_resp.raise_for_status()
            product = detail_resp.json()

            # Example normalization (adjust this to your schema)
            normalized_offer = {
                "id": pid,
                "provider": "Servus Speed",
                "speed": product.get("bandwidthInMbps"),
                "price": product.get("pricePerMonthInCent"),
                "duration": product.get("minimumContractDurationInMonths"),
                "description": product.get("description", ""),
            }
            offers.append(normalized_offer)

        return offers

    except Exception as e:
        logging.exception("❌ Failed to fetch Servus Speed offers")
        return []

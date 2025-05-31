# app/services/ping_perfect_client.py
import os
import requests
import time
import hashlib
import hmac
import json

# --- Credentials and Constants ---
PING_PERFECT_BASE_URL = os.getenv("PING_PERFECT_BASE_URL", "https://pingperfect.gendev7.check24.fun")
PING_PERFECT_CLIENT_ID = os.getenv("PING_PERFECT_CLIENT_ID")
PING_PERFECT_SIGNATURE_SECRET = os.getenv("PING_PERFECT_SIGNATURE_SECRET")
PING_PERFECT_OFFERS_ENDPOINT = "/internet/angebote/data"

def _calculate_ping_perfect_signature(request_body_str, timestamp_seconds, secret):
    data_to_sign = f"{timestamp_seconds}:{request_body_str}"
    signature_bytes = hmac.new(
        secret.encode('utf-8'),
        data_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return signature_bytes.hex()

def _normalize_ping_perfect_offer(offer_data, index):
    if not offer_data:
        return None
    try:
        api_provider_name = offer_data.get("providerName", f"PingPerfectOffer_{index}")
        product_info = offer_data.get("productInfo")
        pricing_details = offer_data.get("pricingDetails")

        if not product_info or not pricing_details:
            print(f"Ping Perfect Norm: Skipping offer - missing productInfo/pricingDetails. API Name: {api_provider_name}")
            return None

        speed_mbps = product_info.get("speed")
        contract_months = product_info.get("contractDurationInMonths")
        connection_type_api = product_info.get("connectionType", "").title()
        tv_package_api = product_info.get("tv")
        limit_from_api = product_info.get("limitFrom")
        max_age_api = product_info.get("maxAge")
        product_name = product_info.get("name", api_provider_name) # Use name from productInfo if available

        monthly_cost_cents = pricing_details.get("monthlyCostInCent")
        monthly_price_eur = monthly_cost_cents / 100.0 if monthly_cost_cents is not None else None
        
        installation_service_str = pricing_details.get("installationService", "").lower()
        installation_included_bool = False
        one_time_cost_eur = 0.00
        
        if installation_service_str == "included" or installation_service_str == "true" or installation_service_str == "0":
            installation_included_bool = True
        elif installation_service_str.isdigit():
            setup_fee_cents = int(installation_service_str)
            if setup_fee_cents > 0:
                one_time_cost_eur = setup_fee_cents / 100.0
            else:
                installation_included_bool = True
        
        benefits_list = []
        if installation_included_bool and one_time_cost_eur == 0.0:
            benefits_list.append("Installation service included")
        elif one_time_cost_eur > 0.0: # Only add if there's an actual fee
            benefits_list.append(f"Installation fee: €{one_time_cost_eur:.2f}")
        
        provider_specific_id = offer_data.get("productId", f"pp_{product_name}_{speed_mbps}_{index}") # Use productId if available

        normalized_offer = {
            "providerName": "Ping Perfect",
            "productName": product_name,
            "downloadSpeedMbps": speed_mbps,
            "uploadSpeedMbps": None,
            "monthlyPriceEur": monthly_price_eur,
            "monthlyPriceEurAfter2Years": None, # Not in spec
            "contractTermMonths": contract_months,
            "connectionType": connection_type_api,
            "benefits": ", ".join(benefits_list) if benefits_list else "N/A",
            "tv": tv_package_api if tv_package_api and tv_package_api.strip() and tv_package_api.lower() != "none" else None,
            "discount": None, # Not in spec
            "discountType": None, # Not in spec
            "installationServiceIncluded": installation_included_bool,
            "ageRestrictionMax": max_age_api,
            "dataLimitGb": limit_from_api,
            "_provider_specific_id": provider_specific_id,
        }
        return normalized_offer
    except Exception as e:
        print(f"Ping Perfect Norm Error: {e} for offer data: {str(offer_data)[:200]}...")
        return None

def fetch_ping_perfect_offers(address_details, wants_fiber_param=True): # Renamed
    if not all([PING_PERFECT_CLIENT_ID, PING_PERFECT_SIGNATURE_SECRET, PING_PERFECT_BASE_URL]):
        print("Ping Perfect Client ERROR: API credentials or URL not fully configured.")
        return []

    request_body_dict = {
        "street": address_details.get("strasse"), "plz": address_details.get("postleitzahl"),
        "houseNumber": address_details.get("hausnummer"), "city": address_details.get("stadt"),
        "wantsFiber": wants_fiber_param
    }
    
    required_fields = ["street", "plz", "houseNumber", "city"] # wantsFiber is boolean, can be False
    for field in required_fields:
        if request_body_dict.get(field) is None:
            print(f"Ping Perfect Client WARNING: Missing required field '{field}'. Address: {address_details}")
            return []

    request_body_str = json.dumps(request_body_dict, sort_keys=True, separators=(',', ':'))
    current_timestamp_seconds = int(time.time())
    signature = _calculate_ping_perfect_signature(
        request_body_str, current_timestamp_seconds, PING_PERFECT_SIGNATURE_SECRET
    )
    headers = {
        "Content-Type": "application/json", "Accept": "application/json",
        "X-Client-Id": PING_PERFECT_CLIENT_ID, "X-Timestamp": str(current_timestamp_seconds),
        "X-Signature": signature
    }
    api_url = f"{PING_PERFECT_BASE_URL.rstrip('/')}{PING_PERFECT_OFFERS_ENDPOINT}"
    all_normalized_offers = []

    try:
        print(f"Ping Perfect Client: Sending request to {api_url}")
        response = requests.post(api_url, data=request_body_str, headers=headers, timeout=20) # Timeout added
        print(f"Ping Perfect Client: API response status: {response.status_code}")
        response.raise_for_status()
        
        offers_list_json = response.json()
        if isinstance(offers_list_json, list):
            print(f"Ping Perfect Client: Received {len(offers_list_json)} raw offers.")
            for i, offer_item in enumerate(offers_list_json):
                normalized = _normalize_ping_perfect_offer(offer_item, i)
                if normalized:
                    all_normalized_offers.append(normalized)
        else:
            print(f"Ping Perfect Client WARNING: Expected list, got {type(offers_list_json)}. Resp: {str(offers_list_json)[:200]}")
            
        print(f"Ping Perfect Client: Processed {len(all_normalized_offers)} offers.")

    except requests.exceptions.Timeout:
        print("Ping Perfect Client ERROR: Timeout during API request.")
    except requests.exceptions.HTTPError as http_err:
        print(f"Ping Perfect Client HTTP ERROR: {http_err.response.status_code} - {http_err.response.text[:200]}")
    except requests.exceptions.RequestException as req_err:
        print(f"Ping Perfect Client REQUEST EXCEPTION: {req_err}")
    except ValueError as json_err: # JSONDecodeError
        print(f"Ping Perfect Client JSON DECODE ERROR: {json_err}. Response: {response.text[:200] if 'response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"Ping Perfect Client UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    return all_normalized_offers

# ... (if __name__ == '__main__': block can remain similar, calling fetch_ping_perfect_offers)
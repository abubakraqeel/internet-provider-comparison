import os
import requests
import time
import hashlib
import hmac
import json

# --- Credentials and Constants ---
# Server URL from OpenAPI spec
PING_PERFECT_BASE_URL = os.getenv("PING_PERFECT_BASE_URL", "https://pingperfect.gendev7.check24.fun")
PING_PERFECT_CLIENT_ID = os.getenv("PING_PERFECT_CLIENT_ID")
PING_PERFECT_SIGNATURE_SECRET = os.getenv("PING_PERFECT_SIGNATURE_SECRET")
PING_PERFECT_OFFERS_ENDPOINT = "/internet/angebote/data" # From OpenAPI spec

# --- Signature Calculation ---
def _calculate_ping_perfect_signature(request_body_str, timestamp_seconds, secret):
    """
    Calculates the HMAC-SHA256 signature for Ping Perfect.
    """
    data_to_sign = f"{timestamp_seconds}:{request_body_str}"
    # Ensure secret and data are bytes for hmac
    signature_bytes = hmac.new(
        secret.encode('utf-8'),
        data_to_sign.encode('utf-8'),
        hashlib.sha256
    ).digest() # Get raw bytes
    return signature_bytes.hex() # Convert raw bytes to hex string

# --- Normalization Function ---
def _normalize_ping_perfect_offer(offer_data, index): # offer_data is an InternetProduct object
    """
    Transforms a Ping Perfect API offer object (InternetProduct) into a standardized format.
    """
    if not offer_data:
        return None

    try:
        # --- Extract from top-level InternetProduct ---
        api_provider_name = offer_data.get("providerName", f"PingPerfectOffer_{index}")

        product_info = offer_data.get("productInfo") # This is optional in WSDL, but crucial
        pricing_details = offer_data.get("pricingDetails") # Also optional

        if not product_info or not pricing_details:
            print(f"Ping Perfect Normalization: Skipping offer due to missing productInfo or pricingDetails. API Provider Name: {api_provider_name}")
            return None

        # --- Extract from ProductInfo ---
        speed_mbps = product_info.get("speed") # Assuming download
        contract_months = product_info.get("contractDurationInMonths")
        connection_type_api = product_info.get("connectionType") # DSL, CABLE, FIBER, MOBILE
        tv_package_api = product_info.get("tv") # String or None
        limit_from_api = product_info.get("limitFrom") # Int or None (assume GB)
        max_age_api = product_info.get("maxAge") # Int or None
        
        # Construct a product name
        product_name = f"{api_provider_name} {connection_type_api}"


        # --- Extract from PricingDetails ---
        monthly_cost_cents = pricing_details.get("monthlyCostInCent")
        monthly_price_eur = monthly_cost_cents / 100.0 if monthly_cost_cents is not None else None
        
        # `installationService` is a string. Need to interpret it.
        # Common values might be "included", "fee_applies", "amount_in_cent", "true/false"
        # This requires checking actual API responses.
        installation_service_str = pricing_details.get("installationService", "").lower()
        installation_included_bool = False
        one_time_cost_eur = 0.00 # Default, adjust if installation has a fee
        
        if installation_service_str == "included" or installation_service_str == "true" or installation_service_str == "0": # Assuming "0" means 0 cost
            installation_included_bool = True
        elif installation_service_str.isdigit(): # If it's a number, assume it's cost in cents
            setup_fee_cents = int(installation_service_str)
            if setup_fee_cents > 0:
                one_time_cost_eur = setup_fee_cents / 100.0
                installation_included_bool = False # As there's a cost
            else: # if 0 cents
                installation_included_bool = True
        # Add more conditions if "fee_applies" or other strings are used.


        # --- Other fields for normalized output (defaults unless found) ---
        upload_speed_mbps = None # Not in Ping Perfect spec
        monthly_price_eur_after_2_years = None # Not in Ping Perfect spec
        discount_value_eur = None # Not in Ping Perfect spec (no voucher fields)
        discount_type_str = None  # Not in Ping Perfect spec

        benefits_list = []
        if installation_included_bool and one_time_cost_eur == 0.0:
            benefits_list.append("Installation service included")
        elif one_time_cost_eur > 0.0:
            benefits_list.append(f"Installation fee: €{one_time_cost_eur:.2f}")

        # if tv_package_api and tv_package_api.strip() and tv_package_api.lower() != "none":
        #     benefits_list.append(f"TV: {tv_package_api}")
        
        if limit_from_api is not None:
            benefits_list.append(f"Data limit: {limit_from_api} GB/month")
        
        if max_age_api is not None:
            benefits_list.append(f"Age restriction: up to {max_age_api} years")

        # Create a provider-specific ID. Using a combination of fields if no single ID given by API.
        # The API response schema for InternetProduct doesn't show a unique 'productId'.
        # We might need to generate one or use a hash of key details.
        # For now, let's use a composite or index.
        provider_specific_id = f"pp_{api_provider_name}_{speed_mbps}_{contract_months}_{index}"
        # A better ID would be if PingPerfect provided one.

        normalized_offer = {
            "providerName": "Ping Perfect", # Standardized name
            "productName": product_name,
            "downloadSpeedMbps": speed_mbps,
            "uploadSpeedMbps": upload_speed_mbps,
            "monthlyPriceEur": monthly_price_eur,
            "monthlyPriceEurAfter2Years": monthly_price_eur_after_2_years,
            "contractTermMonths": contract_months,
            "connectionType": connection_type_api,
            "benefits": ", ".join(benefits_list) if benefits_list else "N/A",
            "tv": tv_package_api if tv_package_api and tv_package_api.strip() and tv_package_api.lower() != "none" else None,
            "discount": discount_value_eur,
            "discountType": discount_type_str,
            "installationServiceIncluded": installation_included_bool,
            "ageRestrictionMax": max_age_api,
            "dataLimitGb": limit_from_api,
            "_provider_specific_id": provider_specific_id,
        }
        return normalized_offer
    except Exception as e:
        print(f"Ping Perfect Normalization: Error normalizing offer: {offer_data}. Error: {e}")
        # import traceback; traceback.print_exc() # For detailed debug
        return None

# --- Main Function to Get Offers ---
def get_ping_perfect_offers(address_details, wants_fiber_param=True): # Added wants_fiber_param
    
    if not all([PING_PERFECT_CLIENT_ID, PING_PERFECT_SIGNATURE_SECRET, PING_PERFECT_BASE_URL]):
        print("Ping Perfect API credentials or URL not fully configured.")
        return []

    # Prepare request body based on CompareProductsRequestData schema
    # It expects: street, plz, houseNumber, city, wantsFiber
    # `address_details` from route is like: {"strasse": ..., "hausnummer": ..., "postleitzahl": ..., "stadt": ... "land": ...}
    request_body_dict = {
        "street": address_details.get("strasse"),
        "plz": address_details.get("postleitzahl"),
        "houseNumber": address_details.get("hausnummer"),
        "city": address_details.get("stadt"),
        "wantsFiber": wants_fiber_param # Get this from args or default it.
                                        # For now, passed as a parameter to this function.
    }
    
    # Ensure all required fields for PingPerfect are present
    required_fields = ["street", "plz", "houseNumber", "city", "wantsFiber"]
    for field in required_fields:
        if request_body_dict.get(field) is None: # wantsFiber could be False, which is not None
            print(f"Ping Perfect: Missing required field '{field}' in request payload. Address details: {address_details}")
            return []

    # Convert dict to compact JSON string (no spaces, sorted keys for consistent signature)
    request_body_str = json.dumps(request_body_dict, sort_keys=True, separators=(',', ':'))

    # Generate timestamp and signature
    current_timestamp_seconds = int(time.time())
    signature = _calculate_ping_perfect_signature(
        request_body_str,
        current_timestamp_seconds,
        PING_PERFECT_SIGNATURE_SECRET
    )

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json", # Good practice to add Accept header
        "X-Client-Id": PING_PERFECT_CLIENT_ID,
        "X-Timestamp": str(current_timestamp_seconds),
        "X-Signature": signature
    }

    api_url = f"{PING_PERFECT_BASE_URL.rstrip('/')}{PING_PERFECT_OFFERS_ENDPOINT}"
    all_normalized_offers = []

    try:
        print(f"Ping Perfect: Sending request to {api_url}")
        # print(f"Ping Perfect: Headers: X-Client-Id={headers['X-Client-Id']}, X-Timestamp={headers['X-Timestamp']}, X-Signature={headers['X-Signature'][:10]}...") # Debug signature
        # print(f"Ping Perfect: Request Body String: {request_body_str}") # Debug body

        response = requests.post(
            api_url,
            data=request_body_str, # Send the JSON string as data
            headers=headers,
            timeout=25 # Adjust timeout as needed
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        
        # Response is an array of InternetProduct objects
        offers_list_json = response.json() 

        if isinstance(offers_list_json, list):
            print(f"Ping Perfect: Received {len(offers_list_json)} offers.")
            for i, offer_item in enumerate(offers_list_json):
                normalized = _normalize_ping_perfect_offer(offer_item, i)
                if normalized:
                    all_normalized_offers.append(normalized)
                
        else:
            print(f"Ping Perfect: Expected a list of offers, but received type: {type(offers_list_json)}. Response: {offers_list_json}")
            
        print(f"Ping Perfect: Successfully processed and normalized {len(all_normalized_offers)} offers.")

    except requests.exceptions.Timeout:
        print("Ping Perfect: Timeout during API request.")
    except requests.exceptions.HTTPError as e:
        print(f"Ping Perfect: HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Ping Perfect: Request error: {e}")
    except ValueError as e: # JSONDecodeError
        print(f"Ping Perfect: Could not decode JSON response: {e}. Response text: {response.text[:500] if 'response' in locals() else 'N/A'}")
    except Exception as e:
        print(f"Ping Perfect: An unexpected error occurred: {e}")
        # import traceback; traceback.print_exc()

    return all_normalized_offers

# --- Example for direct testing (optional) ---
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv() # Load .env file

    PING_PERFECT_CLIENT_ID = os.getenv("PING_PERFECT_CLIENT_ID")
    PING_PERFECT_SIGNATURE_SECRET = os.getenv("PING_PERFECT_SIGNATURE_SECRET")
    PING_PERFECT_BASE_URL = os.getenv("PING_PERFECT_BASE_URL", "https://pingperfect.gendev7.check24.fun")


    if not all([PING_PERFECT_CLIENT_ID, PING_PERFECT_SIGNATURE_SECRET]):
        print("Please set PING_PERFECT_CLIENT_ID and PING_PERFECT_SIGNATURE_SECRET environment variables.")
    else:
        sample_address = {
            "strasse": "Hauptstrasse",
            "hausnummer": "10",
            "postleitzahl": "85737",
            "stadt": "Ismaning",
            "land": "DE" # Though PingPerfect request doesn't use 'land' explicitly
        }
        # Test with wantsFiber=True and wantsFiber=False
        offers_fiber_true = get_ping_perfect_offers(sample_address, wants_fiber_param=True)
        import json
        if offers_fiber_true:
            print(f"\n--- Found {len(offers_fiber_true)} Ping Perfect Offers (wantsFiber=True) ---")
            print(json.dumps(offers_fiber_true, indent=2, ensure_ascii=False))
        
        offers_fiber_false = get_ping_perfect_offers(sample_address, wants_fiber_param=False)
        if offers_fiber_false:
            print(f"\n--- Found {len(offers_fiber_false)} Ping Perfect Offers (wantsFiber=False) ---")
            print(json.dumps(offers_fiber_false, indent=2, ensure_ascii=False))
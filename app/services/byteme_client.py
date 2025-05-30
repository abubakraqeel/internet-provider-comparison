import requests
import os
import csv 
from io import StringIO 


# --- Credentials and Constants ---
BYTEME_BASE_URL = "https://byteme.gendev7.check24.fun/app/api/products/data"
BYTEME_API_KEY = os.getenv("BYTEME_API_KEY")

# --- Normalization Function (specific to ByteMe's CSV structure) ---
def _normalize_byteme_offer(offer_data_dict):
    """
    Transforms a dictionary representing a row from ByteMe's CSV
    into a standardized offer format.

    CSV Header: productId,providerName,speed,monthlyCostInCent,afterTwoYearsMonthlyCost,
                durationInMonths,connectionType,installationService,tv,limitFrom,
                maxAge,voucherType,voucherValue
    "productId": "510",
    "providerName": "Byte Extreme 100, All in",
    "speed": "100",
    "monthlyCostInCent": "4931",
    "afterTwoYearsMonthlyCost": "5131",
    "durationInMonths": "12",
    "connectionType": "Fiber",
    "installationService": "false",
    "tv": "Extreme ByteLive",
    "limitFrom": "300",
    "maxAge": "",
    "voucherType": "absolute",
    "voucherValue": "10775"
    """
    if not offer_data_dict:
        return None

    try:
        product_name = offer_data_dict.get("providerName") 

        connection_type = offer_data_dict.get("connectionType", "N/A")
        speed_str = offer_data_dict.get("speed", "N/A")
        

        # --- Speeds ---
        # Assuming 'speed' is download speed in Mbps
        download_speed_mbps = int(offer_data_dict.get("speed")) if offer_data_dict.get("speed") else None

        # --- Costs ---
        monthly_cost_cents = int(offer_data_dict.get("monthlyCostInCent")) if offer_data_dict.get("monthlyCostInCent") else None
        monthly_price_eur_initial = monthly_cost_cents / 100.0 if monthly_cost_cents is not None else None

        # afterTwoYearsMonthlyCost - 
        after_two_years_cost_cents = int(offer_data_dict.get("afterTwoYearsMonthlyCost")) if offer_data_dict.get("afterTwoYearsMonthlyCost") else None
        monthly_price_eur_later = after_two_years_cost_cents / 100.0 if after_two_years_cost_cents is not None else None
        
        # For now, let's use the initial price for monthlyPriceEur and detail the change in benefits.
        monthly_price_eur = monthly_price_eur_initial


        # --- Contract ---
        duration_months = int(offer_data_dict.get("durationInMonths")) if offer_data_dict.get("durationInMonths") else None

        # --- Features & Benefits ---
        benefits = []
        installation_service_str = offer_data_dict.get("installationService", "false").lower() # "true" or "false"
        installation_service_included = installation_service_str == "true"
        if installation_service_included:
            benefits.append("Installation service included")

        tv_package = offer_data_dict.get("tv") # Assuming this is a string describing the TV package
        # if tv_package and tv_package.strip() and tv_package.lower() != "none":
        #     benefits.append(f"TV package: {tv_package}")


        # Data limit: 'limitFrom' (e.g., "100" for 100GB)
        limit_from_gb_str = offer_data_dict.get("limitFrom")
        data_limit_gb = int(limit_from_gb_str) if limit_from_gb_str and limit_from_gb_str.isdigit() else None
        if data_limit_gb is not None:
            benefits.append(f"Data limit: {data_limit_gb} GB/month")

        # Age restriction: 'maxAge'
        max_age_str = offer_data_dict.get("maxAge")
        max_age = int(max_age_str) if max_age_str and max_age_str.isdigit() else None
        if max_age is not None:
            benefits.append(f"Offer valid for customers up to {max_age} years old")

        # Price change after two years
        if monthly_price_eur_later is not None and monthly_price_eur_later != monthly_price_eur_initial:
            benefits.append(f"Price changes to €{monthly_price_eur_later}/month after 2 years.")
            # Or, if durationInMonths is always 24, "after 24 months".

        # Vouchers: 'voucherType', 'voucherValue' (value in cents)
        voucher_type = offer_data_dict.get("voucherType")
        voucher_value = int(offer_data_dict.get("voucherValue")) / 100.0
        
        # if voucher_type and voucher_value_cents_str and voucher_value_cents_str.isdigit():
        #     voucher_value_cents = int(voucher_value_cents_str)
        #     if voucher_value_cents > 0:
        #         voucher_value_eur = voucher_value_cents / 100.0
        #         benefits.append(f"{voucher_type.capitalize()} voucher: €{voucher_value_eur:.2f}")
        #         # If voucher reduces one-time cost (e.g. setup fee if there was one, or acts as cashback)
        #         one_time_cost_eur -= voucher_value_eur # Makes it negative if it's a cashback

        normalized_offer = {
            "providerName": "ByteMe", # Standardized name
            "productName": product_name,
            "downloadSpeedMbps": download_speed_mbps,
            "uploadSpeedMbps": None, # Not in ByteMe CSV
            "monthlyPriceEur": monthly_price_eur, # Initial price
            "monthlyPriceEurAfter2Years": monthly_price_eur_later,
            "contractTermMonths": duration_months,
            "connectionType": connection_type,
            "benefits": ", ".join(benefits) if benefits else "No specific benefits listed",
            "tv": tv_package,
            "discount": voucher_value,
            "discountType": voucher_type,
            "installationServiceIncluded": installation_service_included,
            "ageRestrictionMax": max_age,
            "dataLimitGb": data_limit_gb,
            "_provider_specific_id": offer_data_dict.get("productId"), # Crucial for de-duplication
            # "_raw_byteme_data": offer_data_dict # Optional for debugging
        }
        return normalized_offer
    except Exception as e:
        print(f"ByteMe Normalization: Error normalizing offer data: {offer_data_dict}. Error: {e}")
        return None


# --- Main Function to Get Offers ---
def get_byteme_offers(address_details):
    """
    Fetches, parses, de-duplicates, and normalizes internet offers from ByteMe.

    :param address_details: A dictionary like:
                            {
                                "street": "Test Street",
                                "houseNumber": "123",
                                "plz": "10115",
                                "city": "Berlin"
                            }
    :return: A list of normalized, de-duplicated offer dictionaries.
    """
    if not BYTEME_API_KEY:
        print("ByteMe API Key (BYTEME_API_KEY) is not configured.")
        return []

    # Construct query parameters from address_details
    # API takes: street, houseNumber, city, plz
    params = {
        "street": address_details.get("strasse"),
        "houseNumber": address_details.get("hausnummer"),
        "city": address_details.get("stadt"),
        "plz": address_details.get("postleitzahl")
    }

    headers = {
        "X-Api-Key": BYTEME_API_KEY
        # No "Content-Type" needed for GET with query params
    }

    all_normalized_offers = []
    processed_product_ids = set() # For de-duplication

    try:
        print(f"ByteMe: Requesting products for address: {params}")
        response = requests.get(
            BYTEME_BASE_URL,
            params=params,
            headers=headers,
            timeout=20 # Timeout for the API call
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)

        # Response content is CSV text
        csv_text = response.text
        
        # Use StringIO to treat the string as a file for csv.reader
        csv_file = StringIO(csv_text)
        
        # The first line is the header
        # productId,providerName,speed,monthlyCostInCent,afterTwoYearsMonthlyCost,durationInMonths,
        # connectionType,installationService,tv,limitFrom,maxAge,voucherType,voucherValue
        csv_reader = csv.DictReader(csv_file) # DictReader uses the first row as keys

        for row_dict in csv_reader:
            product_id = row_dict.get("productId")
            if not product_id: # Skip rows without a product ID
                print(f"ByteMe: Skipping row due to missing productId: {row_dict}")
                continue

            # De-duplication based on productId
            if product_id in processed_product_ids:
                print(f"ByteMe: Skipping duplicate productId: {product_id}")
                continue
            processed_product_ids.add(product_id)

            normalized_offer = _normalize_byteme_offer(row_dict)
            #normalized_offer = row_dict
            if normalized_offer:
                all_normalized_offers.append(normalized_offer)
        
        print(f"ByteMe: Successfully fetched, de-duplicated, and normalized {len(all_normalized_offers)} offers.")

    except requests.exceptions.Timeout:
        print("ByteMe: Timeout fetching products.")
    except requests.exceptions.HTTPError as e:
        print(f"ByteMe: HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"ByteMe: Request error: {e}")
    except csv.Error as e: # Catch errors from csv parsing
        print(f"ByteMe: CSV parsing error: {e}")
    except Exception as e: # Catch any other unexpected errors
        print(f"ByteMe: An unexpected error occurred: {e}")
        # import traceback
        # traceback.print_exc() # For more detailed debugging
        
    return all_normalized_offers

# --- Example for direct testing (optional) ---
# if __name__ == '__main__':
#     # Load .env variables if you're using python-dotenv for local testing
#     from dotenv import load_dotenv
#     load_dotenv()
#     BYTEME_API_KEY = os.getenv("BYTEME_API_KEY") # Re-assign for local scope

#     if not BYTEME_API_KEY:
#         print("Please ensure BYTEME_API_KEY is set in your environment.")
#     else:
#         sample_address = {
#             "strasse": "Teststraße", # Use an address likely to have offers
#             "hausnummer": "1",
#             "postleitzahl": "12345", # Use a valid PLZ for testing
#             "stadt": "Berlin"
#         }
#         offers = get_byteme_offers(sample_address)
#         import json
#         if offers:
#             print(f"\n--- Found {len(offers)} ByteMe Offers ---")
#             print(json.dumps(offers, indent=2))
#         else:
#             print("\n--- No ByteMe offers found or error occurred. ---")
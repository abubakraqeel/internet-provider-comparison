import os
import requests
import time # For potential delays between paginated requests
import json # For printing JSON nicely if testing directly

# --- Credentials and Constants ---
VERBYNDICH_BASE_URL = "https://verbyndich.gendev7.check24.fun/check24/data"
VERBYNDICH_API_KEY = os.getenv("VERBYNDICH_API_KEY")

# In app/services/verbyndich_client.py
import re
import time # Already there
# ... (os, requests, json if needed for __main__)

# ... (VERBYNDICH_BASE_URL, VERBYNDICH_API_KEY) ...

def _parse_verbyndich_description(description_str):
    """
    Parses the VerbynDich description string to extract offer details using regex.
    Returns a dictionary of extracted details.
    """
    details = {
        "downloadSpeedMbps": None, "uploadSpeedMbps": None, "monthlyPriceEur": None,
        "monthlyPriceEurAfter2Years": None, "contractTermMonths": None, 
        "connectionType": None, "tv": None, "dataLimitGb": None,
        "ageRestrictionMax": None, 
        "discount_percentage": None, "discount_percentage_duration_months": None, 
        "discount_percentage_max_eur": None, "discount_onetime_eur": None,
        "discount_onetime_min_order_eur": None,
        "raw_benefits_text": [] # To collect various benefit phrases
    }

    if not description_str:
        return details

    # 1. Monthly Price (Initial)
    price_match = re.search(r"Für nur (\d+)€ im Monat", description_str)
    if price_match:
        details["monthlyPriceEur"] = float(price_match.group(1))

    # 2. Connection Type
    conn_type_match = re.search(r"eine (DSL|Cable|Fiber)-Verbindung", description_str)
    if conn_type_match:
        type_map = {"dsl": "DSL", "cable": "Cable", "fiber": "Fiber"} # Normalize case
        details["connectionType"] = type_map.get(conn_type_match.group(1).lower())

    # 3. Speed (Download)
    speed_match = re.search(r"Geschwindigkeit von (\d+)\s*Mbit/s", description_str)
    if speed_match:
        details["downloadSpeedMbps"] = int(speed_match.group(1))
    # No upload speed seen in these examples for VerbynDich

    # 4. Contract Duration
    term_match = re.search(r"Mindestvertragslaufzeit (\d+)\s*Monate", description_str)
    if term_match:
        details["contractTermMonths"] = int(term_match.group(1))

    # 5. Data Limit (Throttling)
    limit_match = re.search(r"Ab (\d+)GB pro Monat wird die Geschwindigkeit gedrosselt", description_str)
    if limit_match:
        details["dataLimitGb"] = int(limit_match.group(1))
        details["raw_benefits_text"].append(f"Speed throttled after {details['dataLimitGb']}GB/month")


    # 6. Discount Type 1 (Percentage)
    # "Rabatt von 3% auf Ihre monatliche Rechnung bis zum 24. Monat. Der maximale Rabatt beträgt 107€."
    perc_discount_match = re.search(
        r"Rabatt von (\d+)% auf Ihre monatliche Rechnung bis zum (\d+)\. Monat\.\s*Der maximale Rabatt beträgt (\d+)€",
        description_str
    )
    if perc_discount_match:
        details["discount_percentage"] = int(perc_discount_match.group(1))
        details["discount_percentage_duration_months"] = int(perc_discount_match.group(2))
        details["discount_percentage_max_eur"] = float(perc_discount_match.group(3))
        details["raw_benefits_text"].append(
            f"{details['discount_percentage']}% monthly discount for {details['discount_percentage_duration_months']} months (max total €{details['discount_percentage_max_eur']})"
        )
    
    # 7. Discount Type 2 (One-time)
    # "einen einmaligen Rabatt von 108€ auf Ihre monatliche Rechnung. Der Mindestbestellwert beträgt 8€."
    onetime_discount_match = re.search(
        r"einmaligen Rabatt von (\d+)€.*?Der Mindestbestellwert beträgt (\d+)€", # .*? for non-greedy match
        description_str
    )
    if onetime_discount_match:
        details["discount_onetime_eur"] = float(onetime_discount_match.group(1))
        details["discount_onetime_min_order_eur"] = float(onetime_discount_match.group(2))
        details["raw_benefits_text"].append(
            f"One-time discount of €{details['discount_onetime_eur']} (min. order €{details['discount_onetime_min_order_eur']})"
        )

    # 8. Price After 24 Months
    price_after_match = re.search(r"Ab dem 24\. Monat beträgt der monatliche Preis (\d+)€", description_str)
    if price_after_match:
        details["monthlyPriceEurAfter2Years"] = float(price_after_match.group(1))

    # 9. TV (Premium plans)
    # tv_match = re.search(r"Fernsehsender enthalten ([^.]+)\.", description_str) # Captures text until next period
    # if tv_match:
    #     details["tv"] = tv_match.group(1).strip()
    #     if details["tv"]: # Check if something was captured
    #          details["raw_benefits_text"].append(f"TV included: {details['tv']}")


    # 10. Age Restriction (Young tariffs)
    age_match = re.search(r"Personen unter (\d+)\s*Jahren verfügbar", description_str)
    if age_match:
        details["ageRestrictionMax"] = int(age_match.group(1)) # This is the "under X" value
        details["raw_benefits_text"].append(f"Young tariff: for persons under {details['ageRestrictionMax']} years")

    return details

# In app/services/verbyndich_client.py

# ... (VERBYNDICH_BASE_URL, VERBYNDICH_API_KEY, _parse_verbyndich_description) ...

def _normalize_verbyndich_offer(api_offer_item, parsed_desc_details):
    """
    Transforms a VerbynDich API item and parsed description into standardized format.
    api_offer_item example: {"product": "VD-Basic-100", "description": "...", "last": false, "valid": true}
    """
    if not api_offer_item or not api_offer_item.get("valid", False):
        # We'll filter out "valid: False" offers in the main get_verbyndich_offers function instead.
        # Here, we might still want to see what a non-valid offer looks like if it gets this far.
        # However, for final output, only valid=True should be considered.
        pass # Let's assume it's pre-filtered or handled later.

    try:
        product_name_from_api = api_offer_item.get("product", f"Verbyndich Offer")
        
        # Construct a more descriptive product name using parsed details
        product_name = product_name_from_api # Default
        # If speed and type are parsed, use them, otherwise product_name_from_api is often descriptive.
        # The product_name_from_api (e.g., "VerbynDich Basic 25") is already quite good.

        # --- One-time Cost and Discount Handling ---
        # The challenge asks for "discount" and "discountType" in normalized form.
        # And also "oneTimeCostEur".
        # If there's a one-time discount, it effectively reduces any setup fee or acts as cashback.
        # VerbynDich descriptions don't mention setup fees, so discounts are like cashback.
        
        one_time_cost_eur = 0.00
        discount_val_eur = None
        discount_type_str = None

        if parsed_desc_details.get("discount_onetime_eur") is not None:
            discount_val_eur = parsed_desc_details["discount_onetime_eur"]
            discount_type_str = "One-time Discount"
            one_time_cost_eur -= discount_val_eur # Makes it negative (cashback)
        elif parsed_desc_details.get("discount_percentage") is not None:
            # Percentage discount is more complex for a single 'discount' value.
            # We could calculate the first month's discount if a base price is known.
            # For now, let's represent the percentage directly in benefits.
            # The 'discount' field will be for absolute one-time amounts.
            discount_type_str = "Percentage (Monthly)"
            # discount_val_eur could be the max cap, or first month's, or None.
            # Let's set it to the max cap if available, otherwise None.
            discount_val_eur = parsed_desc_details.get("discount_percentage_max_eur")


        # --- Assemble Benefits ---
        # `raw_benefits_text` already contains most detailed benefits.
        benefits_string = ", ".join(parsed_desc_details.get("raw_benefits_text", []))
        if not benefits_string: benefits_string = "N/A" # Default if no specific benefits parsed


        normalized_offer = {
            "providerName": "Verbyndich",
            "productName": product_name, # Using the descriptive name from API
            "downloadSpeedMbps": parsed_desc_details.get("downloadSpeedMbps"),
            "uploadSpeedMbps": parsed_desc_details.get("uploadSpeedMbps"), # Remains None
            "monthlyPriceEur": parsed_desc_details.get("monthlyPriceEur"),
            "monthlyPriceEurAfter2Years": parsed_desc_details.get("monthlyPriceEurAfter2Years"),
            "contractTermMonths": parsed_desc_details.get("contractTermMonths"),
            "connectionType": parsed_desc_details.get("connectionType"),
            "benefits": benefits_string,
            "tv": parsed_desc_details.get("tv"), # Parsed TV package name
            "discount": discount_val_eur, # Value of discount in EUR (primary the one-time, or max % cap)
            "discountType": discount_type_str, # Type of discount
            "installationServiceIncluded": None, # Not explicitly mentioned, assume None unless parsed
            "ageRestrictionMax": parsed_desc_details.get("ageRestrictionMax"),
            "dataLimitGb": parsed_desc_details.get("dataLimitGb"),
            "_provider_specific_id": product_name_from_api, # Use 'product' field as ID
        }
        return normalized_offer
    except Exception as e:
        print(f"Verbyndich Normalization Error: {e} for item {api_offer_item.get('product')}")
        import traceback
        traceback.print_exc()
        return None



# In app/services/verbyndich_client.py

# ... (imports, constants, _parse_verbyndich_description, _normalize_verbyndich_offer) ...

def get_verbyndich_offers(address_details): # Renamed from get_verbyndich_raw_data
    if not VERBYNDICH_API_KEY:
        print("Verbyndich API Key (VERBYNDICH_API_KEY) is not configured.")
        return []

    address_str_body_parts = [
        address_details.get("strasse", "").strip(),
        address_details.get("hausnummer", "").strip(),
        address_details.get("stadt", "").strip(),
        address_details.get("postleitzahl", "").strip()
    ]
    if not all(address_str_body_parts):
        print(f"Verbyndich: Missing address components. Details: {address_details}")
        return []
    address_str_body = ";".join(address_str_body_parts)

    all_normalized_offers = [] # Changed from all_raw_offer_items
    current_page = 0
    max_pages_to_fetch = 25 # Increased slightly just in case, but 18 seemed to be the max

    print(f"Verbyndich: Fetching & Normalizing data for address: '{address_str_body}'")

    while current_page < max_pages_to_fetch:
        params = {"apiKey": VERBYNDICH_API_KEY, "page": current_page}
        headers = {"Content-Type": "text/plain;charset=UTF-8"}
        
        try:
            # print(f"Verbyndich: Requesting page {current_page}...") # Less verbose now
            response = requests.post(
                VERBYNDICH_BASE_URL,
                data=address_str_body.encode('utf-8'),
                params=params, headers=headers, timeout=20
            )
            response.raise_for_status()
            api_offer_item = response.json()
            
            if api_offer_item:
                if api_offer_item.get("valid", False): # Process only "valid: true" offers
                    description = api_offer_item.get("description", "")
                    parsed_description_details = _parse_verbyndich_description(description)
                    
                    normalized = _normalize_verbyndich_offer(api_offer_item, parsed_description_details)
                    if normalized:
                        all_normalized_offers.append(normalized)
                # else: # Optional: log invalid offers if needed for debugging
                #     print(f"Verbyndich: Skipping invalid offer on page {current_page}: {api_offer_item.get('product')}")

                if api_offer_item.get("last", False):
                    # print(f"Verbyndich: 'last' flag true on page {current_page}.") # Less verbose
                    break 
            else:
                print(f"Verbyndich: Empty/non-JSON response on page {current_page}. Stopping.")
                break
            current_page += 1
        except requests.exceptions.Timeout: # ... (keep existing except blocks) ...
            print(f"Verbyndich: Timeout on page {current_page}.")
            break 
        except requests.exceptions.HTTPError as e:
            print(f"Verbyndich: HTTP error on page {current_page}: {e.response.status_code} - {e.response.text}")
            break 
        except ValueError as e: 
            print(f"Verbyndich: JSON decode error on page {current_page}: {e}. Response: {response.text[:200] if 'response' in locals() else 'N/A'}")
            break
        except Exception as e:
            print(f"Verbyndich: Unexpected error on page {current_page}: {e}")
            break
    
    if current_page == max_pages_to_fetch:
        print(f"Verbyndich: Reached max_pages_to_fetch ({max_pages_to_fetch}).")
        
    print(f"Verbyndich: Fetched and normalized {len(all_normalized_offers)} offers across {current_page + 1} page(s).")
    return all_normalized_offers

# --- if __name__ == '__main__': block to test the new get_verbyndich_offers ---
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    VERBYNDICH_API_KEY = os.getenv("VERBYNDICH_API_KEY")

    if not VERBYNDICH_API_KEY:
        print("Set VERBYNDICH_API_KEY.")
    else:
        address_test = {
            "strasse": "Musterstraße",
            "hausnummer": "10",
            "postleitzahl": "10115",
            "stadt": "Berlin"
        }
        print(f"\n--- Testing VerbynDich for Address: {address_test} ---")
        normalized_offers = get_verbyndich_offers(address_test) # Call the new function
        if normalized_offers:
            print(f"Total Normalized VerbynDich Offers: {len(normalized_offers)}")
            import json
            print(json.dumps(normalized_offers, indent=2, ensure_ascii=False))
            # For more detailed check of one item:
            # if len(normalized_offers) > 0:
            #     print("\nExample First Normalized Offer:")
            #     print(json.dumps(normalized_offers[0], indent=2, ensure_ascii=False))
        else:
            print("No normalized offers from VerbynDich.")

        # address_test_garching = {
        #     "strasse": "Birkenweg", 
        #     "hausnummer": "7a", 
        #     "postleitzahl": "85748", 
        #     "stadt": "Garching bei München"
        # }
        # print(f"\n--- Testing VerbynDich for Address: {address_test_garching} ---")
        # normalized_offers_garching = get_verbyndich_offers(address_test_garching) # Call the new function
        # if normalized_offers_garching:
        #     print(f"Total Normalized VerbynDich Offers (Garching): {len(normalized_offers_garching)}")
        #     import json
        #     # print(json.dumps(normalized_offers_garching, indent=2, ensure_ascii=False))
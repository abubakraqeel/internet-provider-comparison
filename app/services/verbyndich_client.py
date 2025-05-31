# app/services/verbyndich_client.py
import os
import requests
import time
import json
import re

# --- Credentials and Constants ---
VERBYNDICH_BASE_URL = "https://verbyndich.gendev7.check24.fun/check24/data"
VERBYNDICH_API_KEY = os.getenv("VERBYNDICH_API_KEY")

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
        "raw_benefits_text": []
    }

    if not description_str:
        return details

    try: # Add a try-catch for parsing robustness
        price_match = re.search(r"Für nur (\d+)€ im Monat", description_str)
        if price_match:
            details["monthlyPriceEur"] = float(price_match.group(1))

        conn_type_match = re.search(r"eine (DSL|Cable|Fiber)-Verbindung", description_str)
        if conn_type_match:
            type_map = {"dsl": "DSL", "cable": "Cable", "fiber": "Fiber"}
            details["connectionType"] = type_map.get(conn_type_match.group(1).lower())

        speed_match = re.search(r"Geschwindigkeit von (\d+)\s*Mbit/s", description_str)
        if speed_match:
            details["downloadSpeedMbps"] = int(speed_match.group(1))

        term_match = re.search(r"Mindestvertragslaufzeit (\d+)\s*Monate", description_str)
        if term_match:
            details["contractTermMonths"] = int(term_match.group(1))

        limit_match = re.search(r"Ab (\d+)GB pro Monat wird die Geschwindigkeit gedrosselt", description_str)
        if limit_match:
            details["dataLimitGb"] = int(limit_match.group(1))
            details["raw_benefits_text"].append(f"Speed throttled after {details['dataLimitGb']}GB/month")

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

        onetime_discount_match = re.search(
            r"einmaligen Rabatt von (\d+)€.*?Der Mindestbestellwert beträgt (\d+)€",
            description_str
        )
        if onetime_discount_match:
            details["discount_onetime_eur"] = float(onetime_discount_match.group(1))
            details["discount_onetime_min_order_eur"] = float(onetime_discount_match.group(2))
            details["raw_benefits_text"].append(
                f"One-time discount of €{details['discount_onetime_eur']} (min. order €{details['discount_onetime_min_order_eur']})"
            )

        price_after_match = re.search(r"Ab dem 24\. Monat beträgt der monatliche Preis (\d+)€", description_str)
        if price_after_match:
            details["monthlyPriceEurAfter2Years"] = float(price_after_match.group(1))

        age_match = re.search(r"Personen unter (\d+)\s*Jahren verfügbar", description_str)
        if age_match:
            details["ageRestrictionMax"] = int(age_match.group(1))
            details["raw_benefits_text"].append(f"Young tariff: for persons under {details['ageRestrictionMax']} years")
            
    except Exception as e:
        print(f"Verbyndich Description Parse Error: {e} on description: {description_str[:100]}...")
    return details


def _normalize_verbyndich_offer(api_offer_item, parsed_desc_details):
    if not api_offer_item: 
        return None

    try:
        product_name_from_api = api_offer_item.get("product", "Verbyndich Offer")
        
        one_time_cost_eur = 0.00
        discount_val_eur = None
        discount_type_str = None

        if parsed_desc_details.get("discount_onetime_eur") is not None:
            discount_val_eur = parsed_desc_details["discount_onetime_eur"]
            discount_type_str = "One-time Discount"
        elif parsed_desc_details.get("discount_percentage") is not None:
            discount_type_str = "Percentage (Monthly)"
            discount_val_eur = parsed_desc_details.get("discount_percentage_max_eur") 

        benefits_string = ", ".join(parsed_desc_details.get("raw_benefits_text", []))
        if not benefits_string: benefits_string = "N/A"

        normalized_offer = {
            "providerName": "Verbyndich",
            "productName": product_name_from_api,
            "downloadSpeedMbps": parsed_desc_details.get("downloadSpeedMbps"),
            "uploadSpeedMbps": None,
            "monthlyPriceEur": parsed_desc_details.get("monthlyPriceEur"),
            "monthlyPriceEurAfter2Years": parsed_desc_details.get("monthlyPriceEurAfter2Years"),
            "contractTermMonths": parsed_desc_details.get("contractTermMonths"),
            "connectionType": parsed_desc_details.get("connectionType"),
            "benefits": benefits_string,
            "tv": parsed_desc_details.get("tv"),
            "discount": discount_val_eur,
            "discountType": discount_type_str,
            "installationServiceIncluded": None, # Not specified by VerbynDich descriptions
            "ageRestrictionMax": parsed_desc_details.get("ageRestrictionMax"),
            "dataLimitGb": parsed_desc_details.get("dataLimitGb"),
            "_provider_specific_id": product_name_from_api,
        }
        return normalized_offer
    except Exception as e:
        print(f"Verbyndich Normalization Error: {e} for item {api_offer_item.get('product')}")
        return None

def fetch_verbyndich_offers(address_details): 
    if not VERBYNDICH_API_KEY:
        print("Verbyndich Client ERROR: API Key (VERBYNDICH_API_KEY) is not configured.")
        return []

    address_str_body_parts = [
        address_details.get("strasse", "").strip(),
        address_details.get("hausnummer", "").strip(),
        address_details.get("stadt", "").strip(),
        address_details.get("postleitzahl", "").strip()
    ]
    if not all(address_str_body_parts):
        print(f"Verbyndich Client WARNING: Missing address components. Details: {address_details}")
        return [] # Return empty if essential address parts are missing
    address_str_body = ";".join(address_str_body_parts)

    all_normalized_offers = []
    current_page = 0
    max_pages_to_fetch = 20 # Keep a reasonable limit

    print(f"Verbyndich Client: Fetching data for address: '{address_str_body}'")

    try: # Outer try for the whole pagination process
        while current_page < max_pages_to_fetch:
            params = {"apiKey": VERBYNDICH_API_KEY, "page": current_page}
            headers = {"Content-Type": "text/plain;charset=UTF-8"}
            
            # Inner try for individual page request
            try:
                response = requests.post(
                    VERBYNDICH_BASE_URL,
                    data=address_str_body.encode('utf-8'),
                    params=params, headers=headers, timeout=15 # Timeout per page request
                )
                # print(f"Verbyndich Client: Page {current_page}, Status: {response.status_code}") # Debug
                response.raise_for_status()
                api_offer_item = response.json()
                
                if api_offer_item:
                    if api_offer_item.get("valid", False):
                        description = api_offer_item.get("description", "")
                        parsed_description_details = _parse_verbyndich_description(description)
                        normalized = _normalize_verbyndich_offer(api_offer_item, parsed_description_details)
                        if normalized:
                            all_normalized_offers.append(normalized)
                    
                    if api_offer_item.get("last", False):
                        break 
                else:
                    print(f"Verbyndich Client WARNING: Empty/non-JSON response on page {current_page}. Stopping pagination.")
                    break 
                current_page += 1
                # time.sleep(0.1) # Optional small delay between paginated requests

            except requests.exceptions.Timeout:
                print(f"Verbyndich Client ERROR: Timeout on page {current_page}.")
                break # Stop pagination on timeout
            except requests.exceptions.HTTPError as http_err:
                print(f"Verbyndich Client HTTP ERROR on page {current_page}: {http_err.response.status_code} - {http_err.response.text[:200]}")
                break # Stop pagination on HTTP error
            except ValueError as json_err: # JSONDecodeError
                print(f"Verbyndich Client JSON DECODE ERROR on page {current_page}: {json_err}. Response: {response.text[:200] if 'response' in locals() else 'N/A'}")
                break # Stop pagination on JSON error
            except requests.exceptions.RequestException as req_err:
                print(f"Verbyndich Client REQUEST EXCEPTION on page {current_page}: {req_err}")
                break # Stop on other request errors

    except Exception as e: # Catch-all for unexpected issues in the loop setup or outer logic
        print(f"Verbyndich Client UNEXPECTED ERROR during pagination: {e}")
        import traceback
        traceback.print_exc()
        return [] # Return whatever has been collected so far or empty list

    print(f"Verbyndich Client: Fetched and normalized {len(all_normalized_offers)} offers across {current_page + 1} page(s).")
    return all_normalized_offers

# --- if __name__ == '__main__': block ---
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    VERBYNDICH_API_KEY = os.getenv("VERBYNDICH_API_KEY") # Ensure it's loaded

    if not VERBYNDICH_API_KEY:
        print("Set VERBYNDICH_API_KEY environment variable.")
    else:
        address_test = {
            "strasse": "Musterstraße", "hausnummer": "10",
            "postleitzahl": "10115", "stadt": "Berlin"
        }
        print(f"\n--- Testing VerbynDich for Address: {address_test} ---")
        normalized_offers = fetch_verbyndich_offers(address_test)
        if normalized_offers:
            print(f"Total Normalized VerbynDich Offers: {len(normalized_offers)}")
            # print(json.dumps(normalized_offers, indent=2, ensure_ascii=False))
        else:
            print("No normalized offers from VerbynDich or an error occurred.")
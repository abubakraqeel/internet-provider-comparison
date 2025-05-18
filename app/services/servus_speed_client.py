import requests
from flask import current_app
from requests.auth import HTTPBasicAuth
import os

BASE_URL = "https://servus-speed.gendev7.check24.fun"
USERNAME = os.getenv("SERVUS_SPEED_USERNAME")
PASSWORD = os.getenv("SERVUS_SPEED_PASSWORD")

def _normalize_servus_speed_offer(product_detail_data, product_id):
    """
    Transforms raw product detail data from Servus Speed API
    into a standardized offer format.
    """
    if not product_detail_data:
        return None

    # Example: Extracting and transforming data based on typical API structures
    # You'll need to inspect the actual `product_detail_data` from Servus Speed
    # and map its fields to your common format.
    '''
    {'servusSpeedProduct': 
      {
      'providerName': 'Servus Basic 50',
      'productInfo': 
        {
        'speed': 50,
        'contractDurationInMonths': 12,
        'connectionType': 'DSL',
        'tv': 'ServusTV Standard',
        'limitFrom': 100,
        'maxAge': 31
        },
      'pricingDetails': {'monthlyCostInCent': 2683, 'installationService': False},
      'discount': 3727
      }
    }
    '''
    servusSpeedProduct = product_detail_data['servusSpeedProduct']
    actual_provider_name = "Servus Speed"

    product_name = servusSpeedProduct.get("providerName")

    product_info = servusSpeedProduct.get("productInfo", {})
    product_pricing = servusSpeedProduct.get("pricingDetails", {})

    if not product_info or not product_pricing:
        print(f"Servus Speed Normalization: Missing 'productInfo' or 'pricingDetails' for ID {product_id}.")
        print(f"Data received: {product_detail_data}")
        return None

    speed = product_info.get("speed")
    duration_months = product_info.get("contractDurationInMonths")
    connectiion_type = product_info.get("connectionType")
    tv = product_info.get("tv")
    limit_from = product_info.get("maxAge")
    max_age = product_info.get("maxAge")

    
    monthly_cost_cents = product_pricing.get("monthlyCostInCent")

    if monthly_cost_cents is None: # Essential field
        print(f"Servus Speed Normalization: Missing 'monthlyCostInCent' for ID {product_id}.")
        return None
    
    monthly_price_eur = monthly_cost_cents / 100.0

    installation_service = product_pricing.get("installationService")

    discount = servusSpeedProduct.get("discount")

    benefits = []

    
    if installation_service:
        benefits.append("Installation service included") # Or "available"
    
    if tv != "":
        benefits.append(f"TV package: {tv}")

    if limit_from is not None:
        # We need to guess the unit or find more info. Assuming GB for now.
        benefits.append(f"Data limit: {limit_from} GB/month") # This is an assumption

    if max_age is not None:
        benefits.append(f"Offer valid for customers up to {max_age} years old")
        # This is important for filtering later.

    normalized_offer = {
        "providerName": actual_provider_name, # Standardized provider name
        "productName": product_name,          # More specific tariff name
        "downloadSpeedMbps": speed,
        "uploadSpeedMbps": None,  # Not available in this schema for Servus Speed
        "monthlyPriceEur": monthly_price_eur,
        "contractTermMonths": duration_months,
        "connectionType": connectiion_type,
        "installationServiceIncluded": installation_service,
        "benefits": ", ".join(benefits) if benefits else "No specific benefits listed",
        "tvIncluded": tv,
        "ageRestrictionMax": max_age,
        "data limit": limit_from,
        "_provider_specific_id": product_id
    }

    return normalized_offer


def get_servus_offers(address):

    if not USERNAME or not PASSWORD:
        print("Servus Speed API credentials (USERNAME, PASSWORD) are not configured.")
        return [] # Or raise an exception

    auth = HTTPBasicAuth(USERNAME, PASSWORD)
    
    # --- Step 1: Get address specific product IDs ---

    available_products_url = f"{BASE_URL}/api/external/available-products"
    
    headers = {
        "Content-Type": "application/json"
    }

    product_ids = []
    try:
        print(f"Servus Speed: Requesting available products with payload: {address}")
        response_step1 = requests.post(available_products_url, json={"address": address}, headers=headers, auth=auth, timeout=15)

        response_step1.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        product_ids = response_step1.json()['availableProducts'] # Should be a list of strings: ["id1", "id2", ...]
    
        if not isinstance(product_ids, list):
            print(f"Servus Speed: Expected list of product IDs, but got: {type(product_ids)}. Response: {product_ids}")
            return []
        
        print(f"Servus Speed: Received product IDs: {product_ids}")

    except requests.exceptions.Timeout:
        print("Servus Speed: Timeout fetching available products.")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Servus Speed: HTTP error fetching available products: {e.response.status_code} - {e.response.text}")
        return []
    except requests.exceptions.RequestException as e: # Other network errors
        print(f"Servus Speed: Request error fetching available products: {e}")
        return []
    except ValueError as e: # JSONDecodeError
        print(f"Servus Speed: Could not decode JSON response for available products: {e}")
        return []
    
    if not product_ids:
        print("Servus Speed: No product IDs found for the address.")
        return []

     # --- Step 2: Get details for each product ID ---

    all_normalized_offers = []
    all_product_offers = []
    product_details_base_url = f"{BASE_URL}/api/external/product-details/"

    for product_id in product_ids:
        if not isinstance(product_id, str) or not product_id.strip():
            print(f"Servus Speed: Invalid product ID found: '{product_id}'. Skipping.")
            continue
        
        detail_url = f"{product_details_base_url}{product_id}"
        
        try:
            print(f"Servus Speed: Requesting details for product ID: {product_id}")

            response_step2 = requests.post(detail_url, json={"address": address}, headers=headers, auth=auth, timeout=15)
            response_step2.raise_for_status()

            product_detail_data = response_step2.json() #works!
            normalized_offer = _normalize_servus_speed_offer(product_detail_data, product_id)
            if normalized_offer:
                all_normalized_offers.append(normalized_offer)
            else:
                # Normalization might return None if offer is not suitable (e.g., not available)
                print(f"Servus Speed: Product {product_id} was not included after normalization (e.g. not available).")

        except requests.exceptions.Timeout:
            print(f"Servus Speed: Timeout fetching details for product ID {product_id}.")
            # Decide if you want to skip this offer or stop altogether
        except requests.exceptions.HTTPError as e:
            print(f"Servus Speed: HTTP error for product ID {product_id}: {e.response.status_code} - {e.response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Servus Speed: Request error for product ID {product_id}: {e}")
        except ValueError as e: # JSONDecodeError
            print(f"Servus Speed: Could not decode JSON for product details of {product_id}: {e}")
            
    print(f"Servus Speed: Successfully fetched and normalized {len(all_normalized_offers)} offers.")
    return all_normalized_offers

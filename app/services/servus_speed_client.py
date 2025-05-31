import requests
# from flask import current_app # Not used in this snippet directly
from requests.auth import HTTPBasicAuth
import os
from concurrent.futures import ThreadPoolExecutor, as_completed # Added for concurrency
from datetime import datetime
import time

BASE_URL = "https://servus-speed.gendev7.check24.fun" # Corrected from your code "https://servus-speed..." to "https://servusspeed..." as per openapi
USERNAME = os.getenv("SERVUS_SPEED_USERNAME")
PASSWORD = os.getenv("SERVUS_SPEED_PASSWORD")

def _normalize_servus_speed_offer(product_detail_data, product_id):
    """
    Transforms raw product detail data from Servus Speed API
    into a standardized offer format.
    """
    if not product_detail_data:
        return None

    servusSpeedProduct = product_detail_data.get('servusSpeedProduct')
    if not servusSpeedProduct:
        print(f"Servus Speed Normalization: 'servusSpeedProduct' key missing for ID {product_id}.")
        return None
        
    actual_provider_name = "Servus Speed"
    product_name = servusSpeedProduct.get("providerName")

    product_info = servusSpeedProduct.get("productInfo", {})
    product_pricing = servusSpeedProduct.get("pricingDetails", {})

    if not product_info or not product_pricing: # product_info or product_pricing can be None if .get returns None
        print(f"Servus Speed Normalization: Missing 'productInfo' or 'pricingDetails' for ID {product_id}.")
        print(f"Data received: {product_detail_data}")
        return None

    speed = product_info.get("speed")
    duration_months = product_info.get("contractDurationInMonths")
    connection_type = product_info.get("connectionType") 
    tv = product_info.get("tv")
    limit_from_val = product_info.get("limitFrom")
    max_age = product_info.get("maxAge")

    monthly_cost_cents = product_pricing.get("monthlyCostInCent")

    if monthly_cost_cents is None:
        print(f"Servus Speed Normalization: Missing 'monthlyCostInCent' for ID {product_id}.")
        return None
    
    monthly_price_eur = monthly_cost_cents / 100.0
    installation_service = product_pricing.get("installationService")
    discount = servusSpeedProduct.get("discount")

    benefits = []
    if installation_service:
        benefits.append("Installation service included")
    
    if tv and tv.strip() != "": # Check if tv is not None and not empty string
        benefits.append(f"TV package: {tv}")

    if limit_from_val is not None:
        benefits.append(f"Data limit: {limit_from_val} GB/month")

    if max_age is not None:
        benefits.append(f"Offer valid for customers up to {max_age} years old")
    '''{
    "_provider_specific_id": "a3cbbf1b918bec17",
    "ageRestrictionMax": 31,
    "benefits": "TV package: ServusFlix Pro Max Ultra, Data limit: 200 GB/month, Offer valid for customers up to 31 years old",
    "connectionType": "Fiber",
    "contractTermMonths": 36,
    "dataLimitGb": 200,
    "discount": 3727,
    "downloadSpeedMbps": 350,
    "installationServiceIncluded": false,
    "monthlyPriceEur": 54.83,
    "productName": "Servus Extreme 350",
    "providerName": "Servus Speed",
    "tvIncluded": "ServusFlix Pro Max Ultra",
    "uploadSpeedMbps": null
  }'''
    normalized_offer = {
        "providerName": actual_provider_name,
        "productName": product_name,
        "downloadSpeedMbps": speed,
        "uploadSpeedMbps": None,
        "monthlyPriceEur": monthly_price_eur,
        "contractTermMonths": duration_months,
        "connectionType": connection_type,
        "installationServiceIncluded": installation_service,
        "benefits": ", ".join(benefits) if benefits else "No specific benefits listed",
        "tvIncluded": tv if tv and tv.strip() != "" else None, # More explicit None if no TV
        "ageRestrictionMax": max_age,
        "dataLimitGb": limit_from_val, # Changed key for clarity
        "_provider_specific_id": product_id,
        "discount": discount
    }
    return normalized_offer


def _fetch_single_product_detail(product_id, address_payload, auth_obj, headers_obj):
    """
    Fetch a single product detail page (step 2) using the provided
    auth object, headers object, and address payload.

    Returns a normalized offer dictionary if the response is OK, or
    None if there was an error in the request or JSON parsing.
    """
    start_time = time.time()

    product_details_base_url = f"{BASE_URL}/api/external/product-details/"
    detail_url = f"{product_details_base_url}{product_id}"
    
    try:
        # print(f"Servus Speed (Thread for {product_id} at {time.strftime('%H:%M:%S')}): Requesting details...")
        response_step2 = requests.post(
            detail_url,
            json={"address": address_payload}, 
            headers=headers_obj,
            auth=auth_obj,
            # timeout=25
        )
        response_received_time = time.time()
        # print(f"Servus Speed (Thread for {product_id} at {time.strftime('%H:%M:%S')}): Response received in {response_received_time - start_time:.2f}s. Status: {response_step2.status_code}")
        response_step2.raise_for_status()
        product_detail_data = response_step2.json()
        json_parsed_time = time.time()
        # print(f"Servus Speed (Thread for {product_id} at {time.strftime('%H:%M:%S')}): JSON parsed in {json_parsed_time - response_received_time:.2f}s.")

        normalized_offer = _normalize_servus_speed_offer(product_detail_data, product_id)
        if normalized_offer:
            return normalized_offer
        else:
            print(f"Servus Speed (Thread for {product_id}): Product not included after normalization.")
            return None

    except requests.exceptions.Timeout:
        print(f"Servus Speed (Thread for {product_id}): Timeout fetching details.")
    except requests.exceptions.HTTPError as e:
        print(f"Servus Speed (Thread for {product_id}): HTTP error: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Servus Speed (Thread for {product_id}): Request error: {e}")
    except ValueError as e: # JSONDecodeError
        print(f"Servus Speed (Thread for {product_id}): Could not decode JSON: {e}")
    except Exception as e: # Catch-all for unexpected errors in thread
        print(f"Servus Speed (Thread for {product_id}): Unexpected error: {e}")
    finally: # Ensure end time is logged even if an error occurs
        end_time = time.time()
        # print(f"Servus Speed (Thread for {product_id} at {time.strftime('%H:%M:%S')}): Task finished in {end_time - start_time:.2f}s total.")
    return None 


def get_servus_offers(address): # 'address' here is the payload for the API, e.g. {"strasse": ..., "hausnummer": ...}

    if not USERNAME or not PASSWORD:
        print("Servus Speed API credentials (USERNAME, PASSWORD) are not configured.")
        return []

    auth = HTTPBasicAuth(USERNAME, PASSWORD)
    headers = {"Content-Type": "application/json"} # Defined once

    # --- Step 1: Get address specific product IDs (remains sequential) ---
    available_products_url = f"{BASE_URL}/api/external/available-products"
    product_ids = []
    try:
        print(f"Servus Speed (Step 1) at {datetime.now()}: Requesting available products with payload: {address}")
        response_step1 = requests.post(
            available_products_url,
            json={"address": address}, 
            headers=headers,
            auth=auth,
            timeout=15
        )
        response_step1.raise_for_status()
        
        product_ids_data = response_step1.json()
        product_ids = product_ids_data.get("availableProducts", [])
    
        if not isinstance(product_ids, list):
            print(f"Servus Speed (Step 1): Expected list of product IDs, but got: {type(product_ids)}. Response: {product_ids_data}")
            return []
        
        print(f"Servus Speed (Step 1): Received {len(product_ids)} product IDs: {product_ids}")

    except requests.exceptions.Timeout:
        print("Servus Speed (Step 1): Timeout fetching available products.")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"Servus Speed (Step 1): HTTP error fetching available products: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"Servus Speed (Step 1): Unexpected error: {e}")
        return []
    
    if not product_ids:
        print("Servus Speed: No product IDs found for the address.")
        return []

    # --- Step 2: Get details for each product ID CONCURRENTLY ---
    all_normalized_offers = []
    # max_workers: Number of threads. Adjust based on testing.
    # For I/O-bound tasks, more workers can be beneficial up to a point.
    with ThreadPoolExecutor(max_workers=5) as executor:

        # Create a list of future objects
        future_to_product_id = {
            executor.submit(_fetch_single_product_detail, pid, address, auth, headers): pid 
            for pid in product_ids if isinstance(pid, str) and pid.strip() # Basic validation of product_id
        }
        
        print(f"Servus Speed (Step 2): Submitted {len(future_to_product_id)} tasks to ThreadPoolExecutor.")

        for future in as_completed(future_to_product_id):
            # product_id_completed = future_to_product_id[future] # For logging if needed
            try:
                result = future.result() # This will raise an exception if one occurred in the thread
                if result:
                    all_normalized_offers.append(result)
            except Exception as exc:
                # This catches exceptions from _fetch_single_product_detail if not caught internally,
                # or from future.result() itself if the task was cancelled, etc.
                # pid_for_exc = future_to_product_id[future] # Get ID for logging
                print(f"Servus Speed (Step 2): A task for a product ID generated an exception: {exc}")

    print(f"Servus Speed at {datetime.now()}: Successfully fetched and normalized {len(all_normalized_offers)} offers out of {len(product_ids)} product IDs using threads.")
    return all_normalized_offers

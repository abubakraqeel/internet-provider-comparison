from flask import Blueprint, jsonify, request
from app.services.servus_speed_client import get_servus_offers
from app.services.byteme_client import get_byteme_offers
from concurrent.futures import ThreadPoolExecutor, as_completed

main_routes = Blueprint('main_rotues', __name__)

@main_routes.route("/api/hello", methods=["GET"])
def hello():
    return jsonify({"message": "Hello, browser!"})


@main_routes.route("/api/offers", methods=["POST"])
def get_offers():
    data = request.get_json()

    if not data or "address" not in data:
        return jsonify({"error": "Missing address"}), 400

    address = data["address"]
    print("Address payload:", address)

    # offers = get_servus_offers(address)
    # return jsonify(offers)
    all_offers_from_all_providers = []
    
    # List of provider functions to call. Each function should take 'address_payload'
    # and return a list of normalized offers or an empty list on error.
    provider_tasks = {
        "ServusSpeed": get_servus_offers,
        "ByteMe": get_byteme_offers,
        # "WebWunder": get_webwunder_offers,
        # "PingPerfect": get_ping_perfect_offers,
        # "VerbynDich": get_verbyndich_offers,
    }

    # Use ThreadPoolExecutor to call all provider functions concurrently
    # You can adjust max_workers based on the number of providers and their expected behavior.
    # If a provider function itself uses threads (like Servus Speed for its details),
    # be mindful of nested threading, though it often works fine.
    with ThreadPoolExecutor(max_workers=len(provider_tasks) or 1) as executor:
        future_to_provider = {
            executor.submit(task_func, address): provider_name 
            for provider_name, task_func in provider_tasks.items()
        }
        
        for future in as_completed(future_to_provider):
            provider_name = future_to_provider[future]
            try:
                provider_offers = future.result(timeout=45) # Add a timeout for each provider's total processing
                if provider_offers: # It will be a list of offers
                    all_offers_from_all_providers.extend(provider_offers)
                    print(f"API Route: Successfully got {len(provider_offers)} offers from {provider_name}")
                else:
                    print(f"API Route: No offers returned from {provider_name} (or empty list was intended).")
            except TimeoutError: # This is for future.result(timeout=X)
                 print(f"API Route: Fetching offers from {provider_name} timed out after 45 seconds.")
            except Exception as exc:
                print(f"API Route: {provider_name} generated an exception: {exc}")
                # Optionally, you could add a placeholder error object to the response
                # for this provider, e.g., {"providerName": provider_name, "error": str(exc)}
                # so the frontend knows it failed. For now, just prints error.

    print(f"API Route: Total combined offers from all providers: {len(all_offers_from_all_providers)}")
    
    # Here, you might sort/filter `all_offers_from_all_providers` before sending
    # Or the frontend can handle that.

    return jsonify(all_offers_from_all_providers)
from flask import Blueprint, jsonify, request
from app.services.ping_perfect_client import get_ping_perfect_offers
from app.services.servus_speed_client import get_servus_offers
from app.services.byteme_client import get_byteme_offers
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.services.verbyndich_client import get_verbyndich_offers
from app.services.webwunder_client import get_webwunder_offers
import uuid # For generating unique IDs
import json # For loading/dumping JSON
from app import db # Import the db instance from app/__init__.py (or app.models if you move it)
from app import SharedLink # Import your SharedLink model (assuming it's in app/models.py)
                              # If SharedLink is in app/__init__.py, you might need to adjust import
                              # e.g., from app import SharedLink


main_routes = Blueprint('main_rotues', __name__)


@main_routes.route("/api/offers", methods=["POST", 'OPTIONS'])
def get_offers():


    if request.method == 'OPTIONS':
        # This block should ideally not be hit if flask-cors is working globally.
        # If it is hit, it means flask-cors didn't fully handle the preflight.
        print("Flask Route: Manually hit OPTIONS block. This is unexpected if global CORS(app) is working.")
        # Return a minimal valid response. flask-cors *might* still augment this.
        return jsonify(message="OPTIONS preflight processed by route"), 200

    # --- POST Request Logic ---
    print(f"--- Received POST to /api/offers ---")
    print(f"Request Content-Type Header: {request.headers.get('Content-Type')}")
    print(f"Flask's interpretation (request.is_json): {request.is_json}")

    if not request.is_json:
        # ... your existing 400 error handling ...
        return jsonify({"error": "Request must be JSON"}), 400
    address = request.get_json()
 # `data` IS the address payload

    # Add some basic validation for the payload itself
    if not isinstance(address, dict) or "strasse" not in address: # Example check
        print(f"Flask Route: ERROR - Invalid address structure or missing 'strasse'. Payload: {address}")
        return jsonify({"error": "Invalid address payload structure or missing required fields."}), 400

    print("Address payload successfully received by Flask:", address)

    # offers = get_servus_offers(address)
    # return jsonify(offers)
    all_offers_from_all_providers = []
    
    # List of provider functions to call. Each function should take 'address'
    # and return a list of normalized offers or an empty list on error.
    provider_tasks = {
        "ServusSpeed": get_servus_offers,
        "ByteMe": get_byteme_offers,
        "WebWunder": get_webwunder_offers,
        "PingPerfect": get_ping_perfect_offers, # Use lambda to pass extra arg
        "VerbynDich": get_verbyndich_offers,
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


# --- NEW ROUTES FOR SHARING ---

@main_routes.route('/api/share', methods=['POST'])
def create_share_link():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    
    offers_data = request.get_json() # This should be the array of normalized offers

    if not isinstance(offers_data, list):
        return jsonify({"error": "Payload must be a list of offers"}), 400
    
    if not offers_data: # Empty list of offers
        return jsonify({"error": "Cannot share an empty list of offers"}), 400

    try:
        # Generate a short, reasonably unique ID
        share_id = uuid.uuid4().hex[:10] # Example: 10-char hex string
        
        # Ensure ID is unique (very unlikely collision with 10 hex chars, but good practice for critical systems)
        # For this challenge, we can assume it's unique enough.
        # while SharedLink.query.get(share_id):
        #     share_id = uuid.uuid4().hex[:10]

        offers_json_string = json.dumps(offers_data) # Convert list of dicts to JSON string

        new_shared_link = SharedLink(id=share_id, offers_json=offers_json_string)
        db.session.add(new_shared_link)
        db.session.commit()
        
        print(f"API Route: Created share link with ID: {share_id}")
        return jsonify({"shareId": share_id, "message": "Share link created successfully"}), 201

    except Exception as e:
        db.session.rollback()
        print(f"API Route: Error creating share link: {e}")
        # import traceback; traceback.print_exc() # For detailed error
        return jsonify({"error": "Failed to create share link", "details": str(e)}), 500


@main_routes.route('/api/share/<share_id>', methods=['GET'])
def get_shared_link_data(share_id):
    if not share_id or len(share_id) > 16: # Basic validation
        return jsonify({"error": "Invalid share ID format"}), 400

    try:
        shared_link_entry = SharedLink.query.get(share_id)

        if shared_link_entry:
            offers_data = json.loads(shared_link_entry.offers_json) # Convert JSON string back to Python list
            print(f"API Route: Retrieved shared link data for ID: {share_id}")
            return jsonify(offers_data), 200
        else:
            print(f"API Route: Share link not found for ID: {share_id}")
            return jsonify({"error": "Share link not found"}), 404
            
    except json.JSONDecodeError:
        print(f"API Route: Error decoding stored JSON for share ID: {share_id}")
        return jsonify({"error": "Corrupted share data"}), 500
    except Exception as e:
        print(f"API Route: Error retrieving share link: {e}")
        return jsonify({"error": "Failed to retrieve share link", "details": str(e)}), 500

# --- END NEW ROUTES FOR SHARING ---
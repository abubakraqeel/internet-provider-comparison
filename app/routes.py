
from flask import Blueprint, jsonify, request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from app.services.ping_perfect_client import fetch_ping_perfect_offers
from app.services.servus_speed_client import get_servus_offers 
from app.services.byteme_client import get_byteme_offers 
from app.services.verbyndich_client import fetch_verbyndich_offers
from app.services.webwunder_client import fetch_webwunder_offers
import uuid
import json
from app import db, SharedLink 

main_routes = Blueprint('main_routes', __name__)

@main_routes.route("/api/offers", methods=["POST"])
def get_offers_route(): 
    print(f"--- API Route: /api/offers POST request received at {time.strftime('%H:%M:%S')} ---")
    
    if not request.is_json:
        print("API Route ERROR: Request must be JSON")
        return jsonify({"error": "Request must be JSON"}), 400
    
    address_payload = request.get_json()
    if not isinstance(address_payload, dict) or not all(k in address_payload for k in ["strasse", "hausnummer", "postleitzahl", "stadt"]):
        print(f"API Route ERROR: Invalid address payload. Received: {address_payload}")
        return jsonify({"error": "Invalid address payload structure or missing required fields."}), 400

    print(f"API Route: Processing address: {address_payload}")
    all_offers_aggregated = []
    
    # Define tasks for each provider
    # For WebWunder, we need to call it for multiple connection types
    tasks_to_submit = []

    # Servus Speed
    tasks_to_submit.append({"name": "ServusSpeed", "func": get_servus_offers, "args": (address_payload,)})
    # ByteMe
    tasks_to_submit.append({"name": "ByteMe", "func": get_byteme_offers, "args": (address_payload,)})
    # Ping Perfect 
    tasks_to_submit.append({"name": "PingPerfect", "func": fetch_ping_perfect_offers, "args": (address_payload, True)})
    # VerbynDich
    tasks_to_submit.append({"name": "VerbynDich", "func": fetch_verbyndich_offers, "args": (address_payload,)})
    
    # WebWunder - create tasks for each connection type
    webwunder_conn_types = ["DSL", "CABLE", "FIBER"] # "MOBILE" often has no address check
    for conn_type in webwunder_conn_types:
        tasks_to_submit.append({
            "name": f"WebWunder-{conn_type}", 
            "func": fetch_webwunder_offers, 
            "args": (address_payload, conn_type, True) # address, conn_type, installation
        })

    
    OVERALL_FETCH_TIMEOUT_SECONDS = 20

    with ThreadPoolExecutor(max_workers=len(tasks_to_submit) or 1) as executor:
        future_to_task = {
            executor.submit(task["func"], *task["args"]): task 
            for task in tasks_to_submit
        }
        
        # print(f"API Route: Submitted {len(future_to_task)} tasks to thread pool.")

        for future in as_completed(future_to_task):
            task_info = future_to_task[future]
            provider_name_for_log = task_info["name"]
            try:
                # Individual task timeout (future.result(timeout))
                # This ensures one very slow provider doesn't block indefinitely
                # even if its internal HTTP timeouts fail.
                # It needs to be less than OVERALL_FETCH_TIMEOUT_SECONDS
                provider_offers_list = future.result(timeout=35) 
                
                if isinstance(provider_offers_list, list) and provider_offers_list:
                    all_offers_aggregated.extend(provider_offers_list)
                    # print(f"API Route INFO: Added {len(provider_offers_list)} offers from {provider_name_for_log}.")
                elif isinstance(provider_offers_list, list): # Empty list returned
                    print(f"API Route INFO: No offers returned from {provider_name_for_log} (empty list).")
                else: # Should not happen if clients return [] on error
                    print(f"API Route WARNING: {provider_name_for_log} returned non-list: {type(provider_offers_list)}")
            
            except TimeoutError: # This is for future.result(timeout=X)
                 print(f"API Route ERROR: Fetching from {provider_name_for_log} with future.result() timed out after 35s.")
            except Exception as exc:
                print(f"API Route ERROR: {provider_name_for_log} client generated an exception: {exc}")
                import traceback
                traceback.print_exc() # Log full traceback for debugging

    print(f"API Route: Total combined offers returned: {len(all_offers_aggregated)}. Sending response at {time.strftime('%H:%M:%S')}.")
    return jsonify(all_offers_aggregated)


@main_routes.route('/api/share', methods=['POST'])
def create_share_link():
    # ... (your existing /api/share POST logic - ensure it has its own robust error handling for DB operations) ...
    print("--- API Route: /api/share POST request ---")
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400
    offers_data = request.get_json()
    if not isinstance(offers_data, list):
        return jsonify({"error": "Payload must be a list of offers"}), 400
    if not offers_data:
        return jsonify({"error": "Cannot share an empty list of offers"}), 400
    try:
        share_id = uuid.uuid4().hex[:10] 
        offers_json_string = json.dumps(offers_data)
        new_shared_link = SharedLink(id=share_id, offers_json=offers_json_string)
        db.session.add(new_shared_link)
        db.session.commit()
        print(f"API Route INFO: Created share link ID: {share_id}")
        return jsonify({"shareId": share_id, "message": "Share link created successfully"}), 201
    except Exception as e:
        db.session.rollback()
        print(f"API Route ERROR creating share link: {e}")
        return jsonify({"error": "Failed to create share link", "details": str(e)}), 500


@main_routes.route('/api/share/<share_id>', methods=['GET'])
def get_shared_link_data(share_id):
    # ... (your existing /api/share/<share_id> GET logic - ensure robust error handling) ...
    print(f"--- API Route: /api/share/{share_id} GET request ---")
    if not share_id or len(share_id) > 16:
        return jsonify({"error": "Invalid share ID format"}), 400
    try:
        shared_link_entry = SharedLink.query.get(share_id)
        if shared_link_entry:
            offers_data = json.loads(shared_link_entry.offers_json)
            print(f"API Route INFO: Retrieved shared data for ID: {share_id}")
            return jsonify(offers_data), 200
        else:
            print(f"API Route WARNING: Share link not found for ID: {share_id}")
            return jsonify({"error": "Share link not found"}), 404
    except json.JSONDecodeError:
        print(f"API Route ERROR: Decoding stored JSON for share ID: {share_id}")
        return jsonify({"error": "Corrupted share data"}), 500
    except Exception as e:
        print(f"API Route ERROR retrieving share link {share_id}: {e}")
        return jsonify({"error": "Failed to retrieve share link", "details": str(e)}), 500
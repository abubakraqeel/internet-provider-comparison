from flask import Blueprint, jsonify, request
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from app.services.ping_perfect_client import fetch_ping_perfect_offers
from app.services.servus_speed_client import get_servus_offers
from app.services.byteme_client import get_byteme_offers
from app.services.verbyndich_client import fetch_verbyndich_offers
from app.services.webwunder_client import fetch_webwunder_offers


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
    
    tasks_to_submit = []
    tasks_to_submit.append({"name": "ServusSpeed", "func": get_servus_offers, "args": (address_payload,)})
    tasks_to_submit.append({"name": "ByteMe", "func": get_byteme_offers, "args": (address_payload,)})
    tasks_to_submit.append({"name": "PingPerfect", "func": fetch_ping_perfect_offers, "args": (address_payload, True)})
    tasks_to_submit.append({"name": "VerbynDich", "func": fetch_verbyndich_offers, "args": (address_payload,)})
    
    webwunder_conn_types = ["DSL", "CABLE", "FIBER"]
    for conn_type in webwunder_conn_types:
        tasks_to_submit.append({
            "name": f"WebWunder-{conn_type}", 
            "func": fetch_webwunder_offers, 
            "args": (address_payload, conn_type, True)
        })
    
    with ThreadPoolExecutor(max_workers=len(tasks_to_submit) or 1) as executor:
        future_to_task = {
            executor.submit(task["func"], *task["args"]): task 
            for task in tasks_to_submit
        }
        
        for future in as_completed(future_to_task):
            task_info = future_to_task[future]
            provider_name_for_log = task_info["name"]
            try:
                provider_offers_list = future.result(timeout=35) 
                if isinstance(provider_offers_list, list) and provider_offers_list:
                    all_offers_aggregated.extend(provider_offers_list)
                elif isinstance(provider_offers_list, list):
                    print(f"API Route INFO: No offers returned from {provider_name_for_log} (empty list).")
                else: 
                    print(f"API Route WARNING: {provider_name_for_log} returned non-list: {type(provider_offers_list)}")
            except TimeoutError:
                 print(f"API Route ERROR: Fetching from {provider_name_for_log} with future.result() timed out after 35s.")
            except Exception as exc:
                print(f"API Route ERROR: {provider_name_for_log} client generated an exception: {exc}")
                import traceback
                traceback.print_exc()

    print(f"API Route: Total combined offers returned: {len(all_offers_aggregated)}. Sending response at {time.strftime('%H:%M:%S')}.")
    return jsonify(all_offers_aggregated)



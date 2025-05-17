from flask import Blueprint, jsonify
from app.services.servus_speed_client import fetch_servus_speed_offers
main_routes = Blueprint('main_rotues', __name__)

@main_routes.route('/hello')
def hello():
    return "Hello world from routes.py using Blueprint"


@main_routes.route("/api/offers", methods=["GET"])
def get_offers():
    # TEMPORARY: Hardcoded test address
    test_address = {
        "street": "Musterstraße",
        "houseNumber": "12",
        "city": "Berlin",
        "plz": "10115"
    }

    offers = fetch_servus_speed_offers(test_address)
    return jsonify(offers)
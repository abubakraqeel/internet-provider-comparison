from flask import Blueprint, jsonify, request
from app.services.servus_speed_client import get_servus_offers

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

    offers = get_servus_offers(address)
    return jsonify(offers)

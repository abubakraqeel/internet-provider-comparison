from flask import Flask
from .routes import main_routes
from dotenv import load_dotenv
import os
from flask_cors import CORS

def create_app():
    load_dotenv("/Users/abubakraqeel/dev/check24/.env")
    
    app = Flask(__name__)
    CORS(app) # Simplest, most permissive for now. This should handle OPTIONS for all routes.
    print("Flask __init__: CORS(app) applied.")

    app.register_blueprint(main_routes)
    print(f"Flask __init__: Registered blueprint '{main_routes.name}'")
    return app
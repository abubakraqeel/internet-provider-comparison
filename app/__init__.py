# app/__init__.py
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv


def create_app():
   
    static_folder_path = '/app/frontend/build' 
    print(f"Flask __init__ (Docker): Static folder path set to: {static_folder_path}")

    app = Flask(__name__, static_folder=static_folder_path)
    CORS(app) 

    # --- Database Configuration REMOVED --- (as per your previous request)
    print("Flask __init__: Database configuration is REMOVED for no-DB deployment.")

    from .routes import main_routes
    app.register_blueprint(main_routes)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if not app.static_folder or not os.path.isdir(app.static_folder):
            print(f"ERROR: Static folder '{app.static_folder}' not found or not a directory.")
            return "Static folder configuration error.", 500
        
        # Check if the requested path exists in the static folder
        requested_path = os.path.join(app.static_folder, path)
        if path != "" and os.path.exists(requested_path) and os.path.isfile(requested_path):
            return send_from_directory(app.static_folder, path)
        else:
            # Fallback to index.html for SPA routing
            index_path = os.path.join(app.static_folder, 'index.html')
            if not os.path.exists(index_path):
                print(f"ERROR: index.html not found in static folder '{app.static_folder}'.")
                return "Application not found (index.html missing).", 404
            return send_from_directory(app.static_folder, 'index.html')
    
    print("Flask __init__: create_app finished (no database mode).")
    return app
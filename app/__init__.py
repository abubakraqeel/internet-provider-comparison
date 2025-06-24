# app/__init__.py
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv



def create_app():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        print(f"Flask __init__: Loading .env file from {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        print(f"Flask __init__: .env file not found at {dotenv_path}, relying on system env vars.")

    static_folder_path = os.path.join(project_root, 'frontend', 'build') 
    app = Flask(__name__, static_folder=static_folder_path) 
    CORS(app) 

    
    from .routes import main_routes 
    app.register_blueprint(main_routes)

    # --- Serve React App ---
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        # Check if app.static_folder exists and is a directory
        if not app.static_folder or not os.path.isdir(app.static_folder):
            print(f"ERROR: Static folder '{app.static_folder}' not found or not a directory.")
            return "Static folder configuration error.", 500

        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            # Check if index.html exists before serving
            index_path = os.path.join(app.static_folder, 'index.html')
            if not os.path.exists(index_path):
                print(f"ERROR: index.html not found in static folder '{app.static_folder}'.")
                return "Application not found (index.html missing).", 404
            return send_from_directory(app.static_folder, 'index.html')
    
  

    print("Flask __init__: create_app finished (no database mode).")
    return app
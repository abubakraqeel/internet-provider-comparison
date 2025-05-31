# app/__init__.py
import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

db = SQLAlchemy()

class SharedLink(db.Model):
    __tablename__ = 'shared_links'
    id = db.Column(db.String(16), primary_key=True)
    offers_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<SharedLink {self.id}>'

def create_app():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        print(f"Flask __init__: Loading .env file from {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        print(f"Flask __init__: .env file not found at {dotenv_path}, relying on system env vars.")

    static_folder = os.path.join(project_root, 'frontend', 'build')
    app = Flask(__name__, static_folder=static_folder)
    CORS(app) # Ensure CORS is enabled, especially if frontend and backend are on different subdomains or ports during dev

    # --- Database Configuration ---
    # Decide whether to use MySQL (on PythonAnywhere) or SQLite (local fallback)
    USE_MYSQL_ENV = os.environ.get('USE_MYSQL', 'false').lower() == 'true' # Add USE_MYSQL=true on PythonAnywhere env vars

    if USE_MYSQL_ENV:
        DB_USERNAME = os.environ.get('DB_USERNAME')
        DB_PASSWORD = os.environ.get('DB_PASSWORD')
        DB_HOST = os.environ.get('DB_HOST')
        DB_NAME = os.environ.get('DB_NAME')

        if not all([DB_USERNAME, DB_PASSWORD, DB_HOST, DB_NAME]):
            print("ERROR: Missing one or more MySQL environment variables (DB_USERNAME, DB_PASSWORD, DB_HOST, DB_NAME)")
            # Fallback to SQLite or raise an error, depending on your preference
            app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(project_root, 'error_shared_links.db')
            print(f"Flask __init__: Falling back to SQLite due to missing MySQL env vars.")
        else:
            app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+mysqlconnector://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
            print(f"Flask __init__: Attempting to use MySQL.")
    else:
        # Default to SQLite (e.g., for local development)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(project_root, 'shared_links.db')
        print(f"Flask __init__: Using SQLite.")
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
                'pool_recycle': 280,  # Recycle connections older than 280 seconds (just under 5 mins)
                'pool_pre_ping': True # Enable pre-ping to check connection validity
            }

    print(f"Flask __init__: SQLALCHEMY_DATABASE_URI set to: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from .routes import main_routes
    app.register_blueprint(main_routes)

    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def serve(path):
        if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            return send_from_directory(app.static_folder, 'index.html')

    with app.app_context():
        print("Flask __init__: Attempting db.create_all()...")
        try:
            db.create_all()
            print("Flask __init__: Database tables checked/created successfully.")
        except Exception as e:
            print(f"Flask __init__: Error during db.create_all(): {e}")
            # This is important to see if DB connection fails

    return app
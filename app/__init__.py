# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv # Make sure this is imported

# Initialize SQLAlchemy at the module level
db = SQLAlchemy()

# Define Model here so it's known when create_app is called and db.create_all() runs
class SharedLink(db.Model):
    __tablename__ = 'shared_links' # Explicit table name is good
    id = db.Column(db.String(16), primary_key=True)
    offers_json = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now()) # server_default uses DB's now

    def __repr__(self):
        return f'<SharedLink {self.id}>'

def create_app():
    # --- Load .env ---
    # Assuming .env is in the project root (one level up from 'app' directory)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    dotenv_path = os.path.join(project_root, '.env')
    if os.path.exists(dotenv_path):
        print(f"Flask __init__: Loading .env file from {dotenv_path}")
        load_dotenv(dotenv_path)
    else:
        print(f"Flask __init__: .env file not found at {dotenv_path}, relying on system env vars.")

    app = Flask(__name__)
    CORS(app)
    
    # --- Database Configuration ---
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(project_root, 'shared_links.db') # DB in project root
    print(f"Flask __init__: SQLALCHEMY_DATABASE_URI set to: {app.config['SQLALCHEMY_DATABASE_URI']}")
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app) 
    
    # --- Import and Register Blueprints ---
    from .routes import main_routes 
    app.register_blueprint(main_routes)
    # print(f"Flask __init__: Registered blueprint '{api_bp.name}'") # Optional log
    
    # --- Create Database Tables ---
    # This needs to be within an app context to access app.config for the DB URI
    with app.app_context():
        print("Flask __init__: Attempting db.create_all()...")
        db.create_all() 
        print("Flask __init__: Database tables checked/created successfully.")

    return app
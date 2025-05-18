from flask import Flask
from .routes import main_routes
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv("/Users/abubakraqeel/dev/check24/.env")
    
    app = Flask(__name__)
    app.register_blueprint(main_routes)
    
    return app
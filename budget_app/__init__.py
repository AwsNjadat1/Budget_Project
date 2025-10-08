# budget_app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from .auth import oauth

# Create the database extension instance, but don't attach it to an app yet
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    oauth.init_app(app)
    db.init_app(app)

    # Register the Microsoft Azure provider with Authlib
    oauth.register(
        name='azure',
        client_id=app.config.get("AZURE_CLIENT_ID"),
        client_secret=app.config.get("AZURE_CLIENT_SECRET"),
        server_metadata_url=f'https://login.microsoftonline.com/{app.config.get("AZURE_TENANT_ID")}/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Import and register Blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    # Create database tables if they don't exist
    # This is a crucial step that runs when the app starts
    with app.app_context():
        from . import models # Import models here to avoid circular imports
        db.create_all()

    return app
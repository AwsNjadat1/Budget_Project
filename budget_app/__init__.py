# budget_app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from .auth import oauth

# This is the middleware that should fix the URL problem, but we'll add a more forceful fix.
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()

def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # We keep the ProxyFix as it's good practice for other parts of Flask (like logging).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Initialize extensions with the app
    oauth.init_app(app)
    db.init_app(app)

    # Register the Microsoft Azure provider with Authlib
    oauth.register(
        name='azure',
        client_id=app.config.get("AZURE_CLIENT_ID"),
        client_secret=app.config.get("AZURE_CLIENT_SECRET"),
        server_metadata_url=f'https://login.microsoftonline.com/{app.config.get("AZURE_TENANT_ID")}/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
        
        # --- THIS IS THE NEW, FORCEFUL FIX ---
        # This parameter explicitly tells Authlib to build all redirect URLs using "https".
        # It overrides any incorrect automatic detection.
        redirect_scheme='https'
        # --- END OF NEW FIX ---
    )

    # Import and register Blueprints
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
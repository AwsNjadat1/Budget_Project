# budget_app/__init__.py

from flask import Flask
from config import Config
# Import the oauth object from our new auth file
from .auth import oauth

def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize the OAuth object with the app
    oauth.init_app(app)
    
    # Register the Microsoft Azure provider with Authlib
    oauth.register(
        name='azure',
        client_id=app.config.get("AZURE_CLIENT_ID"),
        client_secret=app.config.get("AZURE_CLIENT_SECRET"),
        server_metadata_url=f'https://login.microsoftonline.com/{app.config.get("AZURE_TENANT_ID")}/v2.0/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'}
    )

    # Register the main Blueprint
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # Register the auth Blueprint
    from .auth import auth_bp
    app.register_blueprint(auth_bp)

    return app
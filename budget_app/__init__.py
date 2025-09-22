from flask import Flask
from config import Config

def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    """
    # 1. Create the Flask app instance
    app = Flask(__name__)

    # 2. Load configuration from our config.py file
    app.config.from_object(config_class)

    # 3. Register the Blueprint from our routes.py file
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # You could add other extensions or initializations here in the future
    # For example: db.init_app(app)

    # 4. Return the configured app instance
    return app
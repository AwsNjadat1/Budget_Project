from flask import Flask, render_template
from config import Config

def create_app(config_class=Config):
    """
    Creates and configures an instance of the Flask application.
    """
    # 1. Create the Flask app instance
    app = Flask(__name__,
                static_url_path='',
                static_folder='static',
                template_folder='templates')

    # 2. Load configuration from our config.py file
    app.config.from_object(config_class)

    # NEW: Initialize our authentication module
    from .auth import setup_auth
    setup_auth(app)

    # 3. Register the Blueprint from our routes.py file
    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    # You could add other extensions or initializations here in the future
    # For example: db.init_app(app)

    # Add a context processor to make config available to all templates
    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    # 4. Return the configured app instance
    return app
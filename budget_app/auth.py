# budget_app/auth.py

from authlib.integrations.flask_client import OAuth
from flask import current_app, session, redirect, url_for
from functools import wraps

# Initialize OAuth
oauth = OAuth()

def setup_auth(app):
    """Initializes Authlib with the application instance."""
    oauth.init_app(app)
    oauth.register(
        "auth0",
        client_id=app.config["AUTH0_CLIENT_ID"],
        client_secret=app.config["AUTH0_CLIENT_SECRET"],
        client_kwargs={"scope": "openid profile email"},
        server_metadata_url=f'https://{app.config["AUTH0_DOMAIN"]}/.well-known/openid-configuration',
    )

def require_auth(f):
    """
    A decorator to protect routes, ensuring the user is logged in.
    We will use this to protect the main app page.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("main.login"))
        return f(*args, **kwargs)
    return decorated
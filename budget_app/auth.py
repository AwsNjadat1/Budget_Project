# budget_app/auth.py

from flask import Blueprint, redirect, url_for, session
from authlib.integrations.flask_client import OAuth

# Create a Blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

# This will be initialized in the main app factory
oauth = OAuth()

@auth_bp.route('/login')
def login():
    """Redirects the user to the Microsoft login page."""
    redirect_uri = url_for('auth.auth_callback', _external=True)
    return oauth.azure.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/callback')
def auth_callback():
    """Handles the callback from Microsoft after a successful login."""
    token = oauth.azure.authorize_access_token()
    # Store the user's information in the session
    # The 'userinfo' contains details like name, email, etc.
    session['user'] = token.get('userinfo')
    return redirect(url_for('main.index'))

@auth_bp.route('/logout')
def logout():
    """Logs the user out by clearing the session."""
    session.pop('user', None)
    # Also redirect to Microsoft's logout page for a full sign-out
    # The post_logout_redirect_uri should be a page that doesn't require login.
    # We'll create a simple logged-out page for this.
    logout_redirect = url_for('main.logged_out', _external=True)
    return redirect(f"{oauth.azure.server_metadata['end_session_endpoint']}?post_logout_redirect_uri={logout_redirect}")
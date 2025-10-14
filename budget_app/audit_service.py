# budget_app/audit_service.py
from . import db
from .models import AuditLog
from flask import session

def get_current_user():
    """Helper to get user info from the session."""
    user_info = session.get('user', {})
    return user_info.get('oid'), user_info.get('name')

def log_action(action, details=None):
    """
    Creates and saves an audit log entry.
    This should be called after a successful operation but before the final commit.
    """
    try:
        user_id, user_name = get_current_user()
        if not user_id:
            # Don't log if for some reason user isn't in session
            return

        log_entry = AuditLog(
            user_id=user_id,
            user_name=user_name,
            action=action,
            details=str(details) if details else None
        )
        db.session.add(log_entry)
    except Exception as e:
        # If logging fails, we don't want to crash the main application
        print(f"Error while creating audit log: {str(e)}")
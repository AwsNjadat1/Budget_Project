# budget_app/session_manager.py

import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import session # We will use the secure Flask session now

# Import constants and schemas from our new data_utils module
from .data_utils import IDCOL, INTERNAL_DF_COLS

# This dictionary holds all active user sessions in memory.
# The key will now be the USER ID from Auth0.
SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_or_create_session_data(user_id: str) -> Dict[str, Any]:
    """
    Gets or creates a data bucket for an authenticated user.
    The key is now the user's permanent ID from Auth0.
    """
    if user_id in SESSIONS:
        SESSIONS[user_id]["last_accessed"] = datetime.utcnow()
        return SESSIONS[user_id]

    # Create a new data bucket for this user
    SESSIONS[user_id] = {
        "user_id": user_id,
        "entries_df": pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS),
        "masters": {
            "clients": [
                "Client 1", "Client 2", "Client 3", 
            ],
            "products": pd.DataFrame({
                "Product": [
                    "Product 1", "Product 2", "Product 3",
                ],
                "Category": [
                    "Category 1", "Category 2", "Category 3", 
                ],
                "Default_PMT": [pd.NA, pd.NA, pd.NA],
                "Default_GM%": [pd.NA, pd.NA, pd.NA]
            }),
        },
        "last_accessed": datetime.utcnow()
    }
    return SESSIONS[user_id]

def get_session_data_for_request() -> Dict[str, Any]:
    """
    Helper to get the data bucket based on the logged-in user.
    This replaces the old 'get_session_from_request'.
    """
    if "user" not in session or "userinfo" not in session["user"] or "sub" not in session["user"]["userinfo"]:
        # This case should ideally not be hit if endpoints are protected,
        # but it's a good safeguard.
        raise PermissionError("User not authenticated")
    
    user_id = session["user"]["userinfo"]["sub"]
    return get_or_create_session_data(user_id)
import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request

# Import constants from our new data_utils module
from .data_utils import IDCOL, INTERNAL_DF_COLS

# =========================
# Session Management
# =========================
SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_or_create_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Gets or creates a new session for a user."""
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]

    new_session_id = str(uuid.uuid4())
    
    # Each user gets their own copy of data and masters
    SESSIONS[new_session_id] = {
        "id": new_session_id,
        "entries_df": pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS),
        "masters": {
            "clients": [
                "ACME Mining Corp", "Apex Steel Industries", "BlueWater Ports Ltd", 
                "Cedar Trading Co", "Delta Manufacturing", "Eagle Logistics"
            ],
            "products": pd.DataFrame({
                "Product": [
                    "Iron Ore 62%", "HBI Premium", "Coking Coal", "Rebar ASTM A615",
                    "Steel Billets", "Wire Rod", "Hot Rolled Coil", "Cold Rolled Sheet"
                ],
                "Category": [
                    "Iron Ore", "DRI/HBI", "Coal", "Long Steel",
                    "Semi-Finished", "Wire Products", "Flat Steel", "Flat Steel"
                ],
                
            }),
        },
        "last_accessed": datetime.utcnow()
    }
    return SESSIONS[new_session_id]

def get_session_from_request() -> Dict[str, Any]:
    """Helper to get the session ID from the request header."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        # If no session ID is provided, create a new one.
        # This is the entry point for a new user/page refresh.
        return get_or_create_session()
    
    session = SESSIONS.get(session_id)
    if not session:
        # If an invalid/expired session ID is provided, create a new one.
        return get_or_create_session()
    
    session["last_accessed"] = datetime.utcnow()
    return session
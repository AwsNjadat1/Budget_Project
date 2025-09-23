import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import request

# Import constants and schemas from our new data_utils module
from .data_utils import IDCOL, INTERNAL_DF_COLS

# This dictionary holds all active user sessions in memory.
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
                "Client 1", "Client 2", "Client 3", 
            ],
            "products": pd.DataFrame({
                "Product": [
                    "Product 1", "Product 2", "Product 3",
                ],
                "Category": [
                    "Category 1", "Category 2", "Category 3", 
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
        return get_or_create_session()
    
    session = SESSIONS.get(session_id)
    if not session:
        return get_or_create_session()
    
    session["last_accessed"] = datetime.utcnow()
    return session
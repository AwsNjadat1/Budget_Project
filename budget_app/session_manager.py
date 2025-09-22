# File: budget_project/budget_app/session_manager.py
# REVERTED VERSION

import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request

from .data_utils import IDCOL, INTERNAL_DF_COLS

SESSIONS: Dict[str, Dict[str, Any]] = {}

def get_or_create_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Gets or creates a new session for a user."""
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]

    new_session_id = str(uuid.uuid4())
    
    # Each user gets their own copy of the hardcoded data
    SESSIONS[new_session_id] = {
        "id": new_session_id,
        "entries_df": pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS),
        "masters": {
            "clients": [
                "ACME Mining Corp", "Apex Steel Industries", "BlueWater Ports Ltd", 
                "Cedar Trading Co", "Delta Manufacturing", "Eagle Logistics",
                "Global Petrochem", "Quantum Energy", "Fresh Produce Inc."
            ],
            "products": pd.DataFrame({
                "Product": [
                    "Iron Ore 62%", "HBI Premium", "Coking Coal", "Rebar ASTM A615",
                    "Crude Palm Oil", "Soybean Oil", "Caustic Soda", "Sulfuric Acid",
                    "Kraft Paper", "Corrugated Boxes", "Flour", "Sugar"
                ],
                "Category": [
                    "Iron Ore", "DRI/HBI", "Coal", "Long Steel",
                    "Vegetable Oils", "Vegetable Oils", "Chlor-Alkali", "Acids",
                    "Packaging", "Packaging", "Milling", "Commodities"
                ],
                "Default_PMT": [120.50, 350.00, 210.75, 650.00, 950.00, 1100.00, 450.00, 300.00, 880.00, 1200.00, 550.00, 720.00],
                "Default_GM%": [8.5, 12.0, 10.2, 15.5, 12.5, 11.0, 22.0, 18.5, 15.0, 20.0, 10.0, 9.5]
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
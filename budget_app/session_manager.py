import os
import uuid
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request

from .data_utils import IDCOL, INTERNAL_DF_COLS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENTS_CSV_PATH = os.path.join(BASE_DIR, 'master_data', 'clients.csv')
PRODUCTS_CSV_PATH = os.path.join(BASE_DIR, 'master_data', 'products.csv')

SESSIONS: Dict[str, Dict[str, Any]] = {}

def load_default_masters() -> Dict[str, Any]:
    """Loads the master clients and products from the CSV files."""
    try:
        clients_df = pd.read_csv(CLIENTS_CSV_PATH)
    except FileNotFoundError:
        print(f"WARNING: clients.csv not found at {CLIENTS_CSV_PATH}. Using empty DataFrame.")
        clients_df = pd.DataFrame(columns=['Client', 'Business Unit'])

    try:
        products_df = pd.read_csv(PRODUCTS_CSV_PATH)
    except FileNotFoundError:
        print(f"WARNING: products.csv not found at {PRODUCTS_CSV_PATH}. Using empty DataFrame.")
        products_df = pd.DataFrame(columns=['Product', 'Category', 'Default_PMT', 'Default_GM%', 'Business Unit'])
        
    return {"clients": clients_df, "products": products_df}


def get_or_create_session(session_id: Optional[str] = None) -> Dict[str, Any]:
    """Gets or creates a new session for a user."""
    if session_id and session_id in SESSIONS:
        return SESSIONS[session_id]

    new_session_id = str(uuid.uuid4())
    
    default_masters = load_default_masters()
    
    SESSIONS[new_session_id] = {
        "id": new_session_id,
        "entries_df": pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS),
        "masters": default_masters,
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
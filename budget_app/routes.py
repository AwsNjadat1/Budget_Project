# File: budget_project/budget_app/routes.py
# CORRECTED VERSION

import io
import json
from datetime import datetime
import uuid

import pandas as pd
from flask import Blueprint, request, jsonify, send_file, render_template

from .session_manager import get_session_from_request
from .data_utils import (
    to_json_records, from_json_records, month_name_to_num,
    coerce_narrow_schema_types, recalc_narrow_schema, ensure_row_id,
    coerce_wide_schema_types, recalc_wide_schema, convert_wide_to_narrow,
    export_df_for_save, IDCOL, INTERNAL_DF_COLS
)

main = Blueprint('main', __name__)

@main.route("/")
def index():
    """Serve the modern web interface from the template file."""
    return render_template("index.html")

# --- FIXED FUNCTION 1 ---
@main.route("/api/state")
def api_get_state():
    """Get current application state for a user session."""
    session = get_session_from_request()
    return jsonify({
        "session_id": session["id"],
        "entries": to_json_records(session["entries_df"]),
        "masters": {
            # THE FIX: Convert BOTH DataFrames to the correct JSON format
            "clients": json.loads(session["masters"]["clients"].to_json(orient="records")),
            "products": json.loads(session["masters"]["products"].to_json(orient="records")),
        }
    })

@main.route("/api/add", methods=["POST"])
def api_add_entry():
    """Add a new entry to the user's session."""
    session = get_session_from_request()
    entries_df = session["entries_df"]
    masters = session["masters"]
    
    try:
        data = request.get_json(force=True)
        # --- [Validation code remains the same] ---
        errors = []
        if not data.get("qty") or float(data.get("qty")) == 0:
            errors.append("Qty (MT) cannot be 0.")
        if not data.get("pmt") or float(data.get("pmt")) == 0:
            errors.append("PMT (JOD) cannot be 0.")
        if not data.get("gm_percent") or float(data.get("gm_percent")) == 0:
            errors.append("GM % cannot be 0.")
        if errors:
            return jsonify({"status": "error", "message": " ".join(errors)}), 400
        # --- [Entry creation code remains the same] ---
        entry = {
            IDCOL: str(uuid.uuid4()),
            "Business Unit": str(data.get("business_unit", "")),
            "Section": str(data.get("section", "")),
            "Client": str(data.get("client", "")),
            "Category": "",
            "Product": str(data.get("product", "")),
            "Month": month_name_to_num(data.get("month_name", "Jan")),
            "PMT (JOD)": float(data.get("pmt", 0)),
            "GM %": float(data.get("gm_percent", 0)),
            "Qty (MT)": float(data.get("qty", 0)),
            "Sales (JOD)": 0.0,
            "GP (JOD)": 0.0,
            "Sector": str(data.get("sector", "")),
            "Booked": str(data.get("booked", "No")),
        }
        
        new_row_df = pd.DataFrame([entry])
        new_row_df = coerce_narrow_schema_types(new_row_df)
        # Use the products DataFrame from the session for calculations
        products_df = pd.DataFrame(masters["products"])
        new_row_df = recalc_narrow_schema(new_row_df, products_df)

        session["entries_df"] = pd.concat([entries_df, new_row_df], ignore_index=True)
        
        return jsonify({
            "status": "success",
            "entries": to_json_records(session["entries_df"]),
            "message": "Entry added successfully"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to add entry: {str(e)}"}), 500

# --- FIXED FUNCTION 2 ---
@main.route("/api/load_masters", methods=["POST"])
def api_load_masters():
    """Load master data into the user's session from an uploaded file."""
    session = get_session_from_request()
    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        # Read both sheets from the uploaded file
        clients_df = pd.read_excel(file, sheet_name="Clients", engine="openpyxl")
        products_df = pd.read_excel(file, sheet_name="Products", engine="openpyxl")
        
        # THE FIX: Store the entire DataFrames in the session, not just a list of names.
        # This preserves the Business Unit information needed for filtering.
        session["masters"]["clients"] = clients_df
        session["masters"]["products"] = products_df
        
        return jsonify({
            "status": "success",
            "masters": {
                # THE FIX: Also convert both to JSON for the response to the frontend
                "clients": json.loads(clients_df.to_json(orient="records")),
                "products": json.loads(products_df.to_json(orient="records")),
            },
            "message": "Master data loaded successfully into your session"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load master data: {str(e)}"}), 400

# --- [Other routes like /api/commit, /api/recalc, etc., are unchanged] ---
@main.route("/api/commit", methods=["POST"])
def api_commit_changes():
    session = get_session_from_request()
    entries_df = session["entries_df"]
    masters = session["masters"]
    try:
        payload = request.get_json(force=True)
        delete_ids = set(payload.get("deleteIds", []))
        if delete_ids:
            session["entries_df"] = entries_df[~entries_df[IDCOL].isin(delete_ids)]
        return jsonify({
            "status": "success",
            "entries": to_json_records(session["entries_df"]),
            "message": "Changes committed successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": f"Failed to commit changes: {str(e)}"}), 400

@main.route("/api/recalc", methods=["POST"])
def api_recalculate():
    session = get_session_from_request()
    masters = session["masters"]
    try:
        products_df = pd.DataFrame(masters["products"])
        session["entries_df"] = recalc_narrow_schema(session["entries_df"], products_df)
        return jsonify({
            "status": "success",
            "entries": to_json_records(session["entries_df"]),
            "message": "Data recalculated successfully"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@main.route("/api/clear_data", methods=["POST"])
def api_clear_data():
    session = get_session_from_request()
    try:
        session["entries_df"] = pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)
        return jsonify({"status": "success", "message": "Session data cleared successfully.", "entries": []})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route("/api/load_budget", methods=["POST"])
def api_load_budget():
    session = get_session_from_request()
    masters = session["masters"]
    try:
        file = request.files.get("file")
        sheet = request.form.get("sheet", "Budget")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        df = pd.read_excel(file, sheet_name=sheet, engine="openpyxl")
        is_wide_schema = any(col in df.columns for col in ["Qty_Jan (MT)", "PMT_Q1 (JOD)"])
        products_df = pd.DataFrame(masters["products"])
        if is_wide_schema:
            df_processed = coerce_wide_schema_types(df.copy())
            df_processed = recalc_wide_schema(df_processed, products_df)
            df_final_narrow = convert_wide_to_narrow(df_processed)
        else:
            df_final_narrow = coerce_narrow_schema_types(df.copy())
            df_final_narrow = recalc_narrow_schema(df_final_narrow, products_df)
        session["entries_df"] = ensure_row_id(df_final_narrow)
        return jsonify({
            "status": "success",
            "entries": to_json_records(session["entries_df"]),
            "message": f"Budget loaded into your session from {sheet} sheet"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load budget: {str(e)}"}), 400

@main.route("/api/download_current")
def api_download_current():
    session = get_session_from_request()
    try:
        buffer = io.BytesIO()
        export_df = export_df_for_save(session["entries_df"])
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Budget")
        buffer.seek(0)
        return send_file(
            buffer, as_attachment=True,
            download_name=f"Budget_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to download: {str(e)}"}), 400
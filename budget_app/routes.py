# budget_app/routes.py

import io
import json
from datetime import datetime
import uuid

import pandas as pd
# IMPORTANT: Add session, url_for, and redirect
from flask import Blueprint, request, jsonify, send_file, render_template, session, url_for, redirect

# Import our new auth helpers and session manager
from .auth import oauth, require_auth
# RENAME the import to the new function name
from .session_manager import get_session_data_for_request

# Keep all the other data_utils imports
from .data_utils import (
    to_json_records, from_json_records, month_name_to_num,
    coerce_narrow_schema_types, recalc_narrow_schema, ensure_row_id,
    coerce_wide_schema_types, recalc_wide_schema, convert_wide_to_narrow,
    export_df_for_save, IDCOL, INTERNAL_DF_COLS
)

# Create a Blueprint. 'main' is the name we'll use to reference it.
main = Blueprint('main', __name__)

# =========================
# NEW: Authentication Routes
# =========================

@main.route("/login")
def login():
    """Redirect to Auth0 login page."""
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("main.callback", _external=True)
    )

@main.route("/callback")
def callback():
    """Handle callback from Auth0 after successful login."""
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    return redirect(url_for("main.index"))

@main.route("/logout")
def logout():
    """Log the user out from our app and Auth0."""
    session.clear()
    # This constructs the correct URL to log out from Auth0 and redirect back to our app
    domain = main.app.config['AUTH0_DOMAIN']
    client_id = main.app.config['AUTH0_CLIENT_ID']
    return_to = url_for('main.index', _external=True)
    
    logout_url = f"https://{domain}/v2/logout?client_id={client_id}&returnTo={return_to}"
    return redirect(logout_url)

# =========================
# Modern Web Interface
# =========================

@main.route("/")
@require_auth  # This decorator now protects the main application page
def index():
    """Serve the modern web interface. User must be logged in."""
    # We pass the user's information to the template
    user_info = session.get("user", {}).get("userinfo", {})
    return render_template("index.html", user=user_info)

# =========================
# Enhanced API Routes (Now Secured)
# =========================

@main.route("/api/state")
def api_get_state():
    """Get current application state for the authenticated user."""
    try:
        session_data = get_session_data_for_request()
        return jsonify({
            # The concept of a client-side session_id is gone.
            "user": session.get("user", {}).get("userinfo", {}),
            "entries": to_json_records(session_data["entries_df"]),
            "masters": {
                "clients": session_data["masters"]["clients"],
                "products": json.loads(session_data["masters"]["products"].to_json(orient="records")),
            }
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"error": f"Failed to get state: {str(e)}"}), 500

@main.route("/api/add", methods=["POST"])
def api_add_entry():
    """Add a new entry to the user's data."""
    try:
        session_data = get_session_data_for_request()
        entries_df = session_data["entries_df"]
        masters = session_data["masters"]
    
        data = request.get_json(force=True)

        # --- Server-Side Validation (no changes here) ---
        errors = []
        try:
            if float(data.get("qty")) == 0: errors.append("Qty (MT) cannot be 0.")
        except (ValueError, TypeError, AttributeError): errors.append("Invalid value for Qty (MT).")
        try:
            if float(data.get("pmt")) == 0: errors.append("PMT (JOD) cannot be 0.")
        except (ValueError, TypeError, AttributeError): errors.append("Invalid value for PMT (JOD).")
        try:
            if float(data.get("gm_percent")) == 0: errors.append("GP % cannot be 0.")
        except (ValueError, TypeError, AttributeError): errors.append("Invalid value for GP %.")

        if errors:
            return jsonify({"status": "error", "message": " ".join(errors)}), 400
        # --- End Validation ---

        entry = {
            IDCOL: str(uuid.uuid4()), "Business Unit": str(data.get("business_unit", "")),
            "Section": str(data.get("section", "")), "Client": str(data.get("client", "")),
            "Category": "", "Product": str(data.get("product", "")),
            "Month": month_name_to_num(data.get("month_name", "Jan")),
            "PMT (JOD)": float(data.get("pmt", 0)), "GP %": float(data.get("gm_percent", 0)),
            "Qty (MT)": float(data.get("qty", 0)), "Sales (JOD)": 0.0, "GP (JOD)": 0.0,
            "Sector": str(data.get("sector", "")), "Booked": str(data.get("booked", "No")),
        }
        
        new_row_df = pd.DataFrame([entry])
        new_row_df = coerce_narrow_schema_types(new_row_df)
        new_row_df = recalc_narrow_schema(new_row_df, masters["products"])

        if entries_df.empty:
            session_data["entries_df"] = new_row_df
        else:
            session_data["entries_df"] = pd.concat([entries_df, new_row_df], ignore_index=True)
        
        return jsonify({
            "status": "success",
            "entries": to_json_records(session_data["entries_df"]),
            "message": "Entry added successfully"
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to add entry: {str(e)}"}), 500

@main.route("/api/commit", methods=["POST"])
def api_commit_changes():
    """Commit changes for the user's data."""
    try:
        session_data = get_session_data_for_request()
        entries_df = session_data["entries_df"]
        masters = session_data["masters"]

        payload = request.get_json(force=True)
        edited_rows = payload.get("editedRows", [])
        delete_ids = set(payload.get("deleteIds", []))
        
        if delete_ids:
            entries_df = entries_df[~entries_df[IDCOL].isin(delete_ids)]
        
        if edited_rows:
            edited_df = from_json_records(edited_rows, masters)
            edited_df = recalc_narrow_schema(edited_df, masters["products"])

            if not entries_df.empty:
                base = entries_df.set_index(IDCOL)
                updates = edited_df.set_index(IDCOL)
                base.update(updates)
                new_ids = [idx for idx in updates.index if idx not in base.index]
                if new_ids:
                    base = pd.concat([base, updates.loc[new_ids]], axis=0)
                entries_df = base.reset_index()
            else:
                entries_df = edited_df
        
        session_data["entries_df"] = entries_df
        
        return jsonify({
            "status": "success",
            "entries": to_json_records(session_data["entries_df"]),
            "message": "Changes committed successfully"
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"status": "error", "error": f"Failed to commit changes: {str(e)}"}), 400

@main.route("/api/recalc", methods=["POST"])
def api_recalculate():
    """Recalculate all entries in the user's data."""
    try:
        session_data = get_session_data_for_request()
        masters = session_data["masters"]
        
        session_data["entries_df"] = recalc_narrow_schema(session_data["entries_df"], masters["products"])
        return jsonify({
            "status": "success",
            "entries": to_json_records(session_data["entries_df"]),
            "message": "Data recalculated successfully"
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 400

@main.route("/api/clear_data", methods=["POST"])
def api_clear_data():
    """Clear all entries from the user's data."""
    try:
        session_data = get_session_data_for_request()
        session_data["entries_df"] = pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)
        return jsonify({
            "status": "success",
            "message": "Session data cleared successfully.",
            "entries": []
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route("/api/load_masters", methods=["POST"])
def api_load_masters():
    """Load master data into the user's data."""
    try:
        session_data = get_session_data_for_request()
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        excel_file = pd.ExcelFile(file)
        
        if "Clients" in excel_file.sheet_names:
            clients_df = pd.read_excel(excel_file, sheet_name="Clients", engine="openpyxl")
            if "Client" in clients_df.columns:
                session_data["masters"]["clients"] = sorted([str(c) for c in clients_df["Client"].dropna().unique()])
        
        if "Products" in excel_file.sheet_names:
            products_df = pd.read_excel(excel_file, sheet_name="Products", engine="openpyxl")
            required_cols = ["Product", "Category", "Default_PMT", "Default_GM%"]
            for col in required_cols:
                if col not in products_df.columns:
                    products_df[col] = "" if col in ["Product", "Category"] else pd.NA
            session_data["masters"]["products"] = products_df[required_cols]
        
        return jsonify({
            "status": "success",
            "masters": {
                "clients": session_data["masters"]["clients"],
                "products": json.loads(session_data["masters"]["products"].to_json(orient="records")),
            },
            "message": "Master data loaded successfully into your session"
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"error": f"Failed to load master data: {str(e)}"}), 400

@main.route("/api/load_budget", methods=["POST"])
def api_load_budget():
    """Load budget data into the user's data from an uploaded file."""
    try:
        session_data = get_session_data_for_request()
        masters = session_data["masters"]

        file = request.files.get("file")
        sheet = request.form.get("sheet", "Budget")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        df = pd.read_excel(file, sheet_name=sheet, engine="openpyxl")
        is_wide_schema = any(col in df.columns for col in ["Qty_Jan (MT)", "PMT_Q1 (JOD)"])
        
        if is_wide_schema:
            df_processed = coerce_wide_schema_types(df.copy())
            df_processed = recalc_wide_schema(df_processed, masters["products"])
            df_final_narrow = convert_wide_to_narrow(df_processed)
        else:
            df_final_narrow = coerce_narrow_schema_types(df.copy())
            df_final_narrow = recalc_narrow_schema(df_final_narrow, masters["products"])
        
        session_data["entries_df"] = ensure_row_id(df_final_narrow)
        
        return jsonify({
            "status": "success",
            "entries": to_json_records(session_data["entries_df"]),
            "message": f"Budget loaded into your session from {sheet} sheet"
        })
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"error": f"Failed to load budget: {str(e)}"}), 400

@main.route("/api/download_current")
def api_download_current():
    """Download current user's budget data as an Excel file."""
    try:
        session_data = get_session_data_for_request()
        entries_df = session_data["entries_df"]
        buffer = io.BytesIO()
        export_df = export_df_for_save(entries_df)
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Budget")
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"Budget_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except PermissionError:
        return jsonify({"error": "Unauthorized"}), 401
    except Exception as e:
        return jsonify({"error": f"Failed to download: {str(e)}"}), 400


# DEPRECATED: Server-side save is no longer a good model with per-user data
@main.route("/api/save", methods=["POST"])
def api_save():
    return jsonify({"error": "Server-side save is disabled in multi-user mode."}), 403

@main.route("/api/save_as", methods=["POST"])
def api_save_as():
    return jsonify({"error": "Server-side save is disabled in multi-user mode."}), 403
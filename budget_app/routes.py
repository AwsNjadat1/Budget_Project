# budget_app/routes.py

import io
import json
from datetime import datetime
import uuid

import pandas as pd
from flask import (
    Blueprint, request, jsonify, send_file, render_template,
    session, redirect, url_for
)

# --- NEW IMPORTS ---
# Import the database object and the BudgetEntry model
from . import db
from .models import BudgetEntry
# --- END NEW IMPORTS ---

# Import our separated modules
from .data_utils import (
    month_name_to_num,
    coerce_narrow_schema_types, recalc_narrow_schema, ensure_row_id,
    coerce_wide_schema_types, recalc_wide_schema, convert_wide_to_narrow,
    export_df_for_save, IDCOL
)

# Create a Blueprint. 'main' is the name we'll use to reference it.
main = Blueprint('main', __name__)


# --- NEW HELPER FUNCTION ---
def get_user_id():
    """
    Gets the unique, stable Object ID (oid) for the logged-in user.
    This is the key to separating data between different users.
    """
    return session.get('user', {}).get('oid')
# --- END NEW HELPER FUNCTION ---


# =========================
# User-Facing Routes
# =========================

@main.route("/")
def index():
    """Serve the modern web interface. This route is protected."""
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template("index.html", user=session.get('user'))

@main.route("/logged_out")
def logged_out():
    """A simple page to show after the user has logged out."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Logged Out</title>
        <style>
            body { font-family: sans-serif; text-align: center; padding-top: 50px; }
            a { color: #007bff; }
        </style>
    </head>
    <body>
        <h2>You have been successfully logged out.</h2>
        <p><a href="/">Log in again</a></p>
    </body>
    </html>
    """

# =========================
# API Routes (Now Database-Driven)
# =========================

@main.route("/api/state")
def api_get_state():
    """Get all data for the current logged-in user from the database."""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    # Query the database for the current user's entries
    user_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
    # Convert the list of database objects to a list of dictionaries
    entries_list = [entry.to_dict() for entry in user_entries]

    # For now, master data is still managed in the session, not the database.
    # This is a potential future improvement.
    user_session = session.get(f"user_data_{user_id}", {
        "masters": {
            "clients": ["Client 1", "Client 2"],
            "products": pd.DataFrame({"Product": ["Prod A"], "Category": ["Cat X"]})
        }
    })
    
    return jsonify({
        "entries": entries_list,
        "masters": {
            "clients": user_session["masters"]["clients"],
            "products": json.loads(user_session["masters"]["products"].to_json(orient="records")),
        }
    })

@main.route("/api/add", methods=["POST"])
def api_add_entry():
    """Add a new entry to the database for the current user."""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
        
    try:
        data = request.get_json(force=True)

        # --- Your existing validation logic can go here ---
        # For example, check if qty, pmt, etc., are valid.

        # Calculate sales and GP from the raw inputs
        qty = float(data.get("qty", 0))
        pmt = float(data.get("pmt", 0))
        gp_percent = float(data.get("gm_percent", 0))
        sales = round(qty * pmt, 2)
        gp = round(sales * (gp_percent / 100.0), 2)

        # Create a new BudgetEntry object (a new row for the table)
        new_entry = BudgetEntry(
            _rid=str(uuid.uuid4()),
            user_id=user_id,
            business_unit=str(data.get("business_unit", "")),
            section=str(data.get("section", "")),
            client=str(data.get("client", "")),
            category=str(data.get("category", "")),
            product=str(data.get("product", "")),
            month=month_name_to_num(data.get("month_name", "Jan")),
            pmt_jod=pmt,
            gp_percent=gp_percent,
            qty_mt=qty,
            sales_jod=sales,
            gp_jod=gp,
            sector=str(data.get("sector", "")),
            booked=str(data.get("booked", "No")),
        )
        
        db.session.add(new_entry)  # Add the new row to the transaction
        db.session.commit()        # Commit the transaction to the database
        
        # Query all entries for the user to return the updated list to the frontend
        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({
            "status": "success",
            "entries": [entry.to_dict() for entry in all_entries],
            "message": "Entry added successfully"
        })
        
    except Exception as e:
        db.session.rollback()  # If an error occurs, undo the transaction
        return jsonify({"status": "error", "message": f"Failed to add entry: {str(e)}"}), 500

@main.route("/api/commit", methods=["POST"])
def api_commit_changes():
    """Handles deleting rows from the database for the current user."""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    
    try:
        payload = request.get_json(force=True)
        delete_ids = set(payload.get("deleteIds", []))
        
        if delete_ids:
            # Perform a bulk delete on rows that match the user_id and are in the delete_ids list
            BudgetEntry.query.filter(
                BudgetEntry.user_id == user_id,
                BudgetEntry._rid.in_(delete_ids)
            ).delete(synchronize_session=False)
        
        # Note: Frontend does not support editing yet, so editing logic is omitted.
            
        db.session.commit()

        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({
            "status": "success",
            "entries": [entry.to_dict() for entry in all_entries],
            "message": "Changes committed successfully"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": f"Failed to commit changes: {str(e)}"}), 400

@main.route("/api/clear_data", methods=["POST"])
def api_clear_data():
    """Deletes all budget entries for the current user from the database."""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    try:
        BudgetEntry.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "All your data has been cleared successfully.",
            "entries": []
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route("/api/load_budget", methods=["POST"])
def api_load_budget():
    """Loads budget data from an Excel file, replacing the user's current data in the database."""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    try:
        file = request.files.get("file")
        sheet = request.form.get("sheet", "Budget")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        # --- This part of the logic remains the same: process the Excel file ---
        df = pd.read_excel(file, sheet_name=sheet, engine="openpyxl")
        is_wide_schema = any(col in df.columns for col in ["Qty_Jan (MT)", "PMT_Q1 (JOD)"])
        
        # For this example, we'll assume masters are in the session
        user_session = session.get(f"user_data_{user_id}", {"masters": {"products": pd.DataFrame()}})
        masters = user_session["masters"]
        
        if is_wide_schema:
            df_processed = coerce_wide_schema_types(df.copy())
            df_processed = recalc_wide_schema(df_processed, masters["products"])
            df_final_narrow = convert_wide_to_narrow(df_processed)
        else:
            df_final_narrow = coerce_narrow_schema_types(df.copy())
            df_final_narrow = recalc_narrow_schema(df_final_narrow, masters["products"])
        
        df_final_narrow = ensure_row_id(df_final_narrow)
        # --- End of Excel processing ---

        # First, clear all existing data for this user to prevent duplicates
        BudgetEntry.query.filter_by(user_id=user_id).delete()

        # Iterate through the DataFrame and create new database objects
        new_entries = []
        for _, row in df_final_narrow.iterrows():
            entry = BudgetEntry(
                _rid=row.get(IDCOL),
                user_id=user_id,
                business_unit=row.get("Business Unit"),
                section=row.get("Section"),
                client=row.get("Client"),
                category=row.get("Category"),
                product=row.get("Product"),
                month=row.get("Month"),
                qty_mt=row.get("Qty (MT)"),
                pmt_jod=row.get("PMT (JOD)"),
                gp_percent=row.get("GP %"),
                sales_jod=row.get("Sales (JOD)"),
                gp_jod=row.get("GP (JOD)"),
                sector=row.get("Sector"),
                booked=row.get("Booked")
            )
            new_entries.append(entry)
        
        db.session.bulk_save_objects(new_entries) # Efficiently add all new entries
        db.session.commit()

        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({
            "status": "success",
            "entries": [entry.to_dict() for entry in all_entries],
            "message": f"Budget loaded successfully from sheet '{sheet}'."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to load budget: {str(e)}"}), 400

@main.route("/api/download_current")
def api_download_current():
    """Downloads the user's current budget data from the database as an Excel file."""
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
        
    try:
        # Get data from the database
        user_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        entries_list = [entry.to_dict() for entry in user_entries]
        
        if not entries_list:
            return jsonify({"error": "No data to download."}), 404

        # Convert to a DataFrame for easy export
        entries_df = pd.DataFrame(entries_list)
        
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
    except Exception as e:
        return jsonify({"error": f"Failed to download: {str(e)}"}), 400

# Other routes like /api/load_masters can remain as they are for now,
# as they modify session data which is still used for dropdowns.
@main.route("/api/load_masters", methods=["POST"])
def api_load_masters():
    # This function is now less critical but can still be used to update
    # the client/product dropdowns for the current session.
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "Not authenticated"}), 401
    
    # Store master data in a user-specific session key
    user_session_key = f"user_data_{user_id}"
    user_session = session.get(user_session_key, {"masters": {}})

    try:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400
        
        excel_file = pd.ExcelFile(file)
        
        if "Clients" in excel_file.sheet_names:
            clients_df = pd.read_excel(excel_file, sheet_name="Clients", engine="openpyxl")
            if "Client" in clients_df.columns:
                user_session["masters"]["clients"] = sorted([str(c) for c in clients_df["Client"].dropna().unique()])
        
        if "Products" in excel_file.sheet_names:
            products_df = pd.read_excel(excel_file, sheet_name="Products", engine="openpyxl")
            required_cols = ["Product", "Category"]
            for col in required_cols:
                if col not in products_df.columns:
                    products_df[col] = ""
            user_session["masters"]["products"] = products_df[required_cols]
        
        session[user_session_key] = user_session

        return jsonify({
            "status": "success",
            "masters": {
                "clients": user_session["masters"]["clients"],
                "products": json.loads(user_session["masters"]["products"].to_json(orient="records")),
            },
            "message": "Master data loaded successfully into your session"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load master data: {str(e)}"}), 400

@main.route("/api/save", methods=["POST"])
def api_save():
    return jsonify({"error": "Server-side save is disabled. Data is saved automatically."}), 403

@main.route("/api/save_as", methods=["POST"])
def api_save_as():
    return jsonify({"error": "Server-side save is disabled. Use the Download button."}), 403
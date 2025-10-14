# budget_app/routes.py

import io
import json
from datetime import datetime
import uuid
from .audit_service import log_action

import pandas as pd
from flask import (
    Blueprint, request, jsonify, send_file, render_template,
    session, redirect, url_for
)

from config import Config

from . import db
from .models import BudgetEntry, Client, Product
from .data_utils import (
    month_name_to_num,
    coerce_wide_schema_types, recalc_wide_schema, convert_wide_to_narrow,
    coerce_narrow_schema_types, recalc_narrow_schema, ensure_row_id,
    export_df_for_save, IDCOL
)

main = Blueprint('main', __name__)

def get_user_id():
    return session.get('user', {}).get('oid')

def get_user_name():
    return session.get('user', {}).get('name')

@main.route("/")
def index():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template(
        "index.html", 
        user=session.get('user'),
        # Pass the exchange rates to the template
        exchange_rates=Config.EXCHANGE_RATES
    )

@main.route("/logged_out")
def logged_out():
    return """
    <!DOCTYPE html>
    <html><head><title>Logged Out</title><style>body { font-family: sans-serif; text-align: center; padding-top: 50px; } a { color: #007bff; }</style></head>
    <body><h2>You have been successfully logged out.</h2><p><a href="/">Log in again</a></p></body></html>
    """

@main.route("/api/state")
def api_get_state():
    user_id = get_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401
    try:
        user_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        entries_list = [entry.to_dict() for entry in user_entries]
        user_clients = Client.query.filter_by(user_id=user_id).all()
        client_list = sorted([c.name for c in user_clients])
        user_products = Product.query.filter_by(user_id=user_id).all()
        product_list = [{"Product": p.name, "Category": p.category} for p in user_products]
        return jsonify({ "entries": entries_list, "masters": { "clients": client_list, "products": product_list } })
    except Exception as e:
        return jsonify({"error": f"Failed to load state: {str(e)}"}), 500

@main.route("/api/add_master", methods=["POST"])
def api_add_master():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        data = request.get_json(force=True)
        message = ""
        if "new_client" in data:
            client_name = data["new_client"].strip()
            if client_name:
                if not Client.query.filter_by(user_id=user_id, name=client_name).first():
                    db.session.add(Client(user_id=user_id, name=client_name))
                    message = f"Client '{client_name}' added."
                else: message = f"Client '{client_name}' already exists."
        if "new_product" in data:
            product_data = data["new_product"]
            product_name = product_data.get("name", "").strip()
            product_category = product_data.get("category", "Uncategorized").strip()
            if product_name:
                if not Product.query.filter_by(user_id=user_id, name=product_name).first():
                    db.session.add(Product(user_id=user_id, name=product_name, category=product_category))
                    message = f"Product '{product_name}' added."
                else: message = f"Product '{product_name}' already exists."
        db.session.commit()
        all_clients = sorted([c.name for c in Client.query.filter_by(user_id=user_id).all()])
        all_products = [{"Product": p.name, "Category": p.category} for p in Product.query.filter_by(user_id=user_id).all()]
        return jsonify({"status": "success", "message": message, "masters": {"clients": all_clients, "products": all_products}})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to add master data: {str(e)}"}), 500

@main.route("/api/add", methods=["POST"])
def api_add_entry():
    """Add a new entry, with restored and corrected validation logic."""
    user_id, user_name = get_user_id(), get_user_name()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
        
    try:
        data = request.get_json(force=True)
        
        # --- RESTORED AND CORRECTED VALIDATION LOGIC ---
        try:
            qty = float(data.get("qty"))
        except (ValueError, TypeError):
             return jsonify({"status": "error", "message": "Quantity (MT) must be a valid number and cannot be empty."}), 400

        # Block zero-quantity entries immediately
        if qty == 0:
            return jsonify({"status": "error", "message": "Quantity (MT) cannot be 0."}), 400

        section = str(data.get("section", ""))
        is_broker_or_mining = section in ["Broker", "Mining"]
        sales, gp, pmt, gp_percent, profit_per_ton = 0.0, 0.0, 0.0, 0.0, 0.0

        if is_broker_or_mining:
            try:
                profit_per_ton = float(data.get("profit_per_ton"))
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "Profit per Ton must be a valid number and cannot be empty."}), 400
            
            # This validation now only runs if qty > 0, which is always true here.
            if profit_per_ton == 0:
                return jsonify({"status": "error", "message": "Profit per Ton cannot be 0 for Broker/Mining."}), 400
            gp = round(qty * profit_per_ton, 2)
        else:
            try:
                pmt = float(data.get("pmt"))
                gp_percent = float(data.get("gm_percent"))
            except (ValueError, TypeError):
                return jsonify({"status": "error", "message": "PMT and GP % must be valid numbers and cannot be empty."}), 400

            # This validation now only runs if qty > 0, which is always true here.
            if pmt == 0:
                return jsonify({"status": "error", "message": "PMT (USD) cannot be 0 for this section."}), 400
            if gp_percent == 0:
                 return jsonify({"status": "error", "message": "GP % cannot be 0 for this section."}), 400
            
            sales = round(qty * pmt, 2)
            gp = round(sales * (gp_percent / 100.0), 2)
            if qty > 0: profit_per_ton = round(gp / qty, 2)
        # --- END OF RESTORED LOGIC ---

        new_entry = BudgetEntry(
            _rid=str(uuid.uuid4()), user_id=user_id, user_name=user_name, profit_per_ton=profit_per_ton,
            business_unit=str(data.get("business_unit", "")), section=section, client=str(data.get("client", "")),
            category=str(data.get("category", "")), product=str(data.get("product", "")), month=month_name_to_num(data.get("month_name", "Jan")),
            pmt_usd=pmt, gp_percent=gp_percent, qty_mt=qty, sales_usd=sales, gp_usd=gp,
            sector=str(data.get("sector", "")), booked=str(data.get("booked", "No")),
        )
        db.session.add(new_entry)
        log_action("CREATE_BUDGET_ENTRY", details=f"Created entry with ID: {new_entry._rid}")
        db.session.commit()
        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({"status": "success", "entries": [e.to_dict() for e in all_entries], "message": "Entry added successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to add entry: {str(e)}"}), 500

@main.route("/api/update_entry", methods=["POST"])
def api_update_entry():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        data = request.get_json(force=True)
        entry_id, field, value = data.get("entry_id"), data.get("field"), float(data.get("value"))
        entry = BudgetEntry.query.filter_by(_rid=entry_id, user_id=user_id).first()
        if not entry: return jsonify({"error": "Entry not found or you do not have permission to edit it."}), 404
        if field == "Qty (MT)": entry.qty_mt = value
        elif field == "PMT (USD)": entry.pmt_usd = value
        elif field == "GP %": entry.gp_percent = value
        elif field == "Profit per Ton": entry.profit_per_ton = value
        else: return jsonify({"error": f"Invalid field '{field}' for editing."}), 400
        is_broker_or_mining = entry.section in ["Broker", "Mining"]
        if is_broker_or_mining:
            entry.gp_usd, entry.sales_usd = round(entry.qty_mt * entry.profit_per_ton, 2), 0
        else:
            entry.sales_usd = round(entry.qty_mt * entry.pmt_usd, 2)
            entry.gp_usd = round(entry.sales_usd * (entry.gp_percent / 100.0), 2)
            entry.profit_per_ton = round(entry.gp_usd / entry.qty_mt, 2) if entry.qty_mt > 0 else 0
        db.session.commit()
        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({"status": "success", "entries": [e.to_dict() for e in all_entries]})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to update entry: {str(e)}"}), 500

@main.route("/api/commit", methods=["POST"])
def api_commit_changes():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        payload = request.get_json(force=True)
        delete_ids = set(payload.get("deleteIds", []))
        if delete_ids:
            BudgetEntry.query.filter(BudgetEntry.user_id == user_id, BudgetEntry._rid.in_(delete_ids)).delete(synchronize_session=False)
            for entry_id in delete_ids:
                log_action("DELETE_ENTRY", details=f"Deleted entry with ID: {entry_id}")
        db.session.commit()
        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({"status": "success", "entries": [e.to_dict() for e in all_entries], "message": "Changes committed successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": f"Failed to commit changes: {str(e)}"}), 400

@main.route("/api/recalc", methods=["POST"])
def api_recalculate():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        user_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        if not user_entries: return jsonify({"status": "success", "entries": [], "message": "No data to recalculate."})
        user_products = Product.query.filter_by(user_id=user_id).all()
        products_df = pd.DataFrame([{"Product": p.name, "Category": p.category} for p in user_products])
        entries_df = pd.DataFrame([entry.to_dict() for entry in user_entries])
        recalculated_df = recalc_narrow_schema(entries_df, products_df)
        entry_map = {entry._rid: entry for entry in user_entries}
        for _, row in recalculated_df.iterrows():
            entry_to_update = entry_map.get(row[IDCOL])
            if entry_to_update:
                entry_to_update.sales_usd, entry_to_update.gp_usd, entry_to_update.category = row["Sales (usd)"], row["GP (usd)"], row["Category"]
        db.session.commit()
        final_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({"status": "success", "entries": [e.to_dict() for e in final_entries], "message": "Data recalculated successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": f"Failed to recalculate: {str(e)}"}), 500

@main.route("/api/clear_data", methods=["POST"])
def api_clear_data():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        BudgetEntry.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        return jsonify({"status": "success", "message": "All your data has been cleared successfully.", "entries": []})
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@main.route("/api/load_budget", methods=["POST"])
def api_load_budget():
    user_id, user_name = get_user_id(), get_user_name()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        file, sheet = request.files.get("file"), request.form.get("sheet", "Budget")
        if not file: return jsonify({"error": "No file provided"}), 400
        df = pd.read_excel(file, sheet_name=sheet, engine="openpyxl")
        user_products_from_db = Product.query.filter_by(user_id=user_id).all()
        products_df = pd.DataFrame([{"Product": p.name, "Category": p.category} for p in user_products_from_db])
        is_wide_schema = any(col in df.columns for col in ["Qty_Jan (MT)", "PMT_Q1 (usd)"])
        if is_wide_schema:
            df_processed = coerce_wide_schema_types(df.copy())
            df_processed = recalc_wide_schema(df_processed, products_df)
            df_final_narrow = convert_wide_to_narrow(df_processed)
        else:
            df_final_narrow = coerce_narrow_schema_types(df.copy())
            df_final_narrow = recalc_narrow_schema(df_final_narrow, products_df)
        df_final_narrow = ensure_row_id(df_final_narrow)
        BudgetEntry.query.filter_by(user_id=user_id).delete()
        new_entries = [BudgetEntry(
            _rid=row.get(IDCOL), user_id=user_id, user_name=user_name,
            business_unit=row.get("Business Unit"), section=row.get("Section"), client=row.get("Client"),
            category=row.get("Category"), product=row.get("Product"), month=row.get("Month"),
            qty_mt=row.get("Qty (MT)"), pmt_usd=row.get("PMT (usd)"), gp_percent=row.get("GP %"),
            sales_usd=row.get("Sales (usd)"), gp_usd=row.get("GP (usd)"), sector=row.get("Sector"),
            booked=row.get("Booked")
        ) for _, row in df_final_narrow.iterrows()]
        db.session.bulk_save_objects(new_entries)
        db.session.commit()
        all_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        return jsonify({"status": "success", "entries": [e.to_dict() for e in all_entries], "message": f"Budget loaded from '{sheet}'."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to load budget: {str(e)}"}), 400

@main.route("/api/download_current")
def api_download_current():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "User not authenticated"}), 401
    try:
        user_entries = BudgetEntry.query.filter_by(user_id=user_id).all()
        if not user_entries: return "No data to download.", 404
        entries_df = pd.DataFrame([entry.to_dict() for entry in user_entries])
        buffer = io.BytesIO()
        export_df = export_df_for_save(entries_df)
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df.to_excel(writer, index=False, sheet_name="Budget")
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name=f"Budget_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        return jsonify({"error": f"Failed to download: {str(e)}"}), 400

@main.route("/api/load_masters", methods=["POST"])
def api_load_masters():
    user_id = get_user_id()
    if not user_id: return jsonify({"error": "Not authenticated"}), 401
    try:
        file = request.files.get("file")
        if not file: return jsonify({"error": "No file provided"}), 400
        excel_file = pd.ExcelFile(file)
        Client.query.filter_by(user_id=user_id).delete()
        Product.query.filter_by(user_id=user_id).delete()
        if "Clients" in excel_file.sheet_names:
            clients_df = pd.read_excel(excel_file, sheet_name="Clients", engine="openpyxl")
            if "Client" in clients_df.columns:
                new_clients = [Client(user_id=user_id, name=str(c)) for c in clients_df["Client"].dropna().unique()]
                db.session.bulk_save_objects(new_clients)
        if "Products" in excel_file.sheet_names:
            products_df = pd.read_excel(excel_file, sheet_name="Products", engine="openpyxl")
            if "Product" in products_df.columns and "Category" in products_df.columns:
                products_df.dropna(subset=["Product"], inplace=True)
                products_df["Category"].fillna("Uncategorized", inplace=True)
                new_products = [Product(user_id=user_id, name=row["Product"], category=row["Category"]) for _, row in products_df.iterrows()]
                db.session.bulk_save_objects(new_products)
        db.session.commit()
        final_clients = sorted([c.name for c in Client.query.filter_by(user_id=user_id).all()])
        final_products = [{"Product": p.name, "Category": p.category} for p in Product.query.filter_by(user_id=user_id).all()]
        return jsonify({"status": "success", "masters": { "clients": final_clients, "products": final_products }, "message": "Master data loaded into database."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to load master data: {str(e)}"}), 400

@main.route("/api/save", methods=["POST"])
def api_save():
    return jsonify({"error": "Data is saved automatically."}), 403

@main.route("/api/save_as", methods=["POST"])
def api_save_as():
    return jsonify({"error": "Use the Download button."}), 403
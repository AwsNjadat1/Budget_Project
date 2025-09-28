import uuid
import json # We will need this for to_json_records
from typing import Dict, List, Any # And these too
import pandas as pd

# Constants
IDCOL = "_rid"

# --- Internal narrow schema for ENTRIES_DF ---
INTERNAL_DF_COLS = [
    "Business Unit", "Section", "Client", "Category", "Product", "Month",
    "Qty (MT)", "PMT (JOD)", "GP %", "Sales (JOD)", "GP (JOD)", "Sector", "Booked"
]
INTERNAL_NUMERIC_COLS = [
    "Qty (MT)", "PMT (JOD)", "GP %", "Sales (JOD)", "GP (JOD)"
]

# --- Original wide schema for external Excel files ---
WIDE_EXCEL_COLS = [
    "Business Unit", "Section", "Client", "Category", "Product",
    "PMT_Q1 (JOD)", "PMT_Q2 (JOD)", "PMT_Q3 (JOD)", "PMT_Q4 (JOD)",
    "GP %",
    "Qty_Jan (MT)", "Qty_Feb (MT)", "Qty_Mar (MT)", "Qty_Apr (MT)", "Qty_May (MT)", "Qty_Jun (MT)",
    "Qty_Jul (MT)", "Qty_Aug (MT)", "Qty_Sep (MT)", "Qty_Oct (MT)", "Qty_Nov (MT)", "Qty_Dec (MT)",
    "Sales_Q1 (JOD)", "Sales_Q2 (JOD)", "Sales_Q3 (JOD)", "Sales_Q4 (JOD)", "Total_Sales (JOD)",
    "GP_Q1 (JOD)", "GP_Q2 (JOD)", "GP_Q3 (JOD)", "GP_Q4 (JOD)", "Total_GP (JOD)",
    "Sector", "Booked"
]
WIDE_EXCEL_NUMERIC_COLS = [
    "PMT_Q1 (JOD)", "PMT_Q2 (JOD)", "PMT_Q3 (JOD)", "PMT_Q4 (JOD)", "GP %",
    "Qty_Jan (MT)", "Qty_Feb (MT)", "Qty_Mar (MT)", "Qty_Apr (MT)", "Qty_May (MT)", "Qty_Jun (MT)",
    "Qty_Jul (MT)", "Qty_Aug (MT)", "Qty_Sep (MT)", "Qty_Oct (MT)", "Qty_Nov (MT)", "Qty_Dec (MT)",
    "Sales_Q1 (JOD)", "Sales_Q2 (JOD)", "Sales_Q3 (JOD)", "Sales_Q4 (JOD)", "Total_Sales (JOD)",
    "GP_Q1 (JOD)", "GP_Q2 (JOD)", "GP_Q3 (JOD)", "GP_4 (JOD)", "Total_GP (JOD)"
]

# --- Columns for saving/exporting Excel files ---
SAVE_EXCEL_COLS = [
    "Business Unit", "Section", "Client", "Category", "Product", "Month",
    "Qty (MT)", "PMT (JOD)", "GP %", "Sales (JOD)", "GP (JOD)", "Sector", "Booked"
]


# =========================
# Enhanced Helper Functions
# =========================

def month_name_to_num(name: str) -> int:
    """Convert month name to number with error handling"""
    months_map = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    if isinstance(name, str):
        return months_map.get(name.capitalize()[:3], 1) # Handle 'January' -> 'Jan'
    try:
        num = int(name)
        return num if 1 <= num <= 12 else 1
    except (ValueError, TypeError):
        return 1

def month_num_to_name(num: int) -> str:
    """Convert month number to name"""
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return months[num - 1] if 1 <= num <= 12 else "Unknown"

def clean_numeric_string(s: Any) -> Any:
    """
    Cleans a string to prepare it for numeric conversion.
    Handles commas, currency symbols, percentage signs, and negative numbers in parentheses.
    """
    if isinstance(s, (int, float)):
        return s
    if isinstance(s, str):
        s = s.strip()
        s = s.replace(",", "") # Remove thousands separator
        s = s.replace("JOD", "").replace("%", "").strip() # Remove currency/percentage
        if s.startswith("(") and s.endswith(")"): # Handle negative numbers in parentheses
            try:
                return -float(s[1:-1])
            except ValueError:
                pass # Fall through to float conversion
    return s

def coerce_narrow_schema_types(df: pd.DataFrame) -> pd.DataFrame:
    """Type coercion for the internal narrow schema DataFrame."""
    if df.empty:
        return pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)
    
    # Ensure all required columns exist, fill with default values
    for col in INTERNAL_DF_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    
    # Apply cleaning before conversion for numeric columns
    for col in INTERNAL_NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_string)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    # Handle 'Month' column (ensure integer 1-12)
    if "Month" in df.columns:
        df["Month"] = df["Month"].apply(month_name_to_num).fillna(1).astype(int)
        df.loc[~df["Month"].between(1, 12), "Month"] = 1 # Invalid months become 1
    
    # Ensure string types for other columns
    string_cols = [c for c in INTERNAL_DF_COLS if c not in INTERNAL_NUMERIC_COLS and c != "Month"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("")

    # Select and reorder columns to match INTERNAL_DF_COLS
    available_cols = [col for col in [IDCOL] + INTERNAL_DF_COLS if col in df.columns]
    return df[available_cols]

def coerce_wide_schema_types(df: pd.DataFrame) -> pd.DataFrame:
    """Type coercion for the external wide schema DataFrame."""
    if df.empty:
        return pd.DataFrame(columns=[IDCOL] + WIDE_EXCEL_COLS)
    
    # Ensure all required columns exist
    for col in WIDE_EXCEL_COLS:
        if col not in df.columns:
            df[col] = pd.NA
    
    # Apply cleaning and convert numeric columns
    for col in WIDE_EXCEL_NUMERIC_COLS:
        if col in df.columns:
            df[col] = df[col].apply(clean_numeric_string)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    
    # Ensure string types for other columns
    string_cols = [c for c in WIDE_EXCEL_COLS if c not in WIDE_EXCEL_NUMERIC_COLS]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).fillna("")
    
    # Select and reorder columns
    available_cols = [col for col in [IDCOL] + WIDE_EXCEL_COLS if col in df.columns]
    return df[available_cols]

def recalc_wide_schema(df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    """Recalculates sales and GP for a wide-schema DataFrame."""
    if df.empty:
        return df
    
    prod_map = dict(zip(products_df["Product"].astype(str), products_df["Category"].astype(str)))
    df["Category"] = df.apply(
        lambda r: prod_map.get(str(r["Product"]), str(r.get("Category", "Unknown"))), 
        axis=1
    )
    
    # Calculate quarterly sales and GP
    df["Sales_Q1 (JOD)"] = ((df["Qty_Jan (MT)"] + df["Qty_Feb (MT)"] + df["Qty_Mar (MT)"]) * df["PMT_Q1 (JOD)"]).round(2)
    df["Sales_Q2 (JOD)"] = ((df["Qty_Apr (MT)"] + df["Qty_May (MT)"] + df["Qty_Jun (MT)"]) * df["PMT_Q2 (JOD)"]).round(2)
    df["Sales_Q3 (JOD)"] = ((df["Qty_Jul (MT)"] + df["Qty_Aug (MT)"] + df["Qty_Sep (MT)"]) * df["PMT_Q3 (JOD)"]).round(2)
    df["Sales_Q4 (JOD)"] = ((df["Qty_Oct (MT)"] + df["Qty_Nov (MT)"] + df["Qty_Dec (MT)"]) * df["PMT_Q4 (JOD)"]).round(2)
    
    # Total Sales
    df["Total_Sales (JOD)"] = (df["Sales_Q1 (JOD)"] + df["Sales_Q2 (JOD)"] + df["Sales_Q3 (JOD)"] + df["Sales_Q4 (JOD)"]).round(2)
    
    # Calculate GP for each quarter using the annual GP%
    gm_factor = df["GP %"] / 100.0
    df["GP_Q1 (JOD)"] = (df["Sales_Q1 (JOD)"] * gm_factor).round(2)
    df["GP_Q2 (JOD)"] = (df["Sales_Q2 (JOD)"] * gm_factor).round(2)
    df["GP_Q3 (JOD)"] = (df["Sales_Q3 (JOD)"] * gm_factor).round(2)
    df["GP_Q4 (JOD)"] = (df["Sales_Q4 (JOD)"] * gm_factor).round(2)
    
    # Total GP
    df["Total_GP (JOD)"] = (df["GP_Q1 (JOD)"] + df["GP_Q2 (JOD)"] + df["GP_Q3 (JOD)"] + df["GP_Q4 (JOD)"]).round(2)
    
    return df

def recalc_narrow_schema(df: pd.DataFrame, products_df: pd.DataFrame) -> pd.DataFrame:
    """Recalculation for individual monthly entries (narrow schema)"""
    if df.empty:
        return df
    
    prod_map = dict(zip(products_df["Product"].astype(str), products_df["Category"].astype(str)))
    df["Category"] = df.apply(
        lambda r: prod_map.get(str(r["Product"]), str(r.get("Category", "Unknown"))), 
        axis=1
    )
    
    df["Sales (JOD)"] = (df["Qty (MT)"] * df["PMT (JOD)"]).round(2)
    df["GP (JOD)"] = (df["Sales (JOD)"] * df["GP %"] / 100.0).round(2)
    
    return df

def ensure_row_id(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure all rows have unique IDs"""
    if df.empty:
        df[IDCOL] = []
        return df
    
    if IDCOL not in df.columns:
        df[IDCOL] = [str(uuid.uuid4()) for _ in range(len(df))]
    else:
        df[IDCOL] = df[IDCOL].fillna("").astype(str)
        mask = df[IDCOL].eq("")
        df.loc[mask, IDCOL] = [str(uuid.uuid4()) for _ in range(mask.sum())]
    return df

def convert_wide_to_narrow(df_wide: pd.DataFrame) -> pd.DataFrame:
    """Converts a wide-schema DataFrame into the internal narrow-schema format."""
    if df_wide.empty:
        return pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)

    work = df_wide.copy()
    month_qty_cols = [c for c in work.columns if c.startswith("Qty_") and c.endswith("(MT)")]
    
    if not month_qty_cols:
        return pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)

    id_vars_base = ["Business Unit", "Section", "Client", "Category", "Product", "GP %", "Sector", "Booked"]
    id_vars_pmt = [c for c in WIDE_EXCEL_COLS if c.startswith("PMT_Q")]
    id_vars = list(set(id_vars_base + id_vars_pmt + [IDCOL]))
    id_vars = [col for col in id_vars if col in work.columns]

    df_melted = work.melt(id_vars=id_vars, value_vars=month_qty_cols, var_name="MonthCol", value_name="Qty (MT)")

    month_map_name = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}
    df_melted["Month"] = df_melted["MonthCol"].str.extract(r"Qty_(\w+)\s*\(MT\)", expand=False).map(month_map_name).fillna(1).astype(int)
    
    df_melted = df_melted[df_melted["Qty (MT)"] > 0].reset_index(drop=True)

    if df_melted.empty:
        return pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)

    def get_monthly_pmt(row):
        mo = int(row["Month"])
        if mo in (1,2,3): return row.get("PMT_Q1 (JOD)", 0.0)
        if mo in (4,5,6): return row.get("PMT_Q2 (JOD)", 0.0)
        if mo in (7,8,9): return row.get("PMT_Q3 (JOD)", 0.0)
        if mo in (10,11,12): return row.get("PMT_Q4 (JOD)", 0.0)
        return 0.0
    
    df_melted["PMT (JOD)"] = df_melted.apply(get_monthly_pmt, axis=1)
    df_melted["GP %"] = pd.to_numeric(df_melted.get("GP %", 0.0), errors="coerce").fillna(0.0)
    df_melted["Sales (JOD)"] = (df_melted["Qty (MT)"] * df_melted["PMT (JOD)"]).round(2)
    df_melted["GP (JOD)"] = (df_melted["Sales (JOD)"] * df_melted["GP %"] / 100.0).round(2)

    final_df = df_melted[[col for col in [IDCOL] + INTERNAL_DF_COLS if col in df_melted.columns]]
    
    for col in INTERNAL_DF_COLS:
        if col not in final_df.columns:
            final_df[col] = 0.0 if col in INTERNAL_NUMERIC_COLS else ""
            if col == "Month": final_df[col] = 1

    return final_df[INTERNAL_DF_COLS]

def export_df_for_save(df_internal: pd.DataFrame) -> pd.DataFrame:
    """Prepares the internal narrow DataFrame for saving to Excel."""
    if df_internal.empty:
        return pd.DataFrame(columns=SAVE_EXCEL_COLS)
    
    save_df = df_internal.drop(columns=[IDCOL], errors="ignore").copy()
    
    for col in SAVE_EXCEL_COLS:
        if col not in save_df.columns:
            save_df[col] = pd.NA
    
    return save_df[SAVE_EXCEL_COLS]

# def create_master_template() -> io.BytesIO:
#     """Create enhanced master data template"""
#     buffer = io.BytesIO()
#     with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
#         clients_df = pd.DataFrame({"Client": ["Sample Client A", "Sample Client B"]})
#         clients_df.to_excel(writer, index=False, sheet_name="Clients")
        
#         products_df = pd.DataFrame({
#             "Product": ["Sample Product 1", "Sample Product 2"],
#             "Category": ["Category X", "Category Y"],
#             "Default_PMT": [100.0, 200.0],
#             "Default_GM%": [10.0, 15.0],
#         })
#         products_df.to_excel(writer, index=False, sheet_name="Products")
    
#     buffer.seek(0)
#     return buffer

def to_json_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Convert DataFrame to JSON records with better handling"""
    if df.empty:
        return []
    return json.loads(df.to_json(orient="records"))

def from_json_records(records: List[Dict[str, Any]], masters) -> pd.DataFrame:
    """Create DataFrame from JSON records with validation (expects narrow schema)"""
    if not records:
        return pd.DataFrame(columns=[IDCOL] + INTERNAL_DF_COLS)
    
    df = pd.DataFrame(records)
    df = coerce_narrow_schema_types(df)
    df = ensure_row_id(df)
    # Important: Recalculate using the session's specific masters
    df = recalc_narrow_schema(df, masters["products"])
    return df
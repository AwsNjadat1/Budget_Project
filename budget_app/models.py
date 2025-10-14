# budget_app/models.py

from . import db
from .data_utils import IDCOL
from datetime import datetime, timedelta

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    

class BudgetEntry(db.Model):
    __tablename__ = 'budget_entries'

    # The unique row ID from our original DataFrame
    _rid = db.Column(db.String(36), primary_key=True)
    
    # A column to store which user this entry belongs to
    user_id = db.Column(db.String(150), nullable=False, index=True)
    user_name = db.Column(db.String(255))

    # All the other data columns
    business_unit = db.Column(db.String(100))
    section = db.Column(db.String(100))
    client = db.Column(db.String(255))
    category = db.Column(db.String(100))
    product = db.Column(db.String(255))
    month = db.Column(db.Integer)
    qty_mt = db.Column(db.Float)
    pmt_usd = db.Column(db.Float)
    gp_percent = db.Column(db.Float)
    sales_usd = db.Column(db.Float)
    gp_usd = db.Column(db.Float)
    profit_per_ton = db.Column(db.Float)
    sector = db.Column(db.String(255))
    booked = db.Column(db.String(10))

    def to_dict(self):
        """Converts the database object to a dictionary for JSON serialization."""
        return {
            IDCOL: self._rid,
            "User ID": self.user_id,
            "User Name": self.user_name,
            "Business Unit": self.business_unit,
            "Section": self.section,
            "Client": self.client,
            "Category": self.category,
            "Product": self.product,
            "Month": self.month,
            "Qty (MT)": self.qty_mt,
            "PMT (USD)": self.pmt_usd,
            "GP %": self.gp_percent,
            "Sales (USD)": self.sales_usd,
            "GP (USD)": self.gp_usd,
            "Profit per Ton": self.profit_per_ton,
            "Sector": self.sector,
            "Booked": self.booked
        }
        
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(150), nullable=False, index=True)
    user_name = db.Column(db.String(255))
    action = db.Column(db.String(100), nullable=False, index=True) # e.g., 'CREATE_ENTRY', 'DELETE_CLIENT'
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow() + timedelta(hours= 3))
    details = db.Column(db.Text, nullable=True) # For extra info, like the ID of the deleted entry

    def __repr__(self):
        return f"<AuditLog {self.timestamp} - {self.user_name} - {self.action}>"
# budget_app/models.py

from . import db
from .data_utils import IDCOL

class BudgetEntry(db.Model):
    __tablename__ = 'budget_entries'

    # The unique row ID from our original DataFrame
    _rid = db.Column(db.String(36), primary_key=True)
    
    # A column to store which user this entry belongs to
    # This is the key to separating data for different users!
    user_id = db.Column(db.String(150), nullable=False, index=True)

    # All the other data columns
    business_unit = db.Column(db.String(100))
    section = db.Column(db.String(100))
    client = db.Column(db.String(255))
    category = db.Column(db.String(100))
    product = db.Column(db.String(255))
    month = db.Column(db.Integer)
    qty_mt = db.Column(db.Float)
    pmt_jod = db.Column(db.Float)
    gp_percent = db.Column(db.Float)
    sales_jod = db.Column(db.Float)
    gp_jod = db.Column(db.Float)
    sector = db.Column(db.String(255))
    booked = db.Column(db.String(10))

    def to_dict(self):
        """Converts the database object to a dictionary for JSON serialization."""
        return {
            IDCOL: self._rid,
            "Business Unit": self.business_unit,
            "Section": self.section,
            "Client": self.client,
            "Category": self.category,
            "Product": self.product,
            "Month": self.month,
            "Qty (MT)": self.qty_mt,
            "PMT (JOD)": self.pmt_jod,
            "GP %": self.gp_percent,
            "Sales (JOD)": self.sales_jod,
            "GP (JOD)": self.gp_jod,
            "Sector": self.sector,
            "Booked": self.booked
        }
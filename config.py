import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    # Add other configurations here if needed in the future
    # e.g., DATABASE_URI = 'sqlite:///budget.db'
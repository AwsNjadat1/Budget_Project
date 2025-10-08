# config.py

import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    
    # Azure AD configurations
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"

    # Database Configuration
    DB_SERVER = os.environ.get("DB_SERVER")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_DRIVER = os.environ.get("DB_DRIVER")

    # --- THIS IS THE FINAL, CORRECTED CONNECTION LOGIC ---
    # We URL-encode the password and the driver name to handle any special characters safely.
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    encoded_driver = urllib.parse.quote_plus(DB_DRIVER)
    
    # This is the standard and most reliable way to build the connection string.
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pyodbc://{DB_USER}:{encoded_password}@{DB_SERVER}:1433/"
        f"{DB_NAME}?driver={encoded_driver}"
    )
    # --- END OF FINAL, CORRECTED SECTION ---
    
    # Optional: Disable a SQLAlchemy feature that we don't need
    SQLALCHEMY_TRACK_MODIFICATIONS = False
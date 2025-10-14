# config.py

import os
from dotenv import load_dotenv
import urllib.parse

# Load all the secret variables from the .env file into the environment
load_dotenv()

class Config:
    """
    Base application configuration.
    Loads settings from environment variables for security and flexibility.
    """
    # Secret key for session management (e.g., cookies).
    # Falls back to a random key if not set in the environment.
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    
    # Azure Active Directory configurations for user login
    AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
    AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET")
    AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID")
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}"

    # Database Configuration from environment variables
    DB_SERVER = os.environ.get("DB_SERVER")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASSWORD = os.environ.get("DB_PASSWORD")
    DB_DRIVER = os.environ.get("DB_DRIVER")
    
    # Exchange Rates Configuration
    # All rates are defined as 1 USD to the target currency.
    EXCHANGE_RATES = {
        'USD': 1.0,
        'JOD': 0.71,  # As specified: 1 USD = 0.71 JOD
        'EUR': 0.86,  # As specified: 1 USD = 0.86 EUR
    }
    
    # 1. URL-encode the password to handle any special characters safely.
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD)
    
    # 2. For the driver name, the ODBC standard requires replacing spaces with a '+'.
    safe_driver = DB_DRIVER.replace(' ', '+')

    # 3. Construct the final SQLAlchemy Database URI (the connection string).
    # All parameters after the '?' must be separated by an ampersand '&'.
    SQLALCHEMY_DATABASE_URI = (
        f"mssql+pyodbc://{DB_USER}:{encoded_password}@{DB_SERVER}:1433/"
        f"{DB_NAME}?driver={safe_driver}&timeout=60&charset=utf8"  # <-- Semicolons (;) changed to ampersands (&)
    )
    
    
    # This setting disables a Flask-SQLAlchemy feature that we don't need
    # and helps reduce memory overhead.
    SQLALCHEMY_TRACK_MODIFICATIONS = False
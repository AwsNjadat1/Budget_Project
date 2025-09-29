import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    # Add Auth0 configuration
    AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
    AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID")
    AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET")
    AUTH0_API_AUDIENCE = f'https://{os.environ.get("AUTH0_DOMAIN")}/api/v2/'
    
    # Add other configurations here if needed in the future
    # e.g., DATABASE_URI = 'sqlite:///budget.db'
# gunicorn.conf.py
# Binds the server to the port provided by Azure
bind = "0.0.0.0:8000"
# Sets the number of worker processes to handle requests
workers = 4
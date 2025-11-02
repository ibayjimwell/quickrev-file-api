# ======================================
# core/cloud/appwrite.py (CONFIRMED STRUCTURE)
# ======================================

import os
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.databases import Databases
from appwrite.services.account import Account

# --- Configuration (Load from Environment Variables) ---
APPWRITE_ENDPOINT = os.environ.get("APPWRITE_ENDPOINT") 
APPWRITE_PROJECT_ID = os.environ.get("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY = os.environ.get("APPWRITE_API_KEY")

client = Client() 
(client
    .set_endpoint(APPWRITE_ENDPOINT)
    .set_project(APPWRITE_PROJECT_ID)
    .set_key(APPWRITE_API_KEY)
)

cloud_storage = Storage(client)
cloud_database = Databases(client)
cloud_account = Account(client)

    
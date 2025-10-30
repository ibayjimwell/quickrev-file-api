import os
from appwrite.client import Client
from appwrite.services.storage import Storage
from appwrite.services.databases import Databases
from appwrite.services.account import Account

# --- Configuration (Load from Environment Variables) ---
APPWRITE_ENDPOINT = os.environ.get("APPWRITE_ENDPOINT") 
APPWRITE_PROJECT_ID = os.environ.get("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY = os.environ.get("APPWRITE_API_KEY")

# --- Initialize Appwrite Client ---
client = Client()
(client
 .set_endpoint(APPWRITE_ENDPOINT)
 .set_project(APPWRITE_PROJECT_ID)
 .set_key(APPWRITE_API_KEY)
 )

# --- Initialize Appwrite Services ---
storage = Storage(client)
database = Databases(client)
account = Account(client)

# Export the Storage instance
cloud_storage = storage
cloud_database = database
cloud_account = account
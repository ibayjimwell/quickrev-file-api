# dependencies/auth.py (REVISED)

import os
from fastapi import Request, HTTPException, status
from starlette.concurrency import run_in_threadpool # 👈 NEW IMPORT
from appwrite.exception import AppwriteException

# Import the initialized account service from client setup
from core.cloud.appwrite import cloud_account

async def get_appwrite_user(request: Request):
    """
    Dependency that extracts the Appwrite Session Cookie, validates it 
    using the Server SDK, and returns the authenticated user's $id.
    """
    APPWRITE_PROJECT_ID = os.environ.get("APPWRITE_PROJECT_ID")
    session_cookie_name = f"a_session_{APPWRITE_PROJECT_ID}"
    session_cookie = request.cookies.get(session_cookie_name)

    if not session_cookie:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Session cookie missing.",
        )

    # Define the synchronous operation as a lambda function
    def fetch_user_sync():
        # Set the session cookie for the SDK client
        cloud_account.client.headers['X-Appwrite-Session'] = session_cookie
        try:
            # Synchronous call
            return cloud_account.get() 
        finally:
            # Always clear the header in the same thread where it was set
            if 'X-Appwrite-Session' in cloud_account.client.headers:
                del cloud_account.client.headers['X-Appwrite-Session']

    try:
        # 💡 CRITICAL FIX: Run the synchronous Appwrite call in a background thread
        user = await run_in_threadpool(fetch_user_sync)
        
        return user['$id'] 
        
    except AppwriteException as e:
        # Session is invalid or expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {e.message}",
        )
    except Exception as e:
        # Handle other potential exceptions (e.g., network issues)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server authentication error: {e}",
        )
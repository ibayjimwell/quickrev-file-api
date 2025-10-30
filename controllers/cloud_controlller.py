import os
import tempfile
from typing import Dict, Any
from fastapi import UploadFile, File, HTTPException, status, Form, Depends
from appwrite.id import ID
from appwrite.input_file import InputFile
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.exception import AppwriteException
from core.cloud.appwrite import cloud_storage, cloud_database
from core.dependencies.auth import get_appwrite_user

# Configuration Constants
APPWRITE_BUCKET_ID = os.environ.get("APPWRITE_BUCKET_ID")
APPWRITE_DATABASE_ID = os.environ.get("APPWRITE_DATABASE_ID")
FILE_COLLECTION_ID = os.environ.get("FILE_COLLECTION_ID", "files") 


async def upload_file_endpoint(
        file: UploadFile = File(...),
        user_id: str = Depends(get_appwrite_user),
    ) -> Dict[str, Any]:
    
    # Determine file details
    original_file_name = file.filename
        
    # Variables for temp file cleanup
    temp_input_path = None
    new_file_id = ID.unique()

    try:
        # --- Save Uploaded File to Temporary Location ---
        
        # Write file bytes to a temporary local file
        temp_input_path = f"{tempfile.gettempdir()}/{original_file_name}"
        content = await file.read()
        with open(temp_input_path, "wb") as tmp_file:
            tmp_file.write(content)
        
        # --- Upload File to Appwrite Storage ---
        
        # Create the Appwrite InputFile wrapper (using the reliable from_path)
        file_wrapper = InputFile.from_path(
            path=temp_input_path,
        )
        
        # Define permissions for the new file
        permissions_list = [
            Permission.read(Role.user(user_id)), 
            Permission.write(Role.user(user_id)),
            Permission.update(Role.user(user_id)),
            Permission.delete(Role.user(user_id)),
        ]

        # Upload the file using the pre-generated ID
        upload_result = cloud_storage.create_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=new_file_id, 
            file=file_wrapper,
            permissions=permissions_list,
        )
        # The file ID is new_file_id

        # --- Log Metadata to Appwrite Database (FOR LISTING) ---
        
        doc_data = {
            "user_id": user_id,
            "type": "original", 
            "name": os.path.splitext(original_file_name)[0],
            "file_id": new_file_id,
            "source_file_id": "source"
        }

        # Store document with user read permissions
        cloud_database.create_document(
            database_id=APPWRITE_DATABASE_ID,
            collection_id=FILE_COLLECTION_ID,
            document_id=ID.unique(),
            data=doc_data,
            permissions=[Permission.read(Role.user(user_id))]
        )
        
        # --- Return Success ---
        return {
            "success": True, 
            "message": "File uploaded successfully and ready for processing.",
            "file_id": new_file_id,
            "file_name": original_file_name
        }

    except AppwriteException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Appwrite Error: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": f"Upload failed: {str(e)}"}
        )

    finally:
        # --- Clean up temporary files ---
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
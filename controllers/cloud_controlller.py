import os
import io
import tempfile
from typing import Dict, Any, List
from fastapi import UploadFile, File, HTTPException, status, Form, Query # Import Query for optional params
from appwrite.id import ID
from appwrite.input_file import InputFile
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.query import Query as AppwriteQuery # Alias to avoid conflict with FastAPI's Query
from appwrite.exception import AppwriteException
from core.cloud.appwrite import cloud_storage, cloud_database
from fastapi.responses import StreamingResponse

APPWRITE_BUCKET_ID = os.environ.get("APPWRITE_BUCKET_ID")
APPWRITE_DATABASE_ID = os.environ.get("APPWRITE_DATABASE_ID")
FILE_COLLECTION_ID = os.environ.get("FILE_COLLECTION_ID", "files") 

# 💡 CHANGE: Removed Depends, added user_id via Form
async def upload_file_endpoint(
    file: UploadFile = File(...),
    user_id: str = Form(...), # 👈 The user_id is now passed as form data
) -> Dict[str, Any]:
    
    # 1. ⚙️ Pre-Flight Configuration Check (Remains the same)
    missing_config = []
    if not APPWRITE_BUCKET_ID:
        missing_config.append("APPWRITE_BUCKET_ID")
    if not APPWRITE_DATABASE_ID:
        missing_config.append("APPWRITE_DATABASE_ID")
    if not FILE_COLLECTION_ID:
        missing_config.append("FILE_COLLECTION_ID")

    if missing_config:
        print(f"CRITICAL CONFIG ERROR: Missing variables: {', '.join(missing_config)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server Configuration Error: The backend is missing the following Appwrite environment IDs: {', '.join(missing_config)}. Please check your .env file or deployment setup.",
        )
        
    original_file_name = file.filename
    temp_input_path = None
    new_file_id = ID.unique()

    try:
        # --- Save Uploaded File to Temporary Location ---
        temp_input_path = f"{tempfile.gettempdir()}/{original_file_name}"
        # We must use await file.read() here
        content = await file.read() 
        with open(temp_input_path, "wb") as tmp_file:
            tmp_file.write(content)
        
        # --- Upload File to Appwrite Storage ---
        file_wrapper = InputFile.from_path(path=temp_input_path)
        
        # 💡 CHANGE: Permissions still require the user_id for security
        permissions_list = [
            Permission.read(Role.user(user_id)), 
            Permission.write(Role.user(user_id)),
            Permission.update(Role.user(user_id)),
            Permission.delete(Role.user(user_id)),
        ]
        
        # Assuming synchronous call works for now
        upload_result = cloud_storage.create_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=new_file_id, 
            file=file_wrapper,
            permissions=permissions_list,
        )

        # --- Log Metadata to Appwrite Database (FOR LISTING) ---
        doc_data = {
            "user_id": user_id, # 👈 Use the passed user_id
            "type": "original", 
            "name": os.path.splitext(original_file_name)[0],
            "file_id": new_file_id,
            "source_file_id": new_file_id # The source is itself
        }

        # Assuming synchronous call works for now
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

    # 2. 🚨 Exception Handling (Remains the same)
    except AppwriteException as e:
        error_detail = f"Appwrite API Call Failed. Status: {e.code}. Message: {e.message}. Service: Storage/Database."
        print(f"APPWRITE FAILURE: {error_detail}")
        
        status_code = status.HTTP_400_BAD_REQUEST if e.code < 500 else status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(
            status_code=status_code,
            detail=error_detail
        )
        
    # 3. 🛑 General Exception Handling (Remains the same)
    except Exception as e:
        print(f"GENERAL UPLOAD FAILURE: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred during file handling: {type(e).__name__} - {str(e)}"
        )

    finally:
        # --- Clean up temporary files (Remains the same) ---
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception as e:
                print(f"Warning: Failed to clean up temp file {temp_input_path}: {e}")


# 🚀 NEW ENDPOINT: files_listing_endpoint
# This endpoint retrieves a list of the user's uploaded "original" files (Lessons).
async def files_listing_endpoint(
    user_id: str = Query(..., description="The ID of the user whose files to retrieve."),
    type: str = Query("original", description="The type of file to filter by (default: original).")
) -> Dict[str, Any]:
    
    # 1. ⚙️ Pre-Flight Configuration Check
    missing_config = []
    if not APPWRITE_DATABASE_ID:
        missing_config.append("APPWRITE_DATABASE_ID")
    if not FILE_COLLECTION_ID:
        missing_config.append("FILE_COLLECTION_ID")

    if missing_config:
        print(f"CRITICAL CONFIG ERROR: Missing variables: {', '.join(missing_config)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server Configuration Error: The backend is missing the following Appwrite environment IDs: {', '.join(missing_config)}. Please check your .env file or deployment setup.",
        )
        
    try:
        # --- Construct Appwrite Queries ---
        queries = [
            AppwriteQuery.equal("user_id", user_id),
            AppwriteQuery.equal("type", type),
            AppwriteQuery.order_desc("$updatedAt")
        ]

        # --- Fetch Documents from Appwrite Database ---
        # Note: Appwrite synchronous calls must still be wrapped in run_in_threadpool if
        # the Appwrite client is synchronous. Assuming cloud_database calls work.
        documents = cloud_database.list_documents(
            database_id=APPWRITE_DATABASE_ID,
            collection_id=FILE_COLLECTION_ID,
            queries=queries
        )
        
        # --- Process and Format Results ---
        # We extract only the required fields: name, file_id, and updated_at
        file_list: List[Dict[str, Any]] = []
        for doc in documents.get('documents', []):
            file_list.append({
                "name": doc.get('name'),
                "file_id": doc.get('file_id'),
                "updated_at": doc.get('$updatedAt'), # Appwrite uses $updatedAt for last update time
                "document_id": doc.get('$id')
            })
        
        # --- Return Success ---
        return {
            "success": True, 
            "message": f"Successfully retrieved {len(file_list)} files of type '{type}' for user {user_id}.",
            "files": file_list
        }

    # 2. 🚨 Appwrite Exception Handling
    except AppwriteException as e:
        error_detail = f"Appwrite API Call Failed. Status: {e.code}. Message: {e.message}. Service: Database."
        print(f"APPWRITE FAILURE: {error_detail}")
        
        status_code = status.HTTP_400_BAD_REQUEST if e.code < 500 else status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(
            status_code=status_code,
            detail=error_detail
        )
        
    # 3. 🛑 General Exception Handling
    except Exception as e:
        print(f"GENERAL LISTING FAILURE: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred during file listing: {type(e).__name__} - {str(e)}"
        )
    
async def view_file_endpoint(

    file_id: str = Query(..., description="The ID of the file to view (Appwrite file_id).")

) -> StreamingResponse: # 👈 The return type is StreamingResponse

   

    # 1. ⚙️ Pre-Flight Configuration Check

    if not APPWRITE_BUCKET_ID:

        print("CRITICAL CONFIG ERROR: Missing APPWRITE_BUCKET_ID")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail="Server Configuration Error: APPWRITE_BUCKET_ID is missing."

        )

       

    try:

        # --- Fetch the File Stream from Appwrite Storage ---

        # Appwrite's get_file_view returns the file as a stream of bytes.

        file_stream = cloud_storage.get_file_view(

            bucket_id=APPWRITE_BUCKET_ID,

            file_id=file_id

        )



        # NOTE: Appwrite's get_file_view often returns bytes directly.

        # We need to wrap it in an IO stream for FastAPI's StreamingResponse.

       

        # --- Fetch File Metadata to get Content-Type ---

        # The content type is crucial for the browser to display the file correctly.

        file_metadata = cloud_storage.get_file(

            bucket_id=APPWRITE_BUCKET_ID,

            file_id=file_id

        )

       

        mime_type = file_metadata.get('mimeType', 'application/octet-stream')

       

        # --- Return the File using StreamingResponse ---

        # This streams the file directly to the client.

        return StreamingResponse(

            content=io.BytesIO(file_stream),

            media_type=mime_type, # Essential for browser viewing

            # We explicitly *don't* set 'Content-Disposition: attachment' to force viewing

            headers={

                "Content-Length": str(len(file_stream)),

                "Cache-Control": "public, max-age=31536000"

            }

        )



    # 2. 🚨 Appwrite Exception Handling

    except AppwriteException as e:

        error_detail = f"Appwrite API Call Failed. Status: {e.code}. Message: {e.message}. Service: Storage."

        print(f"APPWRITE FAILURE: {error_detail}")

       

        # Handle "File not found" specifically

        if e.code == 404:

             raise HTTPException(

                status_code=status.HTTP_404_NOT_FOUND,

                detail=f"The requested file (ID: {file_id}) was not found in storage."

            )

       

        status_code = status.HTTP_400_BAD_REQUEST if e.code < 500 else status.HTTP_500_INTERNAL_SERVER_ERROR



        raise HTTPException(

            status_code=status_code,

            detail=error_detail

        )

       

    # 3. 🛑 General Exception Handling

    except Exception as e:

        print(f"GENERAL FILE VIEW FAILURE: {type(e).__name__}: {str(e)}")

        raise HTTPException(

            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,

            detail=f"An unexpected server error occurred during file viewing: {type(e).__name__} - {str(e)}"

        )
    

async def file_association_endpoint(
    source_file_id: str = Query(..., description="The Appwrite file_id of the original lesson file (the source).")
) -> Dict[str, Any]:
    
    # 1. ⚙️ Pre-Flight Configuration Check
    missing_config = []
    if not APPWRITE_DATABASE_ID:
        missing_config.append("APPWRITE_DATABASE_ID")
    if not FILE_COLLECTION_ID:
        missing_config.append("FILE_COLLECTION_ID")

    if missing_config:
        print(f"CRITICAL CONFIG ERROR: Missing variables: {', '.join(missing_config)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Server Configuration Error: Missing the following Appwrite environment IDs: {', '.join(missing_config)}."
        )
        
    try:
        # --- Construct Appwrite Queries ---
        # 1. Match the provided source_file_id
        # 2. Exclude the original file itself (where source_file_id == file_id)
        # 3. Order by creation date descending
        queries = [
            AppwriteQuery.equal("source_file_id", source_file_id),
            AppwriteQuery.not_equal("file_id", source_file_id), # Exclude the source file itself
            AppwriteQuery.order_desc("$updatedAt")
        ]

        # --- Fetch Documents from Appwrite Database ---
        documents = cloud_database.list_documents(
            database_id=APPWRITE_DATABASE_ID,
            collection_id=FILE_COLLECTION_ID,
            queries=queries
        )
        
        # --- Process and Format Results ---
        file_list: List[Dict[str, Any]] = []
        for doc in documents.get('documents', []):
            file_list.append({
                "type": doc.get('type'),
                "name": doc.get('name'),
                "file_id": doc.get('file_id'),
                "updated_at": doc.get('$updatedAt'), 
                "document_id": doc.get('$id')
            })
        
        # --- Return Success ---
        return {
            "success": True, 
            "message": f"Successfully retrieved {len(file_list)} associated files for source ID {source_file_id}.",
            "files": file_list
        }

    # 2. 🚨 Appwrite Exception Handling
    except AppwriteException as e:
        error_detail = f"Appwrite API Call Failed. Status: {e.code}. Message: {e.message}. Service: Database."
        print(f"APPWRITE FAILURE: {error_detail}")
        
        status_code = status.HTTP_400_BAD_REQUEST if e.code < 500 else status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(
            status_code=status_code,
            detail=error_detail
        )
        
    # 3. 🛑 General Exception Handling
    except Exception as e:
        print(f"GENERAL ASSOCIATION FAILURE: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred during file association retrieval: {type(e).__name__} - {str(e)}"
        )
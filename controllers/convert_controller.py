import os
import tempfile
from fastapi import HTTPException, status, Form
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask # Correct import for background task
from appwrite.exception import AppwriteException

from core.cloud.appwrite import cloud_storage
from core.converter.converters import convert_md_to_docx 

# Configuration Constant
APPWRITE_BUCKET_ID = os.environ.get("APPWRITE_BUCKET_ID")
DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

# Helper function to run cleanup in the background
def cleanup_temp_files(path1: str, path2: str):
    """Deletes temporary files after the response is sent."""
    async def cleanup():
        if os.path.exists(path1):
            os.remove(path1)
        if os.path.exists(path2):
            os.remove(path2)
    # Use BackgroundTask for Starlette/FastAPI's preferred way of handling cleanup
    return BackgroundTask(cleanup)

from pydantic import BaseModel
from typing import Optional
from fastapi import Body
class DocxConvertRequest(BaseModel):
    """
    Request model for DOCX conversion where both fields are optional.
    If 'content' is missing, the endpoint logic will fall back to downloading
    the content using 'reviewer_file_id'.
    """
    reviewer_file_id: Optional[str] = None
    content: Optional[str] = None # REVISED: Now Optional[str] with default of None

async def download_reviewer_docx_endpoint(
    request_data: DocxConvertRequest = Body(...),
):
    """
    Converts MD content to DOCX. It prioritizes the 'content' field from the request body.
    If 'content' is missing, it falls back to downloading the file using 'reviewer_file_id'.
    """
    reviewer_file_id = request_data.reviewer_file_id
    markdown_content = request_data.content
    
    # Check for minimum required data
    if not markdown_content and not reviewer_file_id:
         raise HTTPException(
             status_code=status.HTTP_400_BAD_REQUEST,
             detail={"success": False, "message": "Either 'content' or 'reviewer_file_id' must be provided for conversion."},
         )
    
    temp_md_path = None
    temp_docx_path = None
    original_file_name = "downloaded_document.md"
    
    try:
        # --- 1. Determine Content Source and Filename ---
        
        if not markdown_content and reviewer_file_id:
            # Scenario 2: Content missing, but ID provided -> Download from Appwrite
            
            # Get Metadata
            file_metadata = cloud_storage.get_file(
                bucket_id=APPWRITE_BUCKET_ID,
                file_id=reviewer_file_id
            )
            original_file_name = file_metadata.get('name') or original_file_name
            
            # Download Content
            md_file_bytes = cloud_storage.get_file_download(
                bucket_id=APPWRITE_BUCKET_ID,
                file_id=reviewer_file_id
            )
            markdown_content = md_file_bytes.decode('utf-8')

        elif markdown_content and reviewer_file_id:
            # Scenario 1 (Primary): Content provided, ID provided (for naming)
            
            # Get Metadata only for the filename
            try:
                file_metadata = cloud_storage.get_file(
                    bucket_id=APPWRITE_BUCKET_ID,
                    file_id=reviewer_file_id
                )
                original_file_name = file_metadata.get('name') or original_file_name
            except AppwriteException:
                # If metadata fails, continue with default name based on ID
                original_file_name = f"reviewer_file_{reviewer_file_id}.md"


        # --- 2. Setup Paths & Filename ---
        
        unique_prefix = reviewer_file_id or os.urandom(8).hex()
        temp_md_path = os.path.join(tempfile.gettempdir(), f"{unique_prefix}.md")
        temp_docx_path = os.path.join(tempfile.gettempdir(), f"{unique_prefix}.docx")
        
        # Construct the final output filename 
        base_name_no_ext = os.path.splitext(original_file_name)[0]
        output_filename = f"{base_name_no_ext.replace('(Reviewer) ', '')}.docx"
        
        # --- 3. Write Markdown Content to Temp File ---
        
        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        # --- 4. Perform the Conversion ---
        
        convert_md_to_docx(temp_md_path, temp_docx_path)

        # --- 5. Return DOCX as a FileResponse ---
        
        return FileResponse(
            path=temp_docx_path,
            filename=output_filename,
            media_type=DOCX_MIME_TYPE,
            background=cleanup_temp_files(temp_md_path, temp_docx_path)
        )

    except AppwriteException as e:
         # Specific handling for errors during content download
         detail_message = f"Cloud Storage Error during content retrieval: {e.message}"
         if e.code == 404:
              detail_message = "Reviewer file not found in cloud storage."
         
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail={"success": False, "message": detail_message},
         )

    except Exception as e:
        # General error handling
        
        if temp_md_path and os.path.exists(temp_md_path): os.remove(temp_md_path)
        if temp_docx_path and os.path.exists(temp_docx_path): os.remove(temp_docx_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": f"Conversion failed: {str(e)}"},
        )
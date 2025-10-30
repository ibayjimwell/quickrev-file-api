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

async def download_reviewer_docx_endpoint(
        reviewer_file_id: str = Form(...),
    ):
    """
    Downloads the reviewer MD file from Appwrite, converts it to DOCX, and forces download.
    The filename is fetched from Appwrite Storage metadata.
    """
    
    # Variables initialized to None for error handling/cleanup
    temp_md_path = None
    temp_docx_path = None
    
    try:
        # --- 1. Get File Metadata (Name) from Appwrite Storage ---
        
        file_metadata = cloud_storage.get_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=reviewer_file_id
        )
        original_file_name = file_metadata.get('name')
        if not original_file_name:
            raise Exception("File metadata is missing the file name.")

        # --- 2. Setup Paths ---
        
        # Use the file ID as a unique prefix for temp files
        unique_prefix = reviewer_file_id
        temp_md_path = os.path.join(tempfile.gettempdir(), f"{unique_prefix}.md")
        temp_docx_path = os.path.join(tempfile.gettempdir(), f"{unique_prefix}.docx")
        
        # Construct the final output filename based on the source MD file name
        # The MD file name should look like: "(Reviewer) Source Document Name.md"
        # We want the DOCX file to be: "Source Document Name.docx" or similar.
        
        # Remove the file extension (.md) and the "(Reviewer) " prefix if present.
        base_name_no_ext = os.path.splitext(original_file_name)[0]
        
        output_filename = f"{base_name_no_ext}.docx"
        
        # --- 3. Download Reviewer MD File from Appwrite ---
        
        md_file_bytes = cloud_storage.get_file_download(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=reviewer_file_id
        )

        # Write file bytes to a temporary local MD file
        with open(temp_md_path, "wb") as f:
            f.write(md_file_bytes)

        # --- 4. Perform the Conversion ---
        
        convert_md_to_docx(temp_md_path, temp_docx_path)

        # --- 5. Return DOCX as a FileResponse (Force Download) ---
        
        return FileResponse(
            path=temp_docx_path,
            filename=output_filename,
            media_type=DOCX_MIME_TYPE,
            background=cleanup_temp_files(temp_md_path, temp_docx_path)
        )

    except AppwriteException as e:
        # Appwrite error handling (e.g., file not found - 404)
        detail_message = f"Cloud Storage Error: {e.message}"
        if e.code == 404:
             detail_message = "Reviewer file not found in cloud storage."

        if temp_md_path and os.path.exists(temp_md_path): os.remove(temp_md_path)
        if temp_docx_path and os.path.exists(temp_docx_path): os.remove(temp_docx_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": detail_message},
        )
        
    except Exception as e:
        # General error handling (e.g., conversion failed)
        
        if temp_md_path and os.path.exists(temp_md_path): os.remove(temp_md_path)
        if temp_docx_path and os.path.exists(temp_docx_path): os.remove(temp_docx_path)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": f"Conversion failed: {str(e)}"},
        )
import os
import json
from typing import Dict, Any
import tempfile
from fastapi import UploadFile, File, Form, HTTPException, Response, status, Depends
from appwrite.id import ID
from appwrite.input_file import InputFile
from appwrite.permission import Permission
from appwrite.role import Role
from appwrite.exception import AppwriteException

from core.converter.converters import convert_pdf_to_txt, convert_pptx_to_txt, convert_docx_to_txt, convert_txt_to_txt
from core.cleaner.cleaner import clean_txt
from core.generator.generators import generate_reviewer, generate_flashcards
from core.cloud.appwrite import cloud_storage, cloud_database

async def generate_reviewer_endpoint(
    file_id: str = Form(...),
    user_id: str = Form(...),
):
    # Configuration Constants
    APPWRITE_BUCKET_ID = os.environ.get("APPWRITE_BUCKET_ID")
    APPWRITE_DATABASE_ID = os.environ.get("APPWRITE_DATABASE_ID")

    # Map file extensions to their respective converter functions
    # NOTE: You should map based on the file extension/type found in metadata.
    converters = {
        "pdf": convert_pdf_to_txt,
        "pptx": convert_pptx_to_txt,
        "docx": convert_docx_to_txt,
        "txt": convert_txt_to_txt
    }

    # Variables for temp file cleanup
    temp_input_path = None
    temp_output_path = None
    original_file_name = None
    file_type = None

    try:
        # --- 1. Get File Metadata from Appwrite Storage ---
        file_metadata = cloud_storage.get_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=file_id
        )
        
        # Extract name and type from metadata
        original_file_name = file_metadata.get('name')
        
        # Get the file extension (the file type)
        # Using os.path.splitext is a robust way to get the extension
        file_extension = os.path.splitext(original_file_name)[1].lstrip('.').lower()
        file_type = file_extension # file_type will be 'pdf', 'docx', etc.

        if file_type not in converters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail={"success": False, "message": f"Unsupported file type: {file_type}"}
            )

        # --- 2. Download Original File from Appwrite ---
        
        # Fetch the file bytes from Appwrite
        file_bytes = cloud_storage.get_file_download(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=file_id
        )

        # Write file bytes to a temporary local file (required by converters)
        temp_input_path = f"{tempfile.gettempdir()}/{file_id}.{file_type}"
        with open(temp_input_path, "wb") as tmp_file:
            tmp_file.write(file_bytes)
        
        # --- 3. Process and Generate Reviewer Content ---
        
        # Convert the file into raw text
        converter_func = converters[file_type]
        raw_text = converter_func(temp_input_path)

        # Clean and Generate the reviewer markdown
        clean_text = clean_txt(raw_text)
        reviewer_md = generate_reviewer(clean_text)

        # --- 4. Upload Generated Markdown to Appwrite Storage ---
        
        # Create the output file name using the ORIGINAL file name
        output_base_name = os.path.splitext(original_file_name)[0]
        output_file_name = f"(Reviewer) {output_base_name}.md"
        temp_output_path = f"{tempfile.gettempdir()}/{output_file_name}"
        
        # Write the Markdown content to a temporary file
        with open(temp_output_path, "w", encoding="utf-8") as tmp_md_file:
            tmp_md_file.write(reviewer_md)

        # Create the Appwrite InputFile wrapper
        # The 'from_path' method reads the file content from the path during the upload call.
        md_file_wrapper = InputFile.from_path(
            path=temp_output_path,
        )

        # Define permissions for the new MD file
        permissions_list = [
            Permission.read(Role.user(user_id)), 
            Permission.write(Role.user(user_id)),
            Permission.update(Role.user(user_id)),
            Permission.delete(Role.user(user_id)),
        ]

        # Upload the new Markdown file
        md_upload_result = cloud_storage.create_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=ID.unique(),
            file=md_file_wrapper,
            permissions=permissions_list,
        )
        new_md_file_id = md_upload_result['$id']

        # --- 5. Log Metadata to Appwrite Database ---
        
        # Data to be stored
        doc_data = {
            "user_id": user_id,
            "type": "reviewer",
            "name": os.path.splitext(output_file_name)[0],
            "file_id": new_md_file_id,
            "source_file_id": file_id # Keep track of the original file
        }

        # Store document with user read permissions
        cloud_database.create_document(
            database_id=APPWRITE_DATABASE_ID,
            collection_id="files",
            document_id=ID.unique(),
            data=doc_data,
            permissions=[Permission.read(Role.user(user_id))]
        )
        
        # --- 6. Return Success ---
        return {
            "success": True, 
            "message": "Reviewer generated and uploaded successfully.",
            "file_id": new_md_file_id,
        }

    except AppwriteException as e:
        # Handle Appwrite-specific errors (e.g., file_id not found in get_file)
        # Attempt to decode error response safely
        try:
            error_detail = e.response.decode('utf-8')
        except:
            error_detail = str(e)

        # Check for specific 'File not found' error (often 404)
        if e.code == 404:
             error_message = "Source file not found in Appwrite Storage."
        else:
             error_message = f"Cloud API/DB Error: {error_detail}"

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": error_message}
        )
    except Exception as e:
        # General error handling
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": f"Generation failed: {str(e)}"}
        )

    finally:
        # --- Clean up all temporary files ---
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if temp_output_path and os.path.exists(temp_output_path):
            os.remove(temp_output_path)


async def generate_flashcards_endpoint(
    file_id: str = Form(...), 
    user_id: str = Form(...),
    items: int = Form(40),
    multiple_choice: bool = Form(True),
    identification: bool = Form(True),
    true_or_false: bool = Form(True),
    enumeration: bool = Form(True),
) -> Dict[str, Any]:
    
    # Configuration Constants
    APPWRITE_BUCKET_ID = os.environ.get("APPWRITE_BUCKET_ID")
    APPWRITE_DATABASE_ID = os.environ.get("APPWRITE_DATABASE_ID")
    
    # Map file extensions to their respective converter functions
    # NOTE: You should map based on the file extension/type found in metadata.
    converters = {
        "pdf": convert_pdf_to_txt,
        "pptx": convert_pptx_to_txt,
        "docx": convert_docx_to_txt,
        "txt": convert_txt_to_txt
    }

    # Variables for temp file cleanup
    temp_input_path = None
    temp_output_path = None
    original_file_name = None
    file_type = None

    # Configuration for flashcard generation
    flashcards_config = {
        "num_items": items,
        "multiplechoice": multiple_choice,
        "identification": identification,
        "trueorfalse": true_or_false,
        "enumeration": enumeration
    }

    try:
        # --- 1. Get File Metadata from Appwrite Storage ---
        file_metadata = cloud_storage.get_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=file_id
        )
        
        # Extract name and type from metadata
        original_file_name = file_metadata.get('name')
        
        # Get the file extension (the file type)
        # Using os.path.splitext is a robust way to get the extension
        file_extension = os.path.splitext(original_file_name)[1].lstrip('.').lower()
        file_type = file_extension # file_type will be 'pdf', 'docx', etc.

        if file_type not in converters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail={"success": False, "message": f"Unsupported file type: {file_type}"}
            )

        # --- 2. Download Original File from Appwrite ---
        
        # Fetch the file bytes from Appwrite
        file_bytes = cloud_storage.get_file_download(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=file_id
        )

        # Write file bytes to a temporary local file (required by converters)
        temp_input_path = f"{tempfile.gettempdir()}/{file_id}.{file_type}"
        with open(temp_input_path, "wb") as tmp_file:
            tmp_file.write(file_bytes)
        
        # --- 3. Process and Generate Content ---
        
        # Convert the file into raw text
        converter_func = converters[file_type]
        raw_text = converter_func(temp_input_path)

        # Clean
        clean_text = clean_txt(raw_text)
        
        # --- 3. Generate Flashcards ---
        flashcards_json_string = generate_flashcards(clean_text, flashcards_config)
        
        # Convert the JSON string into a native Python object (list/dict) for response
        try:
            flashcards_array = json.loads(flashcards_json_string)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail={"success": False, "message": "LLM returned malformed JSON for flashcards."}
            )

        # --- 4. Upload Generated Flashcards JSON to Appwrite Storage ---
        
        # Create the output file name using the ORIGINAL file name
        output_base_name = os.path.splitext(original_file_name)[0]
        output_file_name = f"(Flashcards) {output_base_name}.json"
        temp_json_output_path = f"{tempfile.gettempdir()}/{output_file_name}"
        
        # Write content and ensure the file handle is closed
        with open(temp_json_output_path, "w", encoding='utf-8') as tmp_json_file:
            tmp_json_file.write(flashcards_json_string)

        # Create the Appwrite InputFile wrapper
        json_file_wrapper = InputFile.from_path(
            path=temp_json_output_path,
        )
        
        # Define permissions for the new JSON file
        permissions_list = [
            Permission.read(Role.user(user_id)), 
            Permission.write(Role.user(user_id)),
            Permission.update(Role.user(user_id)),
            Permission.delete(Role.user(user_id)),
        ]

        # Upload the new JSON file
        json_upload_result = cloud_storage.create_file(
            bucket_id=APPWRITE_BUCKET_ID,
            file_id=ID.unique(),
            file=json_file_wrapper,
            permissions=permissions_list,
        )
        new_json_file_id = json_upload_result['$id']
        
        # --- 5. Log Metadata to Appwrite Database ---
        
        doc_data = {
            "user_id": user_id,
            "type": "flashcards",
            "name": os.path.splitext(output_file_name)[0],
            "file_id": new_json_file_id,
            "source_file_id": file_id
        }

        # Store document with user read permissions
        cloud_database.create_document(
            database_id=APPWRITE_DATABASE_ID,
            collection_id="files", 
            document_id=ID.unique(),
            data=doc_data,
            permissions=[Permission.read(Role.user(user_id))]
        )
        
        # --- 6. Return Success ---
        return {
            "success": True, 
            "message": "Flashcards generated and uploaded successfully.",
            "file_id": new_json_file_id,
            "flashcards": flashcards_array
        }

    except AppwriteException as e:
        # Check for specific 'File not found' error (e.g., if reviewer_file_id is invalid)
        if e.code == 404:
            error_message = "Source reviewer file not found in Appwrite Storage."
        else:
            error_message = f"Appwrite Error: {e.message}"
            
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": error_message}
        )
    except Exception as e:
        # General error handling
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": f"Flashcard generation failed: {str(e)}"}
        )

    finally:
        # --- Clean up temporary files ---
        if temp_input_path and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        if temp_json_output_path and os.path.exists(temp_json_output_path):
            os.remove(temp_json_output_path)
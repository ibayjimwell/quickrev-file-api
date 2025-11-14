from fastapi import FastAPI, UploadFile, File, Form, Depends, APIRouter, Query
from controllers.generate_controller import generate_reviewer_endpoint, generate_flashcards_endpoint
from controllers.convert_controller import download_reviewer_docx_endpoint
from controllers.cloud_controlller import upload_file_endpoint, files_listing_endpoint, view_file_endpoint, file_association_endpoint
from fastapi.middleware.cors import CORSMiddleware

# Import environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="QuickRev File API",
    description="API for file operations for QuickRev",
    version="0.0.1"
)

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Allows Appwrite session cookies to be sent
    allow_methods=["*"],    # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],    # Allow all headers
)

# Root endpoint
@app.get("/")
async def root():
    return {"message": "Welcome to QuickRev File API"}

# Testing user id
@app.get("/68f77956003479c46bea")
async def tester():
    return {"68f77956003479c46bea"}

# Generate Reviewer Endpoint
@app.post("/generate/reviewer")
async def generate_reviewer(
        file_id: str = Form(...),
        user_id: str = Form(...),
    ):
    return await generate_reviewer_endpoint(file_id, user_id)

# Generate Flashcards Endpoint
@app.post("/generate/flashcards")
async def generate_flashcards(
        file_id: str = Form(...), 
        user_id: str = Form(...),
        # REVISED: Replaced 'items: int = Form(40)' with quiz type counts (default to 10 each)
        multiple_choice: int = Form(10),
        identification: int = Form(10),
        true_or_false: int = Form(10),
        enumeration: int = Form(10),
    ):
    return await generate_flashcards_endpoint(file_id, user_id, multiple_choice, identification, true_or_false, enumeration)

# Download Reviewer into DOCX Endpoint
@app.post("/download/reviewer/docx")
async def download_reviewer_docx(
        reviewer_file_id: str = Form(...),
    ):
    return await download_reviewer_docx_endpoint(reviewer_file_id)

# Upload File 
@app.post('/cloud/file/upload')
async def upload_file(
        file: UploadFile = File(...),
        user_id: str =Form(...),
    ):
    return await upload_file_endpoint(file, user_id)


# List Files
@app.get("/cloud/file/list")
async def files_listing(
        user_id: str = Query(..., description="The ID of the user whose files to retrieve."),
        type: str = Query("original", description="The type of file to filter by (default: original).")
    ):
    return await files_listing_endpoint(user_id, type)

# View File
@app.get("/cloud/file/view")
async def view_file(
        file_id: str = Query(..., description="The ID of the file to view (Appwrite file_id).")
    ):
    return await view_file_endpoint(file_id)

# List Association
@app.get("/cloud/file/associate")
async def file_association(
        source_file_id: str = Query(..., description="The Appwrite file_id of the original lesson file (the source).")
    ):
    return await file_association_endpoint(source_file_id)


from fastapi import FastAPI, UploadFile, File, Form, Depends, APIRouter
from controllers.generate_controller import generate_reviewer_endpoint, generate_flashcards_endpoint
from controllers.convert_controller import download_reviewer_docx_endpoint
from controllers.cloud_controlller import upload_file_endpoint
from core.dependencies.auth import get_appwrite_user
from fastapi.middleware.cors import CORSMiddleware


# Initialize FastAPI app
app = FastAPI(
    title="QuickRev File API",
    description="API for file operations for QuickRev",
    version="0.0.1"
)

origins = [
    "https://localhost:5173",  # Your Vite development server
    "https://127.0.0.1:5173",  # Just in case
    # Add any other deployment URLs here later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True, # Allows Appwrite session cookies to be sent
    allow_methods=["*"],    # Allow all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],    # Allow all headers
)

# --- NEW: Auth Router ---
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.get("/me")
async def get_current_user_endpoint(
    # The dependency runs first; if successful, user_id is the verified ID.
    user_id: str = Depends(get_appwrite_user) 
):
    """Returns the user's verified ID, confirming the session is active."""
    return {"user_id": user_id, "is_authenticated": True}

# Add the new router to the app
app.include_router(auth_router)

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
        user_id: str = Depends(get_appwrite_user),
    ):
    return await generate_reviewer_endpoint(file_id, user_id)

# Generate Flashcards Endpoint
@app.post("/generate/flashcards")
async def generate_flashcards(
        file_id: str = Form(...), 
        user_id: str = Depends(get_appwrite_user),
        items: int = Form(40),
        multiple_choice: bool = Form(True),
        identification: bool = Form(True),
        true_or_false: bool = Form(True),
        enumeration: bool = Form(True),
    ):
    return await generate_flashcards_endpoint(file_id, user_id, items, multiple_choice, identification, true_or_false, enumeration)

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
        user_id: str = Depends(get_appwrite_user),
    ):
    return await upload_file_endpoint(file, user_id)


import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def send_prompt(prompt: str) -> str:
    """
    Sends a prompt to the Gemini LLM and returns the response text.
    """
    try:
        # Initialize the LLM Client
        # You need to have the GEMINI_API_KEY environment variable set
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    except Exception as e:
        error_message = f"(Gemini) Error initializing Gemini client. Error: {e}"
        raise Exception(error_message)

    try:
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt
        )
        
        return response.text
        
    except Exception as e:
        error_message = f"An error occurred during LLM interaction: {e}"
        raise Exception(error_message)
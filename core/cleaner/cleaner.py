import re
from core.ai.gemini import send_prompt
from core.prompts.prompt import read_prompt

# Basic Pre-Cleaning
# This function is useful for general noise reduction
def basic_text_cleaning(raw_text: str) -> str:
    """Removes excessive whitespace and common doc artifacts."""
    if not isinstance(raw_text, str):
        return ""
    # Normalize line breaks and remove excessive whitespaces
    cleaned_text = re.sub(r'[\r\n]{3,}', '\n\n', raw_text)  # Keep double newlines for paragraph breaks
    cleaned_text = re.sub(r'[ \t]+', ' ', cleaned_text).strip()
    return cleaned_text


# LLM Intelligent Cleaning
def clean_txt(raw_text: str):
    """
    Uses an LLM to remove non-content elements (headers, footers) 
    and structure the core content (terms, lists) without summarizing.
    """
    cleaned_input = basic_text_cleaning(raw_text)

    # The Prompt: This is the instruction for the LLM.
    base_prompt = read_prompt('clean_raw_txt')

    final_prompt = f"""
    {base_prompt}
    {cleaned_input}
    """
    
    # Send the prompt to LLM and get the response
    cleaned_text = send_prompt(final_prompt)
    return cleaned_text
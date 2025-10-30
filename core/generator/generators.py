import json
from core.ai.gemini import send_prompt
from core.prompts.prompt import read_prompt

def generate_reviewer(content: str) -> str:

    # The Prompt: This is the instruction for the LLM.
    base_prompt = read_prompt('generate_reviewer')

    final_prompt = f"""
    {base_prompt}
    {content}
    """
    
    # Send the prompt to LLM and get the response
    generated_reviewer = send_prompt(final_prompt)
    return generated_reviewer
    

def generate_flashcards(content: str, config: dict) -> str:
    """
    Generates a list of flashcards in JSON format from the provided content
    based on the specified configuration. The prompt is strictly set for JSON-only output.
    """

    # Build the Constraints and Instructions
    enabled_types = []
    if config.get('trueorfalse'):
        enabled_types.append('True or False')
    if config.get('multiplechoice'):
        enabled_types.append('Multiple Choice')
    if config.get('identification'):
        enabled_types.append('Identification')
    if config.get('enumeration'):
        enabled_types.append('Enumeration')

    if not enabled_types:
        raise ValueError("At least one flashcard type must be enabled in the config.")
    
    types_list = ", ".join([f'"{t}"' for t in enabled_types])
    num_items = config.get('num_items', 40) 
    sort_order = "Multiple Choice, Identification, True or False, Enumeration"

    # Read the Prompt
    base_prompt = read_prompt('generate_flashcards')

    # Construct the Final Prompt
    # Note: We put the instructions and content AFTER the base_prompt
    # which starts with the strong "JSON ONLY" directive.
    final_prompt = f"""
    {base_prompt}

    --- INSTRUCTIONS ---
    1. The total number of flashcards to generate MUST be **{num_items}**.
    2. The only allowed values for the 'Type' field are: {types_list}.
    3. **SORTING REQUIREMENT**: The flashcards in the JSON array MUST be sorted by 'Type' in the following order: **{sort_order}**. Try to distribute the types evenly, maintaining this sort order.

    --- CONTENT TO ANALYZE ---
    ---
    {content}
    ---
    """
    
    # Send the prompt to LLM and get the response
    generated_flashcards = send_prompt(final_prompt)
    return generated_flashcards
    
    

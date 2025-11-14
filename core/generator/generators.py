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
    based on the specified configuration (now using quantities instead of booleans).
    The prompt is strictly set for JSON-only output.
    """

    # 1. Collect required types and their counts
    type_counts = {
        'Multiple Choice': config.get('multiplechoice', 0),
        'Identification': config.get('identification', 0),
        'True or False': config.get('trueorfalse', 0),
        'Enumeration': config.get('enumeration', 0),
    }

    # 2. Build the list of enabled types, their counts, and calculate total items
    enabled_types_instructions = []
    total_items = 0
    
    # Iterate through the desired sort order to build the instructions
    sort_order_types = [
        'Multiple Choice', 
        'Identification', 
        'True or False', 
        'Enumeration'
    ]

    for type_name in sort_order_types:
        count = type_counts[type_name]
        if count > 0:
            enabled_types_instructions.append(f"{type_name} (Quantity: {count})")
            total_items += count

    if total_items == 0:
        # This check is technically handled earlier in generate_flashcards_endpoint, 
        # but it's good practice to keep here for safety.
        raise ValueError("The total number of flashcard items requested is zero.")
    
    # Format the list of types and their quantities for the prompt
    types_quantity_list = "\n * ".join(enabled_types_instructions)
    
    # Read the Prompt (assuming read_prompt is defined elsewhere)
    base_prompt = read_prompt('generate_flashcards')

    # 3. Construct the Final Prompt
    final_prompt = f"""
    {base_prompt}

    --- INSTRUCTIONS ---
    1. The total number of flashcards to generate MUST be **{total_items}**.
    2. The required breakdown of flashcard types and their exact quantities are:
     * {types_quantity_list}
    3. **SORTING REQUIREMENT**: The flashcards in the JSON array MUST be sorted by 'Type' in the following order: **Multiple Choice, Identification, True or False, Enumeration**.
    4. **QUANTITY REQUIREMENT**: Strictly adhere to the quantity specified for each type.

    --- CONTENT TO ANALYZE ---
    ---
    {content}
    ---
    """
    
    # Send the prompt to LLM and get the response (assuming send_prompt is defined elsewhere)
    generated_flashcards = send_prompt(final_prompt)
    return generated_flashcards
    
    

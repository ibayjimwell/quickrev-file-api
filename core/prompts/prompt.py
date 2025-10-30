
def read_prompt(prompt_name: str) -> str:
    """
    Reads the content of a prompt file given its name.
    
    """
    prompt_path = f'core/prompts/{prompt_name}.txt'
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file '{prompt_path}' not found.")
    except Exception as e:
        raise Exception(f"Error reading prompt file '{prompt_path}': {e}")
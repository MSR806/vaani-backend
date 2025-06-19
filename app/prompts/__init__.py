"""
Initialization module for prompts package with helper functions.
"""


def format_prompt(template: str, **kwargs) -> str:
    """
    Format a prompt template by replacing double curly braces with provided values.

    Args:
        template (str): The template string containing variables in double curly braces
                       format like {{variable_name}}
        **kwargs: Variable keyword arguments containing the values to substitute

    Returns:
        str: The formatted prompt with all variables replaced

    Example:
        >>> template = "Hello {{name}}, welcome to {{place}}!"
        >>> format_prompt(template, name="John", place="Earth")
        "Hello John, welcome to Earth!"
    """
    result = template
    for key, value in kwargs.items():
        placeholder = f"{{{{%s}}}}" % key
        result = result.replace(placeholder, str(value))
    return result

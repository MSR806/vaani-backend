import urllib.parse

async def generate_placeholder_image(text="Placeholder", width=1024, height=1792):
    """
    Generate a placeholder image using placehold.co service.
    
    Args:
        text: Text to display on the image
        width: Image width (default: 1024)
        height: Image height (default: 1792)
        
    Returns:
        URL to the placeholder image
    """
    # URL encode the text for the placeholder
    encoded_text = urllib.parse.quote(text)
    
    # Create the placeholder URL
    placeholder_url = f"https://placehold.co/{width}x{height}?text={encoded_text}"
    
    return placeholder_url

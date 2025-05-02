import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")

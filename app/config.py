import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./writers_llm.db") 
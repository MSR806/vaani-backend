import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")

# Auth0 Configuration
AUTH0_DOMAIN = "dev-6m3v7tgivuzrs5we.us.auth0.com"
AUTH0_API_AUDIENCE = "9a24492f-803c-461c-b051-f1dd7ce3c504"
AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"
AUTH0_ALGORITHMS = ["RS256"]

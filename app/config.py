import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

ENV = os.getenv("ENV", "local")

# Constants
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
XAI_API_KEY = os.getenv("XAI_API_KEY")
PORTKEY_API_KEY = os.getenv("PORTKEY_API_KEY")

# Auth0 Configuration
AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_API_AUDIENCE = os.getenv("AUTH0_API_AUDIENCE")
AUTH0_ISSUER = f"https://{AUTH0_DOMAIN}/"
AUTH0_ALGORITHMS = os.getenv("AUTH0_ALGORITHMS")


class STATSD:
    HOST = os.getenv("STATSD_HOST", "localhost")
    PORT = os.getenv("STATSD_PORT", 8125)

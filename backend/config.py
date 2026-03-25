# Configuration settings

from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from backend directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

NEWSAPI_KEY      = os.getenv("NEWSAPI_KEY")
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
APIFY_TOKEN      = os.getenv("APIFY_TOKEN")
DATABASE_URL     = os.getenv("DATABASE_URL")
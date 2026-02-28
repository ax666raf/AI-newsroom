# Configuration settings

from dotenv import load_dotenv
import os

load_dotenv()

NEWSAPI_KEY      = os.getenv("NEWSAPI_KEY")
GUARDIAN_API_KEY = os.getenv("GUARDIAN_API_KEY")
APIFY_TOKEN      = os.getenv("APIFY_TOKEN")
DATABASE_URL     = os.getenv("DATABASE_URL")
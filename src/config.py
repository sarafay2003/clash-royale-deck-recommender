"""
Central config: loads environment variables and defines shared constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

CLASH_ROYALE_API_KEY = os.getenv("CLASH_ROYALE_API_KEY")
BASE_URL = "https://api.clashroyale.com/v1"

if not CLASH_ROYALE_API_KEY:
    raise RuntimeError(
        "CLASH_ROYALE_API_KEY not found. Copy .env.example to .env and add your key."
    )
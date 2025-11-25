"""
Environment Variables Loader
Load environment variables from .env file before settings are initialized
"""

from pathlib import Path
from dotenv import load_dotenv

# Determine the base directory (where this file is located)
BASE_DIR = Path(__file__).resolve().parent

# Load .env file from the base directory
env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"Loaded environment variables from {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")
    print("Using system environment variables or defaults")

import sys
import os

# Add parent directory to sys.path so app and core can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Top-level exports required by Vercel's Python runtime
from app import app

application = app
handler = app

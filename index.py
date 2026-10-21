"""WSGI entrypoint for Vercel's Flask framework preset."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / 'backend'))
from backend.app import app

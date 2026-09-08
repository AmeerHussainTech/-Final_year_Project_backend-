import sys
import os

# Ensure root directory is on sys.path for module resolution on Vercel
ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from main import app

# Expose app for Vercel WSGI runner
# Vercel looks for `app` or `handler`
handler = app

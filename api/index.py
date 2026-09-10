import sys
import os

# Add parent directory to sys.path so app and core can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app

# WSGI middleware to restore original request path on Vercel rewrites
class VercelPathFix:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        raw_uri = environ.get("HTTP_X_FORWARDED_URI") or environ.get("RAW_URI") or environ.get("HTTP_X_MATCHED_PATH")
        if raw_uri:
            environ["PATH_INFO"] = raw_uri.split("?")[0]
        elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py", "/api"):
            environ["PATH_INFO"] = "/"
        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFix(app.wsgi_app)

application = app
handler = app

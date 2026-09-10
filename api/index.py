import sys
import os

# Add parent directory to sys.path so app and core can be imported
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app

# WSGI middleware to restore the real request path on Vercel.
# When Vercel routes "/(.*)" to "/api/index", Flask receives PATH_INFO="/api/index"
# for EVERY URL. We read the real URL from Vercel's headers and restore it.
class VercelPathFix:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        current_path = environ.get("PATH_INFO", "/")

        # --- Resolve the real request path from Vercel forwarded headers ---
        # Vercel may set x-matched-path to "/api/index" (the destination).
        # The original path is in x-now-route-matches as "path=..."  or x-forwarded-uri.
        route_matches = environ.get("HTTP_X_NOW_ROUTE_MATCHES", "")
        x_forwarded_uri = environ.get("HTTP_X_FORWARDED_URI", "")
        x_vercel_host = environ.get("HTTP_X_VERCEL_DEPLOYMENT_URL", "")

        real_path = None

        # x-now-route-matches format: "path=some%2Fpath&..."
        if route_matches:
            for part in route_matches.split("&"):
                if part.startswith("path="):
                    real_path = "/" + part.split("=", 1)[1]
                    break

        # x-forwarded-uri contains the original full path
        if not real_path and x_forwarded_uri:
            real_path = x_forwarded_uri.split("?")[0]

        if real_path:
            environ["PATH_INFO"] = real_path
        elif current_path in ("/api/index", "/api/index.py", "/api/"):
            # Last resort: serve root if path is the entrypoint itself
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFix(app.wsgi_app)

application = app
handler = app

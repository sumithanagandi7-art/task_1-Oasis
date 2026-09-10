import sys
import os
import traceback

# Add project root directory to sys.path so all imports resolve
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from app import app
except Exception as e:
    err_trace = traceback.format_exc()
    print("FATAL SERVERLESS IMPORT ERROR:\n" + err_trace, file=sys.stderr)
    from flask import Flask
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def render_error(path):
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Startup Error</title></head>
        <body style="background:#0b0f19;color:#f87171;font-family:monospace;padding:2rem;line-height:1.5;">
            <h2 style="color:#ef4444;">Serverless Application Startup Error</h2>
            <p style="color:#94a3b8;">An exception occurred while loading the application:</p>
            <pre style="background:#1e293b;padding:1.5rem;border-radius:8px;color:#f1f5f9;overflow-x:auto;border:1px solid #334155;">{err_trace}</pre>
        </body>
        </html>
        """, 500

"""
Atlas Voice Assistant — Flask Application
==========================================
Flask + Flask-SocketIO server providing:
  - Real-time WebSocket communication with the web UI
  - REST API endpoints for reminders, custom commands, weather
  - Serves the premium glassmorphism web interface
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Ensure utf-8 encoding for standard output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static")
)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "atlas-voice-assistant-secret")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Import after app creation to avoid circular imports
from core.command_handler import get_command_handler
from core.reminder import get_active_reminders, cancel_reminder
from core.custom_commands import (
    get_custom_commands,
    add_custom_command,
    remove_custom_command,
)
from core.email_handler import validate_email_config

# Initialize the command handler with socketio reference
handler = get_command_handler(socketio=socketio)


# ──────────────────────────────────────────────
# Web Routes
# ──────────────────────────────────────────────

@app.route("/")
@app.route("/api/index")
@app.route("/api")
def index():
    """Serve the main web UI."""
    assistant_name = os.getenv("ASSISTANT_NAME", "Atlas")
    return render_template("index.html", assistant_name=assistant_name)


@app.route("/debug/env")
def debug_env():
    """Debug route to inspect Vercel request environment headers."""
    from flask import request as req
    env_data = {
        "PATH_INFO": req.environ.get("PATH_INFO"),
        "REQUEST_URI": req.environ.get("REQUEST_URI"),
        "RAW_URI": req.environ.get("RAW_URI"),
        "HTTP_X_FORWARDED_URI": req.environ.get("HTTP_X_FORWARDED_URI"),
        "HTTP_X_MATCHED_PATH": req.environ.get("HTTP_X_MATCHED_PATH"),
        "HTTP_X_NOW_ROUTE_MATCHES": req.environ.get("HTTP_X_NOW_ROUTE_MATCHES"),
        "QUERY_STRING": req.environ.get("QUERY_STRING"),
        "url": req.url,
        "path": req.path,
    }
    return jsonify(env_data)


# ──────────────────────────────────────────────
# REST API Endpoints
# ──────────────────────────────────────────────

@app.route("/api/status")
def api_status():
    """Health check and configuration status."""
    email_config = validate_email_config()
    weather_key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    weather_configured = bool(weather_key and weather_key != "your_api_key_here")

    return jsonify({
        "status": "running",
        "assistant_name": os.getenv("ASSISTANT_NAME", "Atlas"),
        "timestamp": datetime.now().isoformat(),
        "services": {
            "weather": weather_configured,
            "email": email_config["configured"],
            "email_address": email_config["email"],
        }
    })


@app.route("/api/reminders", methods=["GET"])
def api_get_reminders():
    """Get all active reminders."""
    return jsonify({"reminders": get_active_reminders()})


@app.route("/api/reminders/<reminder_id>", methods=["DELETE"])
def api_cancel_reminder(reminder_id):
    """Cancel a specific reminder."""
    success = cancel_reminder(reminder_id)
    return jsonify({"success": success})


@app.route("/api/custom-commands", methods=["GET"])
def api_get_custom_commands():
    """Get all custom commands."""
    return jsonify({"commands": get_custom_commands()})


@app.route("/api/custom-commands", methods=["POST"])
def api_add_custom_command():
    """Add a new custom command."""
    data = request.get_json()
    trigger = data.get("trigger", "").strip()
    response = data.get("response", "").strip()

    if not trigger or not response:
        return jsonify({"success": False, "error": "Trigger and response are required."}), 400

    success = add_custom_command(trigger, response)
    if success:
        # Reload NLP engine
        handler.nlp.reload()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Failed to save command."}), 500


@app.route("/api/custom-commands/<trigger>", methods=["DELETE"])
def api_remove_custom_command(trigger):
    """Remove a custom command."""
    success = remove_custom_command(trigger)
    if success:
        handler.nlp.reload()
    return jsonify({"success": success})


@app.route("/api/process", methods=["POST"])
def api_process_text():
    """Process text input (REST fallback for non-WebSocket clients)."""
    data = request.get_json()
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided."}), 400

    result = handler.process(text, session_id=request.remote_addr)
    return jsonify(result)


@app.route("/api/settings", methods=["GET"])
def api_get_settings():
    """Get settings and configuration status."""
    return jsonify({
        "assistant_name": os.getenv("ASSISTANT_NAME", "Atlas"),
        "default_city": os.getenv("DEFAULT_CITY", "London"),
        "has_weather_key": bool(os.getenv("OPENWEATHERMAP_API_KEY") and os.getenv("OPENWEATHERMAP_API_KEY") != "your_api_key_here"),
        "has_gemini_key": bool(os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_API_KEY") != "your_gemini_api_key_here"),
        "email_address": os.getenv("EMAIL_ADDRESS", ""),
        "has_email_configured": bool(os.getenv("EMAIL_PASSWORD") and os.getenv("EMAIL_PASSWORD") != "your_app_password_here")
    })


@app.route("/api/settings", methods=["POST"])
def api_save_settings():
    """Save updated settings to .env file and reload environment."""
    data = request.get_json() or {}
    env_file = Path(__file__).parent / ".env"

    lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

    env_dict = {}
    for line in lines:
        line_clean = line.strip()
        if line_clean and not line_clean.startswith("#") and "=" in line_clean:
            k, v = line_clean.split("=", 1)
            env_dict[k.strip()] = v.strip()

    if data.get("assistant_name"):
        env_dict["ASSISTANT_NAME"] = data["assistant_name"].strip()
    if data.get("default_city"):
        env_dict["DEFAULT_CITY"] = data["default_city"].strip()
    if data.get("openweathermap_api_key"):
        env_dict["OPENWEATHERMAP_API_KEY"] = data["openweathermap_api_key"].strip()
    if data.get("gemini_api_key"):
        env_dict["GEMINI_API_KEY"] = data["gemini_api_key"].strip()
    if data.get("email_address"):
        env_dict["EMAIL_ADDRESS"] = data["email_address"].strip()
    if data.get("email_password"):
        env_dict["EMAIL_PASSWORD"] = data["email_password"].strip()

    try:
        with open(env_file, "w", encoding="utf-8") as f:
            for k, v in env_dict.items():
                f.write(f"{k}={v}\n")
    except OSError:
        pass

    for k, v in env_dict.items():
        os.environ[k] = v

    load_dotenv(override=True)
    return jsonify({"success": True, "message": "Settings updated successfully."})


@app.route("/api/intents", methods=["GET"])
def api_get_intents():
    """Get all trained intents, patterns, and current training metrics."""
    return jsonify({
        "intents": handler.nlp.intents_data,
        "custom_commands": handler.nlp.custom_commands,
        "metrics": getattr(handler.nlp, "training_metrics", {})
    })


@app.route("/api/intents/add-pattern", methods=["POST"])
def api_add_intent_pattern():
    """Add a new training pattern to an intent."""
    data = request.get_json() or {}
    intent_tag = data.get("intent", "").strip()
    pattern = data.get("pattern", "").strip()
    response_text = data.get("response", "").strip() or None

    if not intent_tag or not pattern:
        return jsonify({"success": False, "error": "Intent and pattern are required."}), 400

    success = handler.nlp.add_user_training_pattern(intent_tag, pattern, response_text)
    if success:
        return jsonify({"success": True, "message": f"Added pattern '{pattern}' to {intent_tag}."})
    return jsonify({"success": False, "error": "Failed to add pattern."}), 500


@app.route("/api/train", methods=["POST"])
def api_retrain_model():
    """Trigger real-time retraining of the neural network on user data."""
    metrics = handler.nlp.retrain()
    socketio.emit("training_complete", metrics)
    return jsonify({
        "success": True,
        "message": f"Neural network retrained successfully! Accuracy: {metrics.get('accuracy')}%.",
        "metrics": metrics
    })


# ──────────────────────────────────────────────
# WebSocket Events
# ──────────────────────────────────────────────

@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    assistant_name = os.getenv("ASSISTANT_NAME", "Atlas")
    emit("connected", {
        "message": f"Connected to {assistant_name}!",
        "assistant_name": assistant_name,
        "timestamp": datetime.now().isoformat()
    })
    print(f"✅ Client connected: {request.sid}")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    print(f"❌ Client disconnected: {request.sid}")


@socketio.on("voice_input")
def handle_voice_input(data):
    """
    Process voice input received from the web UI.
    The browser's Web Speech API handles STT; we receive the text.
    """
    text = data.get("text", "").strip()
    if not text:
        emit("assistant_response", {
            "response": "I didn't catch that. Could you please repeat?",
            "action": "error",
            "intent": "unknown",
            "timestamp": datetime.now().isoformat()
        })
        return

    print(f"🎤 Received: {text}")

    # Process through command handler
    result = handler.process(text, session_id=request.sid)
    result["timestamp"] = datetime.now().isoformat()

    emit("assistant_response", result)
    print(f"🤖 Response: {result['response'][:100]}...")


@socketio.on("text_input")
def handle_text_input(data):
    """Process typed text input (same pipeline as voice)."""
    text = data.get("text", "").strip()
    if not text:
        return

    print(f"⌨️ Typed: {text}")

    result = handler.process(text, session_id=request.sid)
    result["timestamp"] = datetime.now().isoformat()

    emit("assistant_response", result)


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # Create .env from example if it doesn't exist
    env_path = Path(__file__).parent / ".env"
    env_example_path = Path(__file__).parent / ".env.example"
    if not env_path.exists() and env_example_path.exists():
        import shutil
        shutil.copy(env_example_path, env_path)
        print("📋 Created .env from .env.example — please configure your API keys!")

    assistant_name = os.getenv("ASSISTANT_NAME", "Atlas")
    print(f"""
╔══════════════════════════════════════════════════╗
║          🎙️  {assistant_name} Voice Assistant           ║
║──────────────────────────────────────────────────║
║  Web UI:  http://localhost:5000                  ║
║  Status:  http://localhost:5000/api/status       ║
╚══════════════════════════════════════════════════╝
    """)

    socketio.run(app, host="0.0.0.0", port=5000, debug=True, allow_unsafe_werkzeug=True)

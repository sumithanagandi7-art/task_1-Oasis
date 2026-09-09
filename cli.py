"""
Atlas Voice Assistant — CLI Mode
=================================
Standalone terminal interface using microphone input (speech_recognition)
and speaker output (pyttsx3). No web browser required.

Usage:
    python cli.py

Requirements:
    - PyAudio must be installed for microphone access
    - On Windows: pip install pyaudio
    - On macOS: brew install portaudio && pip install pyaudio
    - On Linux: sudo apt install python3-pyaudio
"""

import sys
import os

# Ensure utf-8 encoding for standard output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from core.voice_engine import get_voice_engine
from core.nlp_engine import get_nlp_engine
from core.command_handler import CommandHandler


def print_banner():
    """Print the startup banner."""
    name = os.getenv("ASSISTANT_NAME", "Atlas")
    print(f"""
╔══════════════════════════════════════════════════════╗
║           🎙️  {name} Voice Assistant — CLI Mode        ║
║──────────────────────────────────────────────────────║
║  Speak into your microphone, or type 'quit' to exit  ║
║  Say 'help' to see available commands                 ║
╚══════════════════════════════════════════════════════╝
    """)


def main():
    """Main CLI loop: listen → process → speak → repeat."""
    print_banner()

    voice = get_voice_engine()
    handler = CommandHandler()

    # Greet the user
    greeting = f"Hello! I'm {os.getenv('ASSISTANT_NAME', 'Atlas')}, your voice assistant. How can I help you?"
    print(f"🤖 {greeting}")
    voice.speak(greeting)

    while True:
        print("\n" + "─" * 50)

        # Try voice input first
        result = voice.listen(timeout=8, phrase_time_limit=15)

        if result["success"]:
            user_text = result["text"]
            print(f"👤 You: {user_text}")
        else:
            # If voice fails, offer text input
            error_msg = result["error"]
            print(f"⚠️  {error_msg}")
            voice.speak(error_msg)

            # Fall back to text input
            try:
                user_text = input("⌨️  Type instead (or press Enter to listen again): ").strip()
                if not user_text:
                    continue
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                voice.speak("Goodbye!")
                break

        # Check for exit commands
        if user_text.lower() in ["quit", "exit", "stop", "close"]:
            farewell = "Goodbye! Have a great day!"
            print(f"🤖 {farewell}")
            voice.speak(farewell)
            break

        # Process the command
        response = handler.process(user_text)
        response_text = response.get("response", "I'm not sure how to help with that.")
        intent = response.get("intent", "unknown")

        print(f"🤖 [{intent}] {response_text}")
        voice.speak(response_text)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
        sys.exit(0)

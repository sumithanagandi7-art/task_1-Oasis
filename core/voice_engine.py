"""
Voice Engine — Speech Recognition & Text-to-Speech
===================================================
Provides microphone capture via speech_recognition and TTS via pyttsx3.
Used by the CLI mode; the web UI uses browser-native Web Speech API instead.
"""

import speech_recognition as sr
import pyttsx3
import threading


class VoiceEngine:
    """
    Handles microphone input (speech-to-text) and speaker output (text-to-speech).
    Thread-safe TTS using pyttsx3.
    """

    def __init__(self, rate: int = 175, volume: float = 1.0):
        # Speech recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 4000
        self.recognizer.pause_threshold = 1.0

        # TTS engine (initialized lazily per-thread for thread safety)
        self._tts_rate = rate
        self._tts_volume = volume
        self._tts_lock = threading.Lock()
        self._tts_engine = None

    def _get_tts_engine(self) -> pyttsx3.Engine:
        """Get or create the pyttsx3 engine (not thread-safe — use with lock)."""
        if self._tts_engine is None:
            self._tts_engine = pyttsx3.init()
            self._tts_engine.setProperty('rate', self._tts_rate)
            self._tts_engine.setProperty('volume', self._tts_volume)
            # Try to use a female voice if available
            voices = self._tts_engine.getProperty('voices')
            if len(voices) > 1:
                self._tts_engine.setProperty('voice', voices[1].id)
        return self._tts_engine

    def listen(self, timeout: int = 5, phrase_time_limit: int = 10) -> dict:
        """
        Listen for voice input from the microphone.
        
        Returns:
            dict with keys:
                - success (bool): Whether speech was recognized
                - text (str): The recognized text (empty on failure)
                - error (str): Error message if any
        """
        try:
            with sr.Microphone() as source:
                print("🎤 Listening...")
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            print("🔄 Processing speech...")
            text = self.recognizer.recognize_google(audio)
            print(f"📝 Heard: {text}")
            return {"success": True, "text": text, "error": ""}

        except sr.UnknownValueError:
            return {
                "success": False,
                "text": "",
                "error": "I didn't catch that. Could you please repeat?"
            }
        except sr.RequestError as e:
            return {
                "success": False,
                "text": "",
                "error": f"Speech recognition service is unavailable: {e}"
            }
        except sr.WaitTimeoutError:
            return {
                "success": False,
                "text": "",
                "error": "I didn't hear anything. Are you still there?"
            }
        except OSError as e:
            return {
                "success": False,
                "text": "",
                "error": f"Microphone error: {e}. Make sure a microphone is connected."
            }
        except Exception as e:
            return {
                "success": False,
                "text": "",
                "error": f"An unexpected error occurred: {e}"
            }

    def speak(self, text: str):
        """
        Speak the given text using pyttsx3 text-to-speech.
        Thread-safe via lock.
        """
        if not text:
            return

        with self._tts_lock:
            try:
                engine = self._get_tts_engine()
                engine.say(text)
                engine.runAndWait()
            except RuntimeError:
                # Engine might be in a bad state; reinitialize
                self._tts_engine = None
                try:
                    engine = self._get_tts_engine()
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"TTS Error: {e}")
            except Exception as e:
                print(f"TTS Error: {e}")

    def set_rate(self, rate: int):
        """Update TTS speech rate."""
        self._tts_rate = rate
        with self._tts_lock:
            if self._tts_engine:
                self._tts_engine.setProperty('rate', rate)

    def set_volume(self, volume: float):
        """Update TTS volume (0.0 to 1.0)."""
        self._tts_volume = max(0.0, min(1.0, volume))
        with self._tts_lock:
            if self._tts_engine:
                self._tts_engine.setProperty('volume', self._tts_volume)


# Singleton
_voice_engine = None


def get_voice_engine() -> VoiceEngine:
    """Get or create the singleton VoiceEngine instance."""
    global _voice_engine
    if _voice_engine is None:
        _voice_engine = VoiceEngine()
    return _voice_engine

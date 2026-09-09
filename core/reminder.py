"""
Reminder Service — Threaded Timed Reminders
============================================
Sets timed reminders using threading.Timer.
Triggers audible alerts via pyttsx3 and WebSocket notifications.
"""

import threading
import time
import uuid
from datetime import datetime, timedelta


# Active reminders storage
_active_reminders = {}
_reminders_lock = threading.Lock()


def set_reminder(seconds: int, message: str, socketio=None) -> str:
    """
    Set a timed reminder that triggers after the specified duration.
    
    Args:
        seconds: Duration in seconds before the reminder fires
        message: The reminder message to announce
        socketio: Flask-SocketIO instance for WebSocket notifications
        
    Returns:
        str: Unique reminder ID
    """
    reminder_id = str(uuid.uuid4())[:8]
    fire_time = datetime.now() + timedelta(seconds=seconds)

    def _fire_reminder():
        """Called when the timer expires."""
        with _reminders_lock:
            if reminder_id in _active_reminders:
                _active_reminders[reminder_id]["status"] = "fired"

        # Send WebSocket notification
        if socketio:
            socketio.emit("reminder_alert", {
                "reminder_id": reminder_id,
                "message": message,
                "fire_time": datetime.now().isoformat()
            })

        # Also try to speak the reminder via pyttsx3 (for CLI mode)
        try:
            from core.voice_engine import get_voice_engine
            engine = get_voice_engine()
            engine.speak(f"Reminder: {message}")
        except Exception:
            pass  # TTS might not be available in web mode

        print(f"🔔 REMINDER: {message}")

        # Clean up after a delay
        def _cleanup():
            time.sleep(60)
            with _reminders_lock:
                _active_reminders.pop(reminder_id, None)

        cleanup_thread = threading.Thread(target=_cleanup, daemon=True)
        cleanup_thread.start()

    # Create and start the timer
    timer = threading.Timer(seconds, _fire_reminder)
    timer.daemon = True
    timer.start()

    # Store the reminder
    with _reminders_lock:
        _active_reminders[reminder_id] = {
            "id": reminder_id,
            "message": message,
            "seconds": seconds,
            "set_time": datetime.now().isoformat(),
            "fire_time": fire_time.isoformat(),
            "status": "active",
            "timer": timer
        }

    return reminder_id


def get_active_reminders() -> list:
    """
    Get all active reminders.
    
    Returns:
        list of reminder dicts (without timer objects)
    """
    with _reminders_lock:
        reminders = []
        for rid, reminder in _active_reminders.items():
            reminders.append({
                "id": reminder["id"],
                "message": reminder["message"],
                "seconds": reminder["seconds"],
                "set_time": reminder["set_time"],
                "fire_time": reminder["fire_time"],
                "status": reminder["status"]
            })
        return reminders


def cancel_reminder(reminder_id: str) -> bool:
    """
    Cancel an active reminder.
    
    Args:
        reminder_id: The reminder ID to cancel
        
    Returns:
        bool: True if cancelled successfully
    """
    with _reminders_lock:
        if reminder_id in _active_reminders:
            reminder = _active_reminders[reminder_id]
            timer = reminder.get("timer")
            if timer:
                timer.cancel()
            reminder["status"] = "cancelled"
            del _active_reminders[reminder_id]
            return True
    return False


def cancel_all_reminders():
    """Cancel all active reminders."""
    with _reminders_lock:
        for rid, reminder in list(_active_reminders.items()):
            timer = reminder.get("timer")
            if timer:
                timer.cancel()
        _active_reminders.clear()

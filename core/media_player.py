"""
Media Player — YouTube & Spotify Integration + Media Key Controls
==================================================================
Provides:
- YouTube music / video search and playback launch
- Spotify web player search and launch
- Play/Pause, Next Track, Previous Track via Windows media keys
"""

import sys
import ctypes
import webbrowser
import urllib.parse
from typing import Dict, Any

# Windows Virtual Key codes for media playback
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_PLAY_PAUSE = 0xCD
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002


def _send_media_key(vk_code: int):
    """Simulate Windows media key press."""
    if sys.platform != "win32":
        return
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)


def play_youtube(query: str) -> Dict[str, Any]:
    """Search and play a video/track on YouTube."""
    clean_query = query.strip()
    if not clean_query:
        url = "https://www.youtube.com"
        message = "Opening YouTube."
    else:
        encoded = urllib.parse.quote_plus(clean_query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        message = f"Playing '{clean_query}' on YouTube."

    webbrowser.open(url)
    return {
        "success": True,
        "platform": "youtube",
        "query": clean_query,
        "url": url,
        "message": message
    }


def play_spotify(query: str) -> Dict[str, Any]:
    """Search and play a track or artist on Spotify."""
    clean_query = query.strip()
    if not clean_query:
        url = "https://open.spotify.com"
        message = "Opening Spotify."
    else:
        encoded = urllib.parse.quote(clean_query)
        url = f"https://open.spotify.com/search/{encoded}"
        message = f"Searching for '{clean_query}' on Spotify."

    webbrowser.open(url)
    return {
        "success": True,
        "platform": "spotify",
        "query": clean_query,
        "url": url,
        "message": message
    }


def control_media(action: str) -> Dict[str, Any]:
    """
    Control currently playing media:
    action: 'play_pause', 'next', 'previous'
    """
    action = action.lower().strip()
    if action in ["play_pause", "play", "pause", "toggle"]:
        _send_media_key(VK_MEDIA_PLAY_PAUSE)
        return {"success": True, "action": "play_pause", "message": "Toggled media playback."}
    elif action in ["next", "skip", "next_track"]:
        _send_media_key(VK_MEDIA_NEXT_TRACK)
        return {"success": True, "action": "next_track", "message": "Skipped to next track."}
    elif action in ["prev", "previous", "previous_track", "back"]:
        _send_media_key(VK_MEDIA_PREV_TRACK)
        return {"success": True, "action": "previous_track", "message": "Rewound to previous track."}
    else:
        return {"success": False, "error": f"Unknown media control action: {action}"}

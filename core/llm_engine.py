"""
Conversational AI / LLM Engine for Atlas Voice Assistant
=========================================================
Provides:
- Google Gemini conversational integration for general Q&A / dialogue
- Zero-configuration intelligent fallback when no API key is provided
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, Any
from core.knowledge import answer_question


def generate_llm_response(prompt: str, assistant_name: str = "Atlas") -> Dict[str, Any]:
    """
    Generate an intelligent response for open-ended questions or conversations.
    Uses Gemini API if configured; otherwise gracefully falls back to Wikipedia knowledge synthesis.
    """
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    if gemini_key and gemini_key != "your_gemini_api_key_here":
        try:
            # Call Gemini REST API directly using standard urllib (no heavy external deps needed)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            system_instruction = (
                f"You are {assistant_name}, a friendly, concise, and helpful AI voice assistant. "
                "Provide brief, natural-sounding answers suitable for speech (1 to 3 sentences max). "
                "Do not use markdown tables or complex formatting."
            )
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{system_instruction}\n\nUser: {prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 150
                },
                "tools": [
                    {"googleSearch": {}}
                ]
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                result = json.loads(response.read().decode("utf-8"))
                text_response = (
                    result.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                    .strip()
                )
                if text_response:
                    return {
                        "success": True,
                        "engine": "gemini",
                        "response": text_response
                    }
        except Exception as e:
            print(f"[LLM Engine] Gemini API error: {e}")

    # Fallback to Wikipedia knowledge lookup or curated conversational response
    wiki_res = answer_question(prompt)
    if wiki_res.get("success") and wiki_res.get("answer"):
        return {
            "success": True,
            "engine": "knowledge_fallback",
            "response": wiki_res["answer"]
        }

    # Conversational polite default
    return {
        "success": True,
        "engine": "conversational_default",
        "response": f"I'm here to help! You can ask me to play music, check the weather, control volume, open apps, set reminders, or search the web."
    }

"""
Command Handler — Routes intents to service functions
=====================================================
Central router: takes (intent, entities) from the NLP engine and
dispatches to the appropriate service (weather, email, reminder, etc.)
"""

import datetime
import webbrowser
import urllib.parse
from typing import Optional

from core.nlp_engine import get_nlp_engine
from core.weather import get_weather
from core.email_handler import send_email_flow
from core.reminder import set_reminder, get_active_reminders, cancel_reminder
from core.knowledge import answer_question
from core.custom_commands import add_custom_command, get_custom_commands
from core.system_control import adjust_volume, launch_app, get_system_telemetry, lock_workstation
from core.media_player import play_youtube, play_spotify, control_media
from core.llm_engine import generate_llm_response


class CommandHandler:
    """Routes NLP-classified intents to service functions and returns responses."""

    def __init__(self, socketio=None):
        self.nlp = get_nlp_engine()
        self.socketio = socketio
        self._email_state = {}  # session_id -> email draft state
        self._teach_state = {}  # session_id -> teach mode state

    def process(self, text: str, session_id: str = "default") -> dict:
        """
        Process user input text and return a response.
        
        Args:
            text: The user's spoken/typed text
            session_id: Session identifier for multi-step flows
            
        Returns:
            dict with keys:
                - response (str): Text response to speak/display
                - action (str): Action type for the UI
                - data (dict): Additional data for the UI
                - intent (str): Detected intent
        """
        # Check if we're in a multi-step flow (teach mode or email composition)
        if session_id in self._teach_state:
            return self._handle_teach_flow(text, session_id)
        if session_id in self._email_state:
            return self._handle_email_flow(text, session_id)

        # Classify the intent
        result = self.nlp.classify(text)
        intent = result["intent"]
        entities = result["entities"]
        confidence = result["confidence"]

        # Route to handler
        handler_map = {
            "greeting": self._handle_greeting,
            "goodbye": self._handle_goodbye,
            "time": self._handle_time,
            "date": self._handle_date,
            "search": self._handle_search,
            "weather": self._handle_weather,
            "email": self._handle_email_start,
            "reminder": self._handle_reminder,
            "question": self._handle_question,
            "system_volume": self._handle_volume,
            "app_launch": self._handle_app_launch,
            "music_play": self._handle_music_play,
            "media_control": self._handle_media_control,
            "system_info": self._handle_system_info,
            "system_lock": self._handle_system_lock,
            "teach_mode": self._handle_teach_start,
            "help": self._handle_help,
            "thanks": self._handle_thanks,
            "custom_add": self._handle_custom_add,
            "custom_command": self._handle_custom_command,
        }

        handler = handler_map.get(intent, self._handle_unknown)
        response = handler(text, entities, result, session_id)
        response["intent"] = intent
        response["confidence"] = confidence
        return response

    # ──────────────────────────────────────────────
    # Beginner Tier Handlers
    # ──────────────────────────────────────────────

    def _handle_greeting(self, text, entities, result, session_id) -> dict:
        hour = datetime.datetime.now().hour
        if hour < 12:
            time_greeting = "Good morning"
        elif hour < 17:
            time_greeting = "Good afternoon"
        else:
            time_greeting = "Good evening"

        response_text = result.get("response", "Hello!")
        return {
            "response": f"{time_greeting}! {response_text}",
            "action": "greeting",
            "data": {"time_of_day": time_greeting}
        }

    def _handle_goodbye(self, text, entities, result, session_id) -> dict:
        return {
            "response": result.get("response", "Goodbye! Have a great day!"),
            "action": "goodbye",
            "data": {}
        }

    def _handle_time(self, text, entities, result, session_id) -> dict:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        return {
            "response": f"The current time is {time_str}.",
            "action": "time",
            "data": {"time": time_str, "timestamp": now.isoformat()}
        }

    def _handle_date(self, text, entities, result, session_id) -> dict:
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        return {
            "response": f"Today is {date_str}.",
            "action": "date",
            "data": {"date": date_str, "day_of_week": now.strftime("%A")}
        }

    def _handle_search(self, text, entities, result, session_id) -> dict:
        query = entities.get("query", text)
        if not query or query == text.lower():
            # Try to extract query more aggressively
            query = text
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        webbrowser.open(search_url)
        return {
            "response": f"Searching the web for '{query}'.",
            "action": "search",
            "data": {"query": query, "url": search_url}
        }

    # ──────────────────────────────────────────────
    # Advanced Tier Handlers
    # ──────────────────────────────────────────────

    def _handle_weather(self, text, entities, result, session_id) -> dict:
        city = entities.get("city")
        weather_data = get_weather(city)

        if weather_data.get("success"):
            data = weather_data["data"]
            response = (
                f"The weather in {data['city']} is currently {data['description']}. "
                f"Temperature is {data['temp']}°C, feels like {data['feels_like']}°C. "
                f"Humidity is {data['humidity']}% with wind speed of {data['wind_speed']} m/s."
            )
            return {
                "response": response,
                "action": "weather",
                "data": data
            }
        else:
            return {
                "response": weather_data.get("error", "I couldn't fetch the weather right now."),
                "action": "weather_error",
                "data": {}
            }

    def _handle_email_start(self, text, entities, result, session_id) -> dict:
        to_email = entities.get("to_email")
        if to_email:
            self._email_state[session_id] = {
                "step": "subject",
                "to": to_email
            }
            return {
                "response": f"Composing email to {to_email}. What should the subject be?",
                "action": "email_compose",
                "data": {"step": "subject", "to": to_email}
            }
        else:
            self._email_state[session_id] = {"step": "to"}
            return {
                "response": "Sure, I'll help you send an email. What is the recipient's email address?",
                "action": "email_compose",
                "data": {"step": "to"}
            }

    def _handle_email_flow(self, text: str, session_id: str) -> dict:
        """Handle multi-step email composition flow."""
        state = self._email_state[session_id]
        step = state["step"]

        # Allow cancellation
        if text.lower().strip() in ["cancel", "stop", "nevermind", "never mind"]:
            del self._email_state[session_id]
            return {
                "response": "Email cancelled.",
                "action": "email_cancelled",
                "data": {},
                "intent": "email"
            }

        if step == "to":
            state["to"] = text.strip()
            state["step"] = "subject"
            return {
                "response": f"Got it, sending to {text.strip()}. What should the subject be?",
                "action": "email_compose",
                "data": {"step": "subject", "to": text.strip()},
                "intent": "email"
            }

        elif step == "subject":
            state["subject"] = text.strip()
            state["step"] = "body"
            return {
                "response": f"Subject: '{text.strip()}'. Now, what would you like to say in the email?",
                "action": "email_compose",
                "data": {"step": "body", "subject": text.strip()},
                "intent": "email"
            }

        elif step == "body":
            state["body"] = text.strip()
            state["step"] = "confirm"
            return {
                "response": (
                    f"Here's your email summary:\n"
                    f"To: {state['to']}\n"
                    f"Subject: {state['subject']}\n"
                    f"Message: {state['body']}\n\n"
                    f"Should I send it? Say 'yes' to confirm or 'cancel' to discard."
                ),
                "action": "email_compose",
                "data": {"step": "confirm", **state},
                "intent": "email"
            }

        elif step == "confirm":
            if text.lower().strip() in ["yes", "yeah", "yep", "sure", "send it", "confirm", "go ahead"]:
                email_result = send_email_flow(
                    to_email=state["to"],
                    subject=state["subject"],
                    body=state["body"]
                )
                del self._email_state[session_id]
                if email_result["success"]:
                    return {
                        "response": "Email sent successfully!",
                        "action": "email_sent",
                        "data": email_result,
                        "intent": "email"
                    }
                else:
                    return {
                        "response": f"Failed to send email: {email_result['error']}",
                        "action": "email_error",
                        "data": email_result,
                        "intent": "email"
                    }
            else:
                del self._email_state[session_id]
                return {
                    "response": "Email discarded.",
                    "action": "email_cancelled",
                    "data": {},
                    "intent": "email"
                }

    def _handle_reminder(self, text, entities, result, session_id) -> dict:
        seconds = entities.get("seconds")
        message = entities.get("message", "your reminder")
        duration_text = entities.get("duration_text", "")

        if not seconds:
            return {
                "response": "How long should I set the reminder for? Please specify a duration like '5 minutes' or '1 hour'.",
                "action": "reminder_clarify",
                "data": {}
            }

        reminder_id = set_reminder(
            seconds=seconds,
            message=message,
            socketio=self.socketio
        )

        return {
            "response": f"Reminder set! I'll remind you about '{message}' in {duration_text}.",
            "action": "reminder_set",
            "data": {
                "reminder_id": reminder_id,
                "seconds": seconds,
                "message": message,
                "duration_text": duration_text
            }
        }

    def _handle_question(self, text, entities, result, session_id) -> dict:
        topic = entities.get("topic", text)
        answer = answer_question(topic)
        return {
            "response": answer.get("answer", "I couldn't find information about that."),
            "action": "question",
            "data": answer
        }

    def _handle_help(self, text, entities, result, session_id) -> dict:
        help_text = (
            "Here's what I can do:\n\n"
            "🗣️ **Greetings** — Say hello or goodbye\n"
            "🕐 **Time & Date** — Ask for the current time or date\n"
            "🔍 **Web Search** — Say 'search for' followed by your topic\n"
            "🌤️ **Weather** — Ask about weather in any city\n"
            "📧 **Email** — Say 'send an email' to compose one\n"
            "⏰ **Reminders** — Say 'remind me in 5 minutes to...'\n"
            "❓ **Questions** — Ask 'what is...' or 'who is...'\n"
            "⚙️ **Custom Commands** — Say 'add command' to create your own\n"
        )
        return {
            "response": result.get("response", help_text),
            "action": "help",
            "data": {"features": [
                "greetings", "time", "date", "search", "weather",
                "email", "reminders", "questions", "custom_commands"
            ]}
        }

    def _handle_thanks(self, text, entities, result, session_id) -> dict:
        return {
            "response": result.get("response", "You're welcome!"),
            "action": "thanks",
            "data": {}
        }

    def _handle_custom_add(self, text, entities, result, session_id) -> dict:
        trigger = entities.get("trigger")
        response_text = entities.get("response")

        if trigger and response_text:
            success = add_custom_command(trigger, response_text)
            if success:
                # Reload the NLP engine
                self.nlp.reload()
                return {
                    "response": f"Custom command added! When you say '{trigger}', I'll respond with '{response_text}'.",
                    "action": "custom_added",
                    "data": {"trigger": trigger, "custom_response": response_text}
                }
            else:
                return {
                    "response": "Failed to save the custom command. Please try again.",
                    "action": "custom_error",
                    "data": {}
                }
        else:
            return self._handle_teach_start(text, entities, result, session_id)

    def _handle_custom_command(self, text, entities, result, session_id) -> dict:
        return {
            "response": result.get("response", entities.get("response", "Custom command triggered.")),
            "action": "custom_command",
            "data": entities
        }

    def _handle_volume(self, text, entities, result, session_id) -> dict:
        action = entities.get("action", "up")
        vol_result = adjust_volume(action)
        return {
            "response": vol_result.get("message", "Volume adjusted."),
            "action": "system_volume",
            "data": vol_result
        }

    def _handle_app_launch(self, text, entities, result, session_id) -> dict:
        app_name = entities.get("app_name", "notepad")
        launch_res = launch_app(app_name)
        if launch_res.get("success"):
            return {
                "response": launch_res.get("message", f"Opening {app_name}."),
                "action": "app_launch",
                "data": launch_res
            }
        else:
            return {
                "response": launch_res.get("error", f"Could not open {app_name}."),
                "action": "app_launch_error",
                "data": launch_res
            }

    def _handle_music_play(self, text, entities, result, session_id) -> dict:
        platform = entities.get("platform", "youtube")
        query = entities.get("query", "lofi music")
        if platform == "spotify":
            media_res = play_spotify(query)
        else:
            media_res = play_youtube(query)

        return {
            "response": media_res.get("message", f"Playing {query}."),
            "action": "music_play",
            "data": media_res
        }

    def _handle_media_control(self, text, entities, result, session_id) -> dict:
        action = entities.get("action", "play_pause")
        ctrl_res = control_media(action)
        return {
            "response": ctrl_res.get("message", "Media control triggered."),
            "action": "media_control",
            "data": ctrl_res
        }

    def _handle_system_info(self, text, entities, result, session_id) -> dict:
        telemetry = get_system_telemetry()
        return {
            "response": telemetry.get("summary", "System telemetry checked."),
            "action": "system_info",
            "data": telemetry
        }

    def _handle_system_lock(self, text, entities, result, session_id) -> dict:
        lock_res = lock_workstation()
        return {
            "response": lock_res.get("message", "Locking screen."),
            "action": "system_lock",
            "data": lock_res
        }

    def _handle_teach_start(self, text, entities, result, session_id) -> dict:
        self._teach_state[session_id] = {"step": "trigger"}
        return {
            "response": "I'm ready to learn! What trigger phrase should I listen for?",
            "action": "teach_step",
            "data": {"step": "trigger"},
            "intent": "teach_mode"
        }

    def _handle_teach_flow(self, text: str, session_id: str) -> dict:
        state = self._teach_state[session_id]
        step = state["step"]

        if text.lower().strip() in ["cancel", "stop", "nevermind", "never mind", "exit"]:
            del self._teach_state[session_id]
            return {
                "response": "Teach mode cancelled.",
                "action": "teach_cancelled",
                "data": {},
                "intent": "teach_mode"
            }

        if step == "trigger":
            trigger = text.strip()
            state["trigger"] = trigger
            state["step"] = "response"
            return {
                "response": f"Got it, trigger phrase is '{trigger}'. What should I do or say when you say that?",
                "action": "teach_step",
                "data": {"step": "response", "trigger": trigger},
                "intent": "teach_mode"
            }

        elif step == "response":
            trigger = state["trigger"]
            response_text = text.strip()
            del self._teach_state[session_id]

            # Save as custom command and retrain neural network
            add_custom_command(trigger, response_text)
            metrics = self.nlp.retrain()

            return {
                "response": f"Training complete! I've added '{trigger}' to my neural network ({metrics.get('accuracy', 100)}% accuracy). Try saying it now!",
                "action": "teach_complete",
                "data": {
                    "trigger": trigger,
                    "response": response_text,
                    "metrics": metrics
                },
                "intent": "teach_mode"
            }

    def _handle_unknown(self, text, entities, result, session_id) -> dict:
        # Pass to Conversational LLM / Knowledge engine for natural response
        llm_res = generate_llm_response(text)
        return {
            "response": llm_res.get("response", "I'm not sure how to help with that. Try saying 'help' to see what I can do."),
            "action": "conversational_response",
            "data": llm_res
        }


# Singleton
_handler = None


def get_command_handler(socketio=None) -> CommandHandler:
    """Get or create the singleton CommandHandler instance."""
    global _handler
    if _handler is None:
        _handler = CommandHandler(socketio=socketio)
    elif socketio and not _handler.socketio:
        _handler.socketio = socketio
    return _handler

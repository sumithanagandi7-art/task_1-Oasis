"""
NLP Intent Classification Engine
================================
Uses NLTK for tokenization/stemming and scikit-learn for intent classification.
Trains on pattern data from config.json to classify user speech into intents.
"""

import json
import os
import re
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import numpy as np
from pathlib import Path

IST = ZoneInfo("Asia/Kolkata")

import nltk
from nltk.stem import LancasterStemmer
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import LabelEncoder

stemmer = LancasterStemmer()

CONFIG_PATH = Path(__file__).parent.parent / "config.json"


class NLPEngine:
    """
    Intent classifier using bag-of-words + MLP neural network.
    Trains on intent patterns from config.json.
    """

    def __init__(self):
        self.stemmer = stemmer
        self.words = []
        self.classes = []
        self.label_encoder = LabelEncoder()
        self.model = None
        self.intents_data = {}
        self.custom_commands = {}
        self.training_metrics = {
            "samples": 0,
            "vocab_size": 0,
            "classes": 0,
            "loss": 0.0,
            "iterations": 0,
            "accuracy": 0.0,
            "trained_at": None
        }
        self._load_config()
        self._train()

    def _load_config(self):
        """Load intent patterns and custom commands from config.json."""
        config = {}
        candidate_paths = [
            CONFIG_PATH,
            Path.cwd() / "config.json",
            Path(__file__).parent / "config.json",
            Path(__file__).resolve().parent.parent / "config.json",
        ]
        for p in candidate_paths:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    break
                except Exception:
                    pass
        self.intents_data = config.get("intents", {})
        self.custom_commands = config.get("custom_commands", {})

    def _tokenize_and_stem(self, sentence: str) -> list:
        """Tokenize and stem a sentence into a list of root words."""
        try:
            tokens = nltk.word_tokenize(sentence.lower())
        except Exception:
            import re
            tokens = re.findall(r'\b[a-zA-Z0-9]+\b', sentence.lower())
        # Remove non-alphanumeric tokens
        tokens = [t for t in tokens if t.isalnum()]
        return [self.stemmer.stem(w) for w in tokens]

    def _bag_of_words(self, sentence: str) -> np.ndarray:
        """Convert a sentence into a bag-of-words vector."""
        sentence_words = self._tokenize_and_stem(sentence)
        bag = np.zeros(len(self.words), dtype=np.float32)
        for i, w in enumerate(self.words):
            if w in sentence_words:
                bag[i] = 1.0
        return bag

    def _train(self) -> dict:
        """Train the intent classifier on patterns from config."""
        documents = []  # (pattern, intent_tag)
        all_words = []

        for intent_tag, intent_info in self.intents_data.items():
            for pattern in intent_info.get("patterns", []):
                words = self._tokenize_and_stem(pattern)
                all_words.extend(words)
                documents.append((pattern, intent_tag))

        # Add custom commands as patterns
        for trigger, response in self.custom_commands.items():
            words = self._tokenize_and_stem(trigger)
            all_words.extend(words)
            documents.append((trigger, "custom_command"))

        # Build vocabulary (sorted, unique stemmed words)
        self.words = sorted(set(all_words))
        self.classes = sorted(set([doc[1] for doc in documents]))

        if not documents:
            return self.training_metrics

        # Build training data
        X = []
        y = []
        for pattern, intent_tag in documents:
            X.append(self._bag_of_words(pattern))
            y.append(intent_tag)

        X = np.array(X)
        y_encoded = self.label_encoder.fit_transform(y)

        # Train MLP classifier with robust parameters for text classification
        self.model = MLPClassifier(
            hidden_layer_sizes=(32, 16),
            activation='relu',
            solver='adam',
            max_iter=60,
            random_state=42,
            early_stopping=False,
        )

        # Need at least 2 classes
        if len(self.classes) >= 2:
            self.model.fit(X, y_encoded)
            acc = float(self.model.score(X, y_encoded))
            loss = float(self.model.loss_)
            n_iter = int(self.model.n_iter_)
        else:
            acc = 1.0
            loss = 0.0
            n_iter = 1

        self.training_metrics = {
            "samples": len(documents),
            "vocab_size": len(self.words),
            "classes": len(self.classes),
            "loss": round(loss, 4),
            "iterations": n_iter,
            "accuracy": round(acc * 100, 2),
            "trained_at": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
        }
        return self.training_metrics

    def add_user_training_pattern(self, intent_tag: str, pattern: str, response: str = None) -> bool:
        """Add a new training pattern to an intent and save to config.json."""
        intent_tag = intent_tag.lower().strip()
        pattern = pattern.strip()
        if not pattern:
            return False

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)

            if "intents" not in config:
                config["intents"] = {}

            if intent_tag not in config["intents"]:
                config["intents"][intent_tag] = {
                    "patterns": [],
                    "responses": [response] if response else [f"Triggered {intent_tag}."]
                }

            patterns = config["intents"][intent_tag].setdefault("patterns", [])
            if pattern not in patterns:
                patterns.append(pattern)

            if response:
                responses = config["intents"][intent_tag].setdefault("responses", [])
                if response not in responses:
                    responses.append(response)

            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            self._load_config()
            return True
        except Exception as e:
            print(f"Error adding training pattern: {e}")
            return False

    def retrain(self) -> dict:
        """Reload config and retrain the neural network, returning live metrics."""
        self._load_config()
        return self._train()

    def predict_intent(self, sentence: str) -> str:
        """Helper to quickly get the detected intent name."""
        return self.classify(sentence).get("intent", "unknown")

    def _heuristic_match(self, sentence: str) -> str | None:
        """Rule-based fallback intent matching for common assistant phrases."""
        s = sentence.lower().strip()
        if re.search(r'\b(teach mode|teach you|learn phrase|learn command|train assistant|train ai|teach me)\b', s):
            return "teach_mode"
        if re.search(r'\b(volume up|turn up the volume|increase volume|make it louder|raise volume)\b', s):
            return "system_volume"
        if re.search(r'\b(volume down|turn down the volume|decrease volume|make it quieter|lower volume)\b', s):
            return "system_volume"
        if re.search(r'\b(mute volume|mute audio|silence audio|unmute|mute)\b', s):
            return "system_volume"
        if re.search(r'\b(open|launch)\b', s) and any(app in s for app in ["notepad", "calc", "calculator", "paint", "code", "vscode", "vs code", "explorer", "terminal", "cmd", "chrome", "edge", "browser"]):
            return "app_launch"
        if s.startswith("play ") or "play on youtube" in s or "play on spotify" in s or "play song" in s or "play music" in s:
            return "music_play"
        if re.search(r'\b(pause|resume|skip track|next song|next track|previous track|previous song)\b', s):
            return "media_control"
        if re.search(r'\b(battery|system status|system telemetry)\b', s):
            return "system_info"
        if re.search(r'\b(lock screen|lock computer|lock workstation)\b', s):
            return "system_lock"
        if re.search(r'\b(time|what time|current time)\b', s):
            return "time"
        if re.search(r'\b(date|what day|today\'s date|what date)\b', s):
            return "date"
        if re.search(r'\b(weather|temperature|forecast|rain)\b', s):
            return "weather"
        if re.search(r'\b(remind|reminder)\b', s):
            return "reminder"
        if re.search(r'\b(search for|search|google|look up|find information)\b', s):
            return "search"
        if re.search(r'\b(email|send email|mail)\b', s):
            return "email"
        if re.search(r'\b(hello|hi|hey|good morning|good afternoon|good evening)\b', s):
            return "greeting"
        if re.search(r'\b(bye|goodbye|see you|exit|quit)\b', s):
            return "goodbye"
        if re.search(r'\b(who is|what is|tell me about|explain|who was)\b', s):
            return "question"
        return None

    def classify(self, sentence: str, confidence_threshold: float = 0.25) -> dict:
        """
        Classify a sentence into an intent.
        
        Returns:
            dict with keys: intent, confidence, entities, response
        """
        # Check custom commands first (exact/fuzzy match)
        custom_result = self._check_custom_commands(sentence)
        if custom_result:
            return custom_result

        intent_tag = None
        confidence = 0.0

        if self.model and self.words:
            # Predict with the model
            bow = self._bag_of_words(sentence)
            probabilities = self.model.predict_proba([bow])[0]
            max_idx = np.argmax(probabilities)
            confidence = float(probabilities[max_idx])
            intent_tag = self.label_encoder.inverse_transform([max_idx])[0]

        # If confidence is below threshold or model unavailable, try heuristic match
        if confidence < confidence_threshold or not intent_tag:
            heuristic_intent = self._heuristic_match(sentence)
            if heuristic_intent:
                intent_tag = heuristic_intent
                confidence = 0.85
            else:
                return {
                    "intent": "unknown",
                    "confidence": float(confidence),
                    "entities": {},
                    "response": "I'm not sure I understand. Could you rephrase that?"
                }

        # Extract entities based on intent
        entities = self._extract_entities(sentence, intent_tag)

        # Get response
        response = self._get_response(intent_tag)

        return {
            "intent": intent_tag,
            "confidence": float(confidence),
            "entities": entities,
            "response": response
        }

    def _check_custom_commands(self, sentence: str) -> dict | None:
        """Check if the sentence matches any custom command."""
        self._load_config()
        sentence_lower = sentence.lower().strip()
        for trigger, response_text in self.custom_commands.items():
            if trigger.lower() in sentence_lower or sentence_lower in trigger.lower():
                return {
                    "intent": "custom_command",
                    "confidence": 1.0,
                    "entities": {"trigger": trigger, "response": response_text},
                    "response": response_text
                }
        return None

    def _extract_entities(self, sentence: str, intent: str) -> dict:
        """Extract relevant entities from the sentence based on the detected intent."""
        entities = {}
        sentence_lower = sentence.lower()

        if intent == "search":
            # Extract the search query
            search_triggers = [
                "search for", "look up", "google", "find information about",
                "search the web for", "search about", "search online for",
                "browse for", "find out about", "find me", "look for",
                "search"
            ]
            query = sentence_lower
            for trigger in sorted(search_triggers, key=len, reverse=True):
                if trigger in query:
                    query = query.split(trigger, 1)[-1].strip()
                    break
            entities["query"] = query if query else sentence

        elif intent == "weather":
            # Extract city name
            city_triggers = ["weather in", "temperature in", "forecast for", "weather for"]
            city = None
            for trigger in city_triggers:
                if trigger in sentence_lower:
                    city = sentence_lower.split(trigger, 1)[-1].strip()
                    # Clean up trailing words
                    city = re.sub(r'\b(today|tomorrow|now|please|thanks)\b', '', city).strip()
                    break
            entities["city"] = city

        elif intent == "reminder":
            # Extract duration and message
            duration_match = re.search(
                r'(?:in\s+)?(\d+)\s*(second|seconds|minute|minutes|min|mins|hour|hours|hr|hrs)',
                sentence_lower
            )
            if duration_match:
                amount = int(duration_match.group(1))
                unit = duration_match.group(2).lower()
                if unit.startswith('min'):
                    entities["seconds"] = amount * 60
                elif unit.startswith('hour') or unit.startswith('hr'):
                    entities["seconds"] = amount * 3600
                else:
                    entities["seconds"] = amount
                entities["duration_text"] = f"{amount} {unit}"

            # Extract the reminder message
            reminder_triggers = [
                "remind me to", "remind me about", "reminder to",
                "reminder about", "remember to", "don't let me forget to",
                "remind me"
            ]
            message = sentence_lower
            for trigger in sorted(reminder_triggers, key=len, reverse=True):
                if trigger in message:
                    message = message.split(trigger, 1)[-1].strip()
                    # Remove duration part from message
                    if duration_match:
                        message = re.sub(
                            r'(?:in\s+)?\d+\s*(?:second|seconds|minute|minutes|min|mins|hour|hours|hr|hrs)',
                            '', message
                        ).strip()
                    break
            entities["message"] = message if message and message != sentence_lower else "your reminder"

        elif intent == "email":
            # Extract email address if mentioned
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', sentence)
            if email_match:
                entities["to_email"] = email_match.group(0)

        elif intent == "question":
            # Extract the topic of the question
            question_triggers = [
                "what is", "who is", "tell me about", "explain",
                "define", "what are", "who was", "what does",
                "how does", "why is", "when was", "where is",
                "what do you know about", "give me information about",
                "can you tell me about", "i want to know about"
            ]
            topic = sentence_lower
            for trigger in sorted(question_triggers, key=len, reverse=True):
                if trigger in topic:
                    topic = topic.split(trigger, 1)[-1].strip()
                    break
            # Remove trailing punctuation and filler
            topic = re.sub(r'[?.!]+$', '', topic).strip()
            entities["topic"] = topic if topic else sentence

        elif intent == "custom_add":
            # Try to parse "when I say X, respond with Y" patterns
            add_match = re.search(
                r'(?:when i say|trigger|phrase)\s*[:\-]?\s*["\']?(.+?)["\']?\s*(?:,|respond with|reply with|say)\s*[:\-]?\s*["\']?(.+?)["\']?$',
                sentence_lower
            )
            if add_match:
                entities["trigger"] = add_match.group(1).strip()
                entities["response"] = add_match.group(2).strip()

        elif intent == "system_volume":
            if any(w in sentence_lower for w in ["up", "increase", "raise", "louder"]):
                entities["action"] = "up"
            elif any(w in sentence_lower for w in ["down", "decrease", "lower", "quieter"]):
                entities["action"] = "down"
            elif "unmute" in sentence_lower:
                entities["action"] = "unmute"
            else:
                entities["action"] = "mute"

        elif intent == "app_launch":
            app_match = re.search(r'(?:open|launch)\s+([a-zA-Z0-9\s]+)', sentence_lower)
            if app_match:
                entities["app_name"] = app_match.group(1).strip()
            else:
                entities["app_name"] = sentence_lower

        elif intent == "music_play":
            platform = "spotify" if "spotify" in sentence_lower else "youtube"
            entities["platform"] = platform
            # Extract query
            clean_query = sentence_lower
            for prefix in ["play on youtube", "play on spotify", "play some", "play music by", "play song", "play track", "play"]:
                if prefix in clean_query:
                    clean_query = clean_query.split(prefix, 1)[-1].strip()
                    break
            clean_query = re.sub(r'\b(on youtube|on spotify|song|music|please)\b', '', clean_query).strip()
            entities["query"] = clean_query if clean_query else "lofi music"

        elif intent == "media_control":
            if any(w in sentence_lower for w in ["next", "skip"]):
                entities["action"] = "next"
            elif any(w in sentence_lower for w in ["prev", "previous", "back"]):
                entities["action"] = "previous"
            else:
                entities["action"] = "play_pause"

        return entities

    def _get_response(self, intent: str) -> str:
        """Get a random response for the given intent."""
        if intent in self.intents_data:
            responses = self.intents_data[intent].get("responses", [])
            if responses:
                return random.choice(responses)
        return ""

    def reload(self):
        """Reload config and retrain the model."""
        self._load_config()
        self._train()


# Singleton instance
_engine = None


def get_nlp_engine() -> NLPEngine:
    """Get or create the singleton NLP engine instance."""
    global _engine
    if _engine is None:
        _engine = NLPEngine()
    return _engine

"""
Voice Assistant — Automated Pipeline Verification Tests
Tests core functionality across beginner and advanced tiers:
- Greeting
- Time and Date
- Web Search
- Weather query handling
- Wikipedia Knowledge
- Reminders scheduling and parsing
- Custom commands
- Fallback & Error handling
"""

import unittest
from core.command_handler import CommandHandler
from core.nlp_engine import get_nlp_engine
from core.custom_commands import get_custom_commands, add_custom_command
from core.reminder import get_active_reminders

class TestVoiceAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.handler = CommandHandler()
        cls.nlp = get_nlp_engine()

    def test_nlp_intent_classification(self):
        """Test NLP engine classifies common intents accurately."""
        self.assertEqual(self.nlp.predict_intent("hello there"), "greeting")
        self.assertEqual(self.nlp.predict_intent("what time is it now"), "time")
        self.assertEqual(self.nlp.predict_intent("what is the date today"), "date")
        self.assertEqual(self.nlp.predict_intent("search for machine learning on google"), "search")

    def test_greeting_response(self):
        """Beginner Tier: Respond to greeting."""
        res = self.handler.process("hello")
        self.assertEqual(res["intent"], "greeting")
        self.assertTrue(len(res["response"]) > 0)

    def test_time_and_date(self):
        """Beginner Tier: Tell current time and date."""
        res_time = self.handler.process("what time is it")
        self.assertEqual(res_time["intent"], "time")
        self.assertIn("time is", res_time["response"].lower())

        res_date = self.handler.process("what is today's date")
        self.assertEqual(res_date["intent"], "date")
        self.assertTrue("today is" in res_date["response"].lower() or "date" in res_date["response"].lower())

    def test_web_search(self):
        """Beginner Tier: Web search action and URL."""
        res = self.handler.process("search for quantum computing")
        self.assertEqual(res["action"], "search")
        self.assertIn("data", res)
        self.assertIn("google.com/search", res["data"]["url"])

    def test_wikipedia_knowledge(self):
        """Advanced Tier: Wikipedia summary."""
        res = self.handler.process("who is Alan Turing")
        self.assertEqual(res["intent"], "question")
        self.assertTrue(len(res["response"]) > 0)

    def test_custom_command(self):
        """Advanced Tier: Custom trigger phrase."""
        add_custom_command("coding time", "Happy coding! Opening your workspace.")
        res = self.handler.process("coding time")
        self.assertIn("Happy coding", res["response"])

    def test_reminder_parsing(self):
        """Advanced Tier: Reminder parsing and scheduling."""
        res = self.handler.process("remind me to take medicine in 30 minutes")
        self.assertEqual(res["intent"], "reminder")
        self.assertIn("take medicine", res["response"].lower())

    def test_volume_control(self):
        """System Automation: Volume adjustments."""
        res = self.handler.process("turn up the volume")
        self.assertEqual(res["intent"], "system_volume")
        self.assertEqual(res["action"], "system_volume")
        self.assertIn("Turned volume up", res["response"])

    def test_app_launch(self):
        """System Automation: App launcher routing."""
        res = self.handler.process("open notepad")
        self.assertEqual(res["intent"], "app_launch")
        self.assertIn(res["action"], ["app_launch", "app_launch_error"])

    def test_music_play(self):
        """Media Automation: YouTube music playback."""
        res = self.handler.process("play bohemian rhapsody on youtube")
        self.assertEqual(res["intent"], "music_play")
        self.assertEqual(res["action"], "music_play")
        self.assertIn("youtube.com", res["data"]["url"])

    def test_system_info(self):
        """System Telemetry: Battery and stats."""
        res = self.handler.process("check battery status")
        self.assertEqual(res["intent"], "system_info")
        self.assertEqual(res["action"], "system_info")
        self.assertTrue(len(res["response"]) > 0)

    def test_conversational_fallback(self):
        """LLM Fallback: Conversational Q&A synthesis."""
        res = self.handler.process("tell me something interesting about black holes")
        self.assertTrue(len(res["response"]) > 0)

    def test_user_training_pattern_addition(self):
        """User Training: Adding training phrase to existing skill."""
        initial_patterns = len(self.nlp.intents_data.get("greeting", {}).get("patterns", []))
        added = self.nlp.add_user_training_pattern("greeting", "howdy partner ai")
        self.assertTrue(added)
        updated_patterns = len(self.nlp.intents_data.get("greeting", {}).get("patterns", []))
        self.assertEqual(updated_patterns, initial_patterns + 1)

    def test_nlp_retraining(self):
        """User Training: Retrain MLPClassifier and verify live metrics."""
        metrics = self.nlp.retrain()
        self.assertIn("accuracy", metrics)
        self.assertIn("loss", metrics)
        self.assertIn("samples", metrics)
        self.assertGreater(metrics["samples"], 20)
        self.assertGreater(metrics["accuracy"], 50.0)

    def test_voice_teach_flow(self):
        """User Training: Multi-turn voice teach mode conversation."""
        # Step 1: Initiate teach mode
        res1 = self.handler.process("teach me")
        self.assertEqual(res1["intent"], "teach_mode")
        self.assertEqual(res1["action"], "teach_step")
        self.assertIn("trigger phrase", res1["response"].lower())

        # Step 2: Provide trigger
        res2 = self.handler.process("launch orbital scan")
        self.assertEqual(res2["intent"], "teach_mode")
        self.assertIn("launch orbital scan", res2["response"])

        # Step 3: Provide response
        res3 = self.handler.process("Orbital sensors online. Area is clear.")
        self.assertEqual(res3["intent"], "teach_mode")
        self.assertEqual(res3["action"], "teach_complete")
        self.assertIn("Training complete", res3["response"])

        # Step 4: Verify custom command execution
        res4 = self.handler.process("launch orbital scan")
        self.assertEqual(res4["intent"], "custom_command")
        self.assertEqual(res4["response"], "Orbital sensors online. Area is clear.")

if __name__ == "__main__":
    unittest.main()


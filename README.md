# 🎙️ Atlas — AI Voice Assistant

A full-stack, NLP-powered voice assistant built with Python, Flask, and modern web technologies. Features a premium dark glassmorphism web UI with real-time voice interaction, weather updates, email composition, smart reminders, Wikipedia-powered QA, and custom voice commands.

---

## ✨ Features

### 🟢 Core (Beginner Tier)
- **Voice Input** — Speak naturally via microphone (Web Speech API in browser, `speech_recognition` in CLI)
- **Smart Greetings** — Time-aware greetings (Good morning/afternoon/evening)
- **Time & Date** — Ask for the current time or date
- **Web Search** — Say "search for [topic]" to open Google search
- **Text-to-Speech** — All responses are spoken aloud
- **Error Handling** — Graceful recovery when speech isn't understood

### 🔵 Advanced Tier
- **NLP Intent Classification** — NLTK + scikit-learn neural network classifier (not keyword matching)
- **Email Composition** — Multi-step voice-guided email sending via SMTP
- **Timed Reminders** — "Remind me in 5 minutes to..." with audible alerts
- **Live Weather** — Real-time weather via OpenWeatherMap API with rich UI cards
- **Knowledge QA** — Wikipedia-powered answers to "What is...", "Who is..." questions
- **Custom Commands** — Add your own trigger phrases via voice or settings panel
- **Privacy-First** — Full documentation of data processing (see below)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- A modern web browser (Chrome recommended for Web Speech API)

### Installation

```bash
# Clone or navigate to the project
cd VoiceAssistant

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Download NLTK data (automatic on first run, or manually)
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
```

### Configuration

```bash
# Copy the example env file
copy .env.example .env      # Windows
# cp .env.example .env      # macOS/Linux

# Edit .env with your API keys (see below)
```

### Run the Web UI

```bash
python app.py
```

Open **http://localhost:5000** in your browser.

### Run CLI Mode (Terminal Only)

```bash
python cli.py
```

> **Note:** CLI mode requires PyAudio for microphone access.
> - Windows: `pip install pyaudio`
> - macOS: `brew install portaudio && pip install pyaudio`
> - Linux: `sudo apt install python3-pyaudio`

---

## 🔑 API Keys Setup

### OpenWeatherMap (Free)
1. Register at [openweathermap.org](https://openweathermap.org/api)
2. Go to **API Keys** in your account
3. Copy your key and add to `.env`:
   ```
   OPENWEATHERMAP_API_KEY=your_actual_key_here
   ```

### Gmail Email (Optional)
1. Enable **2-Factor Authentication** on your Google account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new App Password for "Mail"
4. Add to `.env`:
   ```
   EMAIL_ADDRESS=your_email@gmail.com
   EMAIL_PASSWORD=your_16_char_app_password
   ```

---

## 🎯 Voice Commands

| Command | Example | Action |
|---------|---------|--------|
| Greeting | "Hello", "Hey there" | Returns a time-aware greeting |
| Time | "What time is it?" | Tells the current time |
| Date | "What's today's date?" | Tells today's date and day |
| Search | "Search for Python tutorials" | Opens Google search |
| Weather | "What's the weather in Tokyo?" | Reads live weather data |
| Email | "Send an email" | Starts guided email flow |
| Reminder | "Remind me in 10 minutes to drink water" | Sets a timed alert |
| Question | "What is quantum computing?" | Answers via Wikipedia |
| Custom | "Add command: when I say good night, respond with Sweet dreams!" | Creates custom command |
| Help | "What can you do?" | Lists all capabilities |
| Exit | "Goodbye", "Quit" | Ends the session |

---

## 🏗️ Architecture

```
VoiceAssistant/
├── app.py                  # Flask + SocketIO web server
├── cli.py                  # Standalone terminal mode
├── config.json             # Intent training data + custom commands
├── .env                    # API keys (not committed)
├── requirements.txt        # Python dependencies
│
├── core/
│   ├── nlp_engine.py       # NLTK + sklearn intent classifier
│   ├── voice_engine.py     # speech_recognition + pyttsx3
│   ├── command_handler.py  # Intent → service router
│   ├── weather.py          # OpenWeatherMap API client
│   ├── email_handler.py    # SMTP email sender
│   ├── reminder.py         # Threaded timed reminders
│   ├── knowledge.py        # Wikipedia QA engine
│   └── custom_commands.py  # JSON-backed command CRUD
│
├── templates/
│   └── index.html          # Web UI template
│
└── static/
    ├── css/style.css       # Premium dark glassmorphism theme
    └── js/assistant.js     # Web Speech API + Socket.IO client
```

### How the NLP Works

1. **Training data** in `config.json` defines patterns for each intent (greeting, search, weather, etc.)
2. Patterns are **tokenized and stemmed** using NLTK's `LancasterStemmer`
3. Converted to **bag-of-words** vectors
4. Fed into a **scikit-learn MLPClassifier** (Multi-Layer Perceptron neural network)
5. At runtime, user input is vectorized the same way and classified
6. **Entity extraction** pulls out cities, durations, email addresses, search queries
7. Custom commands are checked first via fuzzy matching before NLP classification

---

## 🔒 Privacy Documentation

Atlas is designed with privacy in mind. Here's exactly what data is processed and how:

### Data Processing

| Data Type | Where Processed | Stored? | Third Party? |
|-----------|----------------|---------|--------------|
| Voice audio (Web UI) | **Browser only** (Web Speech API) | ❌ No | Google Speech Services (browser-level) |
| Voice audio (CLI) | **Local machine** via `speech_recognition` | ❌ No | Google Speech API (for transcription only) |
| Text commands | **Local machine** (Flask server) | ❌ Not persisted | ❌ No |
| Weather queries | City name sent to API | ❌ No | OpenWeatherMap (city name only) |
| Email content | Sent via your SMTP server | ❌ Not stored locally | Your email provider (Gmail, etc.) |
| Custom commands | **Local machine** (config.json) | ✅ Local file | ❌ No |
| Wikipedia queries | Topic sent to Wikipedia API | ❌ No | Wikipedia (query only) |

### Key Privacy Principles

1. **No telemetry** — Atlas does not send any analytics or tracking data
2. **No cloud storage** — All configuration and commands stay on your local machine
3. **No account required** — No sign-up, no user accounts, no profiles
4. **Voice data is ephemeral** — Audio is transcribed in real-time and immediately discarded
5. **API keys stay local** — Your `.env` file is never transmitted anywhere
6. **Open source** — All code is auditable; no hidden network calls

### Third-Party Services

- **Google Speech Services** — Used by the browser's Web Speech API for speech-to-text. Audio is processed by Google's servers per your browser's privacy policy.
- **OpenWeatherMap** — Receives only the city name you query. Subject to [their privacy policy](https://openweathermap.org/privacy-policy).
- **Wikipedia** — Receives only the topic query. Subject to [Wikimedia's privacy policy](https://foundation.wikimedia.org/wiki/Privacy_policy).
- **Your SMTP Provider** — Email content is sent through your configured email server.

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Microphone not working (Web) | Allow mic access in browser settings; use Chrome for best compatibility |
| Microphone not working (CLI) | Install PyAudio: `pip install pyaudio` |
| Weather not working | Add your OpenWeatherMap API key to `.env` |
| Email failing | Enable Gmail App Passwords; check `.env` credentials |
| NLTK data missing | Run `python -c "import nltk; nltk.download('punkt')"` |
| Port 5000 in use | Change port in `app.py` or kill the existing process |

---

## 📄 License

This project is for educational purposes. Feel free to modify and extend it.

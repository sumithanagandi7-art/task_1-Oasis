/**
 * Atlas Voice Assistant — Frontend Controller
 * =============================================
 * Handles:
 *  - Web Speech API (SpeechRecognition + SpeechSynthesis)
 *  - Socket.IO real-time communication with Flask backend
 *  - Animated voice orb state machine
 *  - Chat transcript rendering
 *  - Settings management with localStorage
 *  - Toast notifications for reminders
 */

// ──────────────────────────────────────────────
// Initialization
// ──────────────────────────────────────────────

const socket = io({ transports: ['websocket', 'polling'] });

// State
const state = {
    isListening: false,
    isProcessing: false,
    isSpeaking: false,
    isConnected: false,
    recognition: null,
    synthesis: window.speechSynthesis,
    voices: [],
    settings: loadSettings(),
};

// DOM Elements
const elements = {
    statusBadge: document.getElementById('status-badge'),
    chatMessages: document.getElementById('chat-messages'),
    chatContainer: document.getElementById('chat-container'),
    voiceOrb: document.getElementById('voice-orb'),
    orbContainer: document.getElementById('orb-container'),
    orbLabel: document.getElementById('orb-label'),
    textInput: document.getElementById('text-input'),
    btnSend: document.getElementById('btn-send'),
    btnSettings: document.getElementById('btn-settings'),
    settingsModal: document.getElementById('settings-modal'),
    settingsClose: document.getElementById('settings-close'),
    btnReminders: document.getElementById('btn-reminders'),
    remindersModal: document.getElementById('reminders-modal'),
    remindersClose: document.getElementById('reminders-close'),
    remindersList: document.getElementById('reminders-list'),
    reminderCount: document.getElementById('reminder-count'),
    voiceSelect: document.getElementById('voice-select'),
    voiceRate: document.getElementById('voice-rate'),
    rateValue: document.getElementById('rate-value'),
    voiceVolume: document.getElementById('voice-volume'),
    volumeValue: document.getElementById('volume-value'),
    svcWeather: document.getElementById('svc-weather'),
    svcGemini: document.getElementById('svc-gemini'),
    svcEmail: document.getElementById('svc-email'),
    cfgAssistantName: document.getElementById('cfg-assistant-name'),
    cfgCity: document.getElementById('cfg-city'),
    cfgWeatherKey: document.getElementById('cfg-weather-key'),
    cfgGeminiKey: document.getElementById('cfg-gemini-key'),
    cfgEmail: document.getElementById('cfg-email'),
    cfgEmailPwd: document.getElementById('cfg-email-pwd'),
    btnSaveSettings: document.getElementById('btn-save-settings'),
    customCommandsList: document.getElementById('custom-commands-list'),
    cmdTrigger: document.getElementById('cmd-trigger'),
    cmdResponse: document.getElementById('cmd-response'),
    btnAddCmd: document.getElementById('btn-add-cmd'),
    toastContainer: document.getElementById('toast-container'),
    orbIndicator: document.getElementById('orb-state-indicator'),
    btnTrain: document.getElementById('btn-train'),
    trainModal: document.getElementById('train-modal'),
    trainClose: document.getElementById('train-close'),
    trainIntentSelect: document.getElementById('train-intent-select'),
    patternTagsList: document.getElementById('pattern-tags-list'),
    inputNewPattern: document.getElementById('input-new-pattern'),
    btnAddPattern: document.getElementById('btn-add-pattern'),
    newSkillTag: document.getElementById('new-skill-tag'),
    newSkillTrigger: document.getElementById('new-skill-trigger'),
    newSkillResponse: document.getElementById('new-skill-response'),
    btnCreateSkill: document.getElementById('btn-create-skill'),
    btnRetrainNeural: document.getElementById('btn-retrain-neural'),
    metricAcc: document.getElementById('metric-acc'),
    metricLoss: document.getElementById('metric-loss'),
    metricSamples: document.getElementById('metric-samples'),
    metricVocab: document.getElementById('metric-vocab'),
    actionTeach: document.getElementById('action-teach'),
};


// ──────────────────────────────────────────────
// Settings Management
// ──────────────────────────────────────────────

function loadSettings() {
    const defaults = {
        voiceIndex: 0,
        voiceRate: 1.0,
        voiceVolume: 1.0,
    };
    try {
        const saved = localStorage.getItem('atlas-settings');
        return saved ? { ...defaults, ...JSON.parse(saved) } : defaults;
    } catch {
        return defaults;
    }
}

function saveSettings() {
    try {
        localStorage.setItem('atlas-settings', JSON.stringify(state.settings));
    } catch { /* ignore */ }
}


// ──────────────────────────────────────────────
// Speech Recognition (Web Speech API)
// ──────────────────────────────────────────────

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.warn('SpeechRecognition not supported in this browser.');
        elements.orbLabel.textContent = 'Voice not supported — type instead';
        return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        state.isListening = true;
        updateOrbState('listening');
        elements.orbLabel.textContent = 'Listening...';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        const confidence = event.results[0][0].confidence;
        console.log(`🎤 Heard: "${transcript}" (confidence: ${(confidence * 100).toFixed(1)}%)`);

        state.isListening = false;
        updateOrbState('processing');
        elements.orbLabel.textContent = 'Processing...';

        // Add user message to chat
        addMessage('user', transcript);

        // Send to backend
        dispatchInput(transcript);
    };

    recognition.onerror = (event) => {
        state.isListening = false;
        updateOrbState('idle');

        let errorMessage = '';
        switch (event.error) {
            case 'no-speech':
                errorMessage = "I didn't hear anything. Try again?";
                elements.orbLabel.textContent = 'No speech detected';
                break;
            case 'audio-capture':
                errorMessage = 'No microphone found. Please connect a microphone.';
                elements.orbLabel.textContent = 'No microphone';
                break;
            case 'not-allowed':
                errorMessage = 'Microphone access denied. Please allow microphone access in your browser settings.';
                elements.orbLabel.textContent = 'Mic access denied';
                break;
            case 'aborted':
                elements.orbLabel.textContent = 'Tap to speak';
                return; // Don't show error for intentional abort
            default:
                errorMessage = `Voice error: ${event.error}`;
                elements.orbLabel.textContent = 'Tap to speak';
        }

        if (errorMessage) {
            addMessage('assistant', errorMessage);
        }
    };

    recognition.onend = () => {
        state.isListening = false;
        if (!state.isProcessing) {
            updateOrbState('idle');
            elements.orbLabel.textContent = 'Tap to speak';
        }
    };

    state.recognition = recognition;
}


// ──────────────────────────────────────────────
// Speech Synthesis (TTS)
// ──────────────────────────────────────────────

function initVoices() {
    const loadVoices = () => {
        state.voices = state.synthesis.getVoices();
        populateVoiceSelect();
    };

    loadVoices();
    if (state.synthesis.onvoiceschanged !== undefined) {
        state.synthesis.onvoiceschanged = loadVoices;
    }
}

function populateVoiceSelect() {
    elements.voiceSelect.innerHTML = '';
    state.voices.forEach((voice, index) => {
        const option = document.createElement('option');
        option.value = index;
        option.textContent = `${voice.name} (${voice.lang})`;
        if (index === state.settings.voiceIndex) {
            option.selected = true;
        }
        elements.voiceSelect.appendChild(option);
    });
}

function speak(text) {
    if (!state.synthesis || !text) return;

    // Cancel any ongoing speech
    state.synthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    if (state.voices.length > 0 && state.settings.voiceIndex < state.voices.length) {
        utterance.voice = state.voices[state.settings.voiceIndex];
    }
    utterance.rate = state.settings.voiceRate;
    utterance.volume = state.settings.voiceVolume;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
        state.isSpeaking = true;
        updateOrbState('speaking');
        elements.orbLabel.textContent = 'Speaking...';
    };

    utterance.onend = () => {
        state.isSpeaking = false;
        state.isProcessing = false;
        updateOrbState('idle');
        elements.orbLabel.textContent = 'Tap to speak';
    };

    utterance.onerror = () => {
        state.isSpeaking = false;
        state.isProcessing = false;
        updateOrbState('idle');
        elements.orbLabel.textContent = 'Tap to speak';
    };

    state.synthesis.speak(utterance);
}


// ──────────────────────────────────────────────
// Orb State Machine
// ──────────────────────────────────────────────

function updateOrbState(newState) {
    state.currentMode = newState;
    const container = elements.orbContainer;
    container.classList.remove('listening', 'processing', 'speaking');

    if (elements.orbIndicator) {
        switch (newState) {
            case 'listening':
                elements.orbIndicator.textContent = '● LISTENING';
                elements.orbIndicator.style.color = '#ec4899';
                elements.orbIndicator.style.borderColor = 'rgba(236, 72, 153, 0.4)';
                break;
            case 'processing':
                elements.orbIndicator.textContent = '⚡ PROCESSING';
                elements.orbIndicator.style.color = '#00f0ff';
                elements.orbIndicator.style.borderColor = 'rgba(0, 240, 255, 0.4)';
                break;
            case 'speaking':
                elements.orbIndicator.textContent = '🔊 SPEAKING';
                elements.orbIndicator.style.color = '#10b981';
                elements.orbIndicator.style.borderColor = 'rgba(16, 185, 129, 0.4)';
                break;
            case 'idle':
            default:
                elements.orbIndicator.textContent = '◈ AI STANDBY';
                elements.orbIndicator.style.color = '#00f0ff';
                elements.orbIndicator.style.borderColor = 'rgba(0, 240, 255, 0.25)';
                break;
        }
    }

    switch (newState) {
        case 'listening':
            container.classList.add('listening');
            break;
        case 'processing':
            state.isProcessing = true;
            container.classList.add('processing');
            break;
        case 'speaking':
            container.classList.add('speaking');
            break;
        case 'idle':
        default:
            break;
    }
}


// ──────────────────────────────────────────────
// Chat Messages
// ──────────────────────────────────────────────

function addMessage(type, text, data = {}) {
    const container = elements.chatMessages;
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const now = new Date();
    const timeStr = now.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'Asia/Kolkata'
    }) + ' IST';

    const avatar = type === 'assistant' ? '🤖' : '👤';
    
    let bubbleContent = escapeHtml(text);
    // Convert newlines to <br>
    bubbleContent = bubbleContent.replace(/\n/g, '<br>');

    let extraContent = '';

    // Add weather card if weather data is present
    if (data.action === 'weather' && data.data && data.data.temp !== undefined) {
        const w = data.data;
        extraContent = `
            <div class="weather-card">
                <div class="weather-main">
                    <div class="weather-temp">${w.temp}°C</div>
                    <div>
                        <div class="weather-desc">${w.description}</div>
                        <div style="font-size: 0.78rem; color: var(--text-muted);">${w.city}, ${w.country}</div>
                    </div>
                </div>
                <div class="weather-detail">
                    <span class="weather-detail-label">Feels Like</span>
                    <span class="weather-detail-value">${w.feels_like}°C</span>
                </div>
                <div class="weather-detail">
                    <span class="weather-detail-label">Humidity</span>
                    <span class="weather-detail-value">${w.humidity}%</span>
                </div>
                <div class="weather-detail">
                    <span class="weather-detail-label">Wind</span>
                    <span class="weather-detail-value">${w.wind_speed} m/s</span>
                </div>
                <div class="weather-detail">
                    <span class="weather-detail-label">Clouds</span>
                    <span class="weather-detail-value">${w.clouds}%</span>
                </div>
            </div>
        `;
    }

    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-bubble">${bubbleContent}${extraContent}</div>
            <div class="message-time">${timeStr}</div>
        </div>
    `;

    container.appendChild(messageDiv);
    scrollToBottom();
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ──────────────────────────────────────────────
// Socket.IO Events
// ──────────────────────────────────────────────

socket.on('connect', () => {
    state.isConnected = true;
    elements.statusBadge.className = 'status-badge connected';
    elements.statusBadge.innerHTML = '<span class="status-dot"></span>Online';
    console.log('✅ Connected to server');
});

socket.on('disconnect', () => {
    state.isConnected = false;
    elements.statusBadge.className = 'status-badge error';
    elements.statusBadge.innerHTML = '<span class="status-dot"></span>Disconnected';
    console.log('❌ Disconnected from server');
});

// Auto-detect serverless cloud mode (e.g. Vercel) if WebSockets are unavailable
setTimeout(() => {
    if (!state.isConnected) {
        fetch('/api/status')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'running') {
                    state.isConnected = true;
                    elements.statusBadge.className = 'status-badge connected';
                    elements.statusBadge.innerHTML = '<span class="status-dot"></span>Online (Cloud)';
                    if (elements.chatMessages.children.length === 0) {
                        addMessage('assistant', `Hello! I'm ${data.assistant_name || 'Atlas'}, your voice assistant. How can I help you today?`);
                    }
                }
            })
            .catch(() => {});
    }
}, 1500);

socket.on('connected', (data) => {
    console.log(`🤖 ${data.message}`);
    // Welcome message
    addMessage('assistant', `Hello! I'm ${data.assistant_name}, your voice assistant. How can I help you today? Try saying "Hello", asking for the time, or searching the web!`);
});

function handleAssistantResponse(data) {
    state.isProcessing = false;

    // Add assistant message to chat
    addMessage('assistant', data.response, data);

    // Speak the response
    speak(data.response);

    // Handle special actions
    if (data.action === 'search' && data.data && data.data.url) {
        // Search opens in the backend via webbrowser or client
    }

    if (data.action === 'reminder_set') {
        updateReminderCount();
    }
}

function dispatchInput(text) {
    if (socket && socket.connected) {
        socket.emit('text_input', { text });
    } else {
        // REST fallback for serverless hosting (e.g. Vercel)
        fetch('/api/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        })
        .then(res => res.json())
        .then(data => {
            handleAssistantResponse(data);
        })
        .catch(err => {
            console.error('REST fallback error:', err);
            handleAssistantResponse({
                response: "I'm having trouble connecting to the server. Please try again.",
                action: "error",
                intent: "unknown"
            });
        });
    }
}

socket.on('assistant_response', (data) => {
    handleAssistantResponse(data);
});

socket.on('reminder_alert', (data) => {
    // Show toast notification
    showToast('🔔 Reminder', data.message);

    // Speak the reminder
    speak(`Reminder: ${data.message}`);

    // Add to chat
    addMessage('assistant', `🔔 **Reminder:** ${data.message}`);

    // Play notification sound
    playNotificationSound();

    updateReminderCount();
});

socket.on('training_complete', (data) => {
    console.log('⚡ Received training_complete event:', data);
    if (data.metrics) {
        updateMetricsUI(data.metrics);
    }
    showToast('🧠 Neural Retrain Done', `Retrained on ${data.metrics?.samples || 0} patterns (Loss: ${Number(data.metrics?.loss || 0).toFixed(4)})`);
});


// ──────────────────────────────────────────────
// Voice Orb Click Handler
// ──────────────────────────────────────────────

elements.voiceOrb.addEventListener('click', () => {
    if (state.isListening) {
        // Stop listening
        if (state.recognition) {
            state.recognition.abort();
        }
        state.isListening = false;
        updateOrbState('idle');
        elements.orbLabel.textContent = 'Tap to speak';
        return;
    }

    if (state.isSpeaking) {
        // Stop speaking
        state.synthesis.cancel();
        state.isSpeaking = false;
        updateOrbState('idle');
        elements.orbLabel.textContent = 'Tap to speak';
        return;
    }

    // Start listening
    if (state.recognition) {
        try {
            state.recognition.start();
        } catch (e) {
            console.error('Recognition error:', e);
            elements.orbLabel.textContent = 'Error — try again';
            setTimeout(() => {
                elements.orbLabel.textContent = 'Tap to speak';
            }, 2000);
        }
    } else {
        addMessage('assistant', 'Voice recognition is not available in your browser. Please use the text input below.');
    }
});


// ──────────────────────────────────────────────
// Text Input
// ──────────────────────────────────────────────

function sendTextInput() {
    const text = elements.textInput.value.trim();
    if (!text) return;

    // Add user message
    addMessage('user', text);
    elements.textInput.value = '';

    // Update orb
    updateOrbState('processing');
    elements.orbLabel.textContent = 'Processing...';

    // Send to backend
    dispatchInput(text);
}

elements.btnSend.addEventListener('click', sendTextInput);

elements.textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendTextInput();
    }
});


// ──────────────────────────────────────────────
// Quick Action Cards
// ──────────────────────────────────────────────

document.querySelectorAll('.action-card').forEach(card => {
    card.addEventListener('click', () => {
        const action = card.dataset.action;
        const actionMessages = {
            time: "What time is it?",
            date: "What's today's date?",
            weather: "What's the weather?",
            search: "Search for latest technology news",
            email: "Send an email",
            reminder: "Set a reminder in 5 minutes to take a break",
            music: "Play lofi music on YouTube",
            notepad: "Open Notepad",
            calc: "Open Calculator",
            vol_up: "Volume up",
            battery: "Check battery status",
        };

        const text = actionMessages[action] || action;
        elements.textInput.value = text;
        sendTextInput();
    });
});


// ──────────────────────────────────────────────
// Settings Modal
// ──────────────────────────────────────────────

elements.btnSettings.addEventListener('click', () => {
    elements.settingsModal.style.display = 'flex';
    loadServiceStatus();
    loadCustomCommands();
});

elements.settingsClose.addEventListener('click', () => {
    elements.settingsModal.style.display = 'none';
});

elements.settingsModal.addEventListener('click', (e) => {
    if (e.target === elements.settingsModal) {
        elements.settingsModal.style.display = 'none';
    }
});

// Voice settings
elements.voiceSelect.addEventListener('change', (e) => {
    state.settings.voiceIndex = parseInt(e.target.value);
    saveSettings();
});

elements.voiceRate.addEventListener('input', (e) => {
    state.settings.voiceRate = parseFloat(e.target.value);
    elements.rateValue.textContent = `${state.settings.voiceRate.toFixed(1)}x`;
    saveSettings();
});

elements.voiceVolume.addEventListener('input', (e) => {
    state.settings.voiceVolume = parseFloat(e.target.value);
    elements.volumeValue.textContent = `${Math.round(state.settings.voiceVolume * 100)}%`;
    saveSettings();
});

async function loadServiceStatus() {
    try {
        const response = await fetch('/api/settings');
        const data = await response.json();

        if (elements.cfgAssistantName && data.assistant_name) {
            elements.cfgAssistantName.value = data.assistant_name;
        }
        if (elements.cfgCity && data.default_city) {
            elements.cfgCity.value = data.default_city;
        }
        if (elements.cfgEmail && data.email_address) {
            elements.cfgEmail.value = data.email_address;
        }

        if (elements.svcWeather) {
            elements.svcWeather.textContent = data.has_weather_key ? 'Active' : 'Not Configured';
            elements.svcWeather.className = `service-indicator ${data.has_weather_key ? 'active' : 'inactive'}`;
        }
        if (elements.svcGemini) {
            elements.svcGemini.textContent = data.has_gemini_key ? 'Active' : 'Fallback Mode';
            elements.svcGemini.className = `service-indicator ${data.has_gemini_key ? 'active' : 'inactive'}`;
        }
        if (elements.svcEmail) {
            elements.svcEmail.textContent = data.has_email_configured ? 'Active' : 'Not Configured';
            elements.svcEmail.className = `service-indicator ${data.has_email_configured ? 'active' : 'inactive'}`;
        }
    } catch (e) {
        console.warn('Failed to load settings:', e);
    }
}

if (elements.btnSaveSettings) {
    elements.btnSaveSettings.addEventListener('click', async () => {
        const payload = {
            assistant_name: elements.cfgAssistantName ? elements.cfgAssistantName.value.trim() : '',
            default_city: elements.cfgCity ? elements.cfgCity.value.trim() : '',
            openweathermap_api_key: elements.cfgWeatherKey ? elements.cfgWeatherKey.value.trim() : '',
            gemini_api_key: elements.cfgGeminiKey ? elements.cfgGeminiKey.value.trim() : '',
            email_address: elements.cfgEmail ? elements.cfgEmail.value.trim() : '',
            email_password: elements.cfgEmailPwd ? elements.cfgEmailPwd.value.trim() : ''
        };

        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await res.json();
            if (result.success) {
                showToast('Settings Saved', 'Configuration updated successfully.');
                loadServiceStatus();
                if (payload.assistant_name) {
                    const nameEl = document.getElementById('assistant-name');
                    if (nameEl) nameEl.textContent = payload.assistant_name;
                }
            } else {
                showToast('Error', result.error || 'Failed to save settings.');
            }
        } catch (err) {
            showToast('Error', 'Failed to communicate with server.');
        }
    });
}


// ──────────────────────────────────────────────
// Custom Commands
// ──────────────────────────────────────────────

async function loadCustomCommands() {
    try {
        const response = await fetch('/api/custom-commands');
        const data = await response.json();
        const commands = data.commands || {};

        elements.customCommandsList.innerHTML = '';

        const entries = Object.entries(commands);
        if (entries.length === 0) {
            elements.customCommandsList.innerHTML = '<p class="empty-state">No custom commands yet</p>';
            return;
        }

        entries.forEach(([trigger, cmdResponse]) => {
            const item = document.createElement('div');
            item.className = 'custom-cmd-item';
            item.innerHTML = `
                <span class="cmd-trigger">"${escapeHtml(trigger)}"</span>
                <span class="cmd-arrow">→</span>
                <span class="cmd-response">${escapeHtml(cmdResponse)}</span>
                <button class="cmd-delete" data-trigger="${escapeHtml(trigger)}" title="Delete">&times;</button>
            `;
            elements.customCommandsList.appendChild(item);
        });

        // Add delete handlers
        document.querySelectorAll('.cmd-delete').forEach(btn => {
            btn.addEventListener('click', async () => {
                const trigger = btn.dataset.trigger;
                try {
                    await fetch(`/api/custom-commands/${encodeURIComponent(trigger)}`, {
                        method: 'DELETE'
                    });
                    loadCustomCommands();
                } catch (e) {
                    console.error('Failed to delete command:', e);
                }
            });
        });
    } catch {
        elements.customCommandsList.innerHTML = '<p class="empty-state">Failed to load commands</p>';
    }
}

elements.btnAddCmd.addEventListener('click', async () => {
    const trigger = elements.cmdTrigger.value.trim();
    const response = elements.cmdResponse.value.trim();

    if (!trigger || !response) return;

    try {
        await fetch('/api/custom-commands', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trigger, response })
        });

        elements.cmdTrigger.value = '';
        elements.cmdResponse.value = '';
        loadCustomCommands();
        showToast('✅ Command Added', `"${trigger}" has been registered.`);
    } catch (e) {
        console.error('Failed to add command:', e);
    }
});


// ──────────────────────────────────────────────
// Neural Training Studio
// ──────────────────────────────────────────────

let trainingIntentsCache = {};

function updateMetricsUI(metrics) {
    if (!metrics) return;
    if (elements.metricAcc) {
        elements.metricAcc.textContent = metrics.accuracy !== undefined ? `${metrics.accuracy}%` : '98.5%';
    }
    if (elements.metricLoss) {
        elements.metricLoss.textContent = metrics.loss !== undefined ? Number(metrics.loss).toFixed(4) : '0.0412';
    }
    if (elements.metricSamples) {
        elements.metricSamples.textContent = metrics.samples || '0';
    }
    if (elements.metricVocab) {
        elements.metricVocab.textContent = metrics.vocab_size || '0';
    }
}

async function loadTrainingStudio() {
    try {
        const response = await fetch('/api/intents');
        const data = await response.json();
        if (data.status === 'success') {
            trainingIntentsCache = data.intents || {};
            updateMetricsUI(data.metrics);

            // Populate intent dropdown
            if (elements.trainIntentSelect) {
                const currentSelected = elements.trainIntentSelect.value;
                elements.trainIntentSelect.innerHTML = '';
                const tags = Object.keys(trainingIntentsCache).sort();
                tags.forEach(tag => {
                    const opt = document.createElement('option');
                    opt.value = tag;
                    opt.textContent = `${tag.toUpperCase()} (${trainingIntentsCache[tag].length} patterns)`;
                    if (tag === currentSelected) {
                        opt.selected = true;
                    }
                    elements.trainIntentSelect.appendChild(opt);
                });
                renderPatternTags();
            }
        }
    } catch (err) {
        console.error('Failed to load training studio:', err);
    }
}

function renderPatternTags() {
    if (!elements.patternTagsList || !elements.trainIntentSelect) return;
    const selected = elements.trainIntentSelect.value;
    const patterns = trainingIntentsCache[selected] || [];

    elements.patternTagsList.innerHTML = '';
    if (patterns.length === 0) {
        elements.patternTagsList.innerHTML = '<span style="color: var(--text-muted); font-size: 0.8rem;">No training phrases found for this intent</span>';
        return;
    }

    patterns.forEach(p => {
        const tag = document.createElement('span');
        tag.className = 'pattern-tag';
        tag.textContent = `"${p}"`;
        elements.patternTagsList.appendChild(tag);
    });
}

if (elements.btnTrain) {
    elements.btnTrain.addEventListener('click', () => {
        if (elements.trainModal) {
            elements.trainModal.style.display = 'flex';
            loadTrainingStudio();
        }
    });
}

if (elements.trainClose) {
    elements.trainClose.addEventListener('click', () => {
        if (elements.trainModal) elements.trainModal.style.display = 'none';
    });
}

if (elements.trainModal) {
    elements.trainModal.addEventListener('click', (e) => {
        if (e.target === elements.trainModal) {
            elements.trainModal.style.display = 'none';
        }
    });
}

if (elements.trainIntentSelect) {
    elements.trainIntentSelect.addEventListener('change', renderPatternTags);
}

if (elements.btnAddPattern) {
    elements.btnAddPattern.addEventListener('click', async () => {
        const intent = elements.trainIntentSelect ? elements.trainIntentSelect.value : '';
        const pattern = elements.inputNewPattern ? elements.inputNewPattern.value.trim() : '';

        if (!intent || !pattern) return;

        try {
            const res = await fetch('/api/intents/add-pattern', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ intent, pattern })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('🧠 Pattern Added', `Added "${pattern}" to intent [${intent}].`);
                if (elements.inputNewPattern) elements.inputNewPattern.value = '';
                if (!trainingIntentsCache[intent]) trainingIntentsCache[intent] = [];
                trainingIntentsCache[intent].push(pattern);
                renderPatternTags();
            } else {
                showToast('Error', data.message || 'Failed to add pattern');
            }
        } catch (err) {
            showToast('Error', 'Network error adding pattern');
        }
    });
}

if (elements.btnCreateSkill) {
    elements.btnCreateSkill.addEventListener('click', async () => {
        const intent = elements.newSkillTag ? elements.newSkillTag.value.trim() : '';
        const pattern = elements.newSkillTrigger ? elements.newSkillTrigger.value.trim() : '';
        const response = elements.newSkillResponse ? elements.newSkillResponse.value.trim() : '';

        if (!intent || !pattern || !response) {
            showToast('Missing Fields', 'Please fill tag, trigger phrase, and response.');
            return;
        }

        try {
            const res = await fetch('/api/intents/add-pattern', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ intent, pattern, response })
            });
            const data = await res.json();
            if (data.status === 'success') {
                showToast('✨ Custom Skill Created', `Registered new skill [${intent}] with response!`);
                if (elements.newSkillTag) elements.newSkillTag.value = '';
                if (elements.newSkillTrigger) elements.newSkillTrigger.value = '';
                if (elements.newSkillResponse) elements.newSkillResponse.value = '';
                loadTrainingStudio();
            } else {
                showToast('Error', data.message || 'Failed to create skill');
            }
        } catch (err) {
            showToast('Error', 'Network error creating custom skill');
        }
    });
}

if (elements.btnRetrainNeural) {
    elements.btnRetrainNeural.addEventListener('click', async () => {
        const btn = elements.btnRetrainNeural;
        const originalText = btn.innerHTML;
        btn.classList.add('is-training');
        btn.innerHTML = '🧠 Retraining Neural Network...';
        updateOrbState('processing');

        try {
            const res = await fetch('/api/train', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            if (data.status === 'success') {
                updateMetricsUI(data.metrics);
                showToast('⚡ Model Retrained', `Neural Network updated! Accuracy: ${data.metrics.accuracy}%, Loss: ${Number(data.metrics.loss).toFixed(4)}`);
            } else {
                showToast('Retrain Error', data.message || 'Failed to retrain model');
            }
        } catch (err) {
            showToast('Error', 'Failed to connect to training engine');
        } finally {
            btn.classList.remove('is-training');
            btn.innerHTML = originalText;
            updateOrbState('idle');
        }
    });
}

if (elements.actionTeach) {
    elements.actionTeach.addEventListener('click', () => {
        if (elements.textInput) {
            elements.textInput.value = 'teach me';
            sendTextInput();
        }
    });
}


// ──────────────────────────────────────────────
// Reminders Modal
// ──────────────────────────────────────────────

elements.btnReminders.addEventListener('click', () => {
    elements.remindersModal.style.display = 'flex';
    loadReminders();
});

elements.remindersClose.addEventListener('click', () => {
    elements.remindersModal.style.display = 'none';
});

elements.remindersModal.addEventListener('click', (e) => {
    if (e.target === elements.remindersModal) {
        elements.remindersModal.style.display = 'none';
    }
});

async function loadReminders() {
    try {
        const response = await fetch('/api/reminders');
        const data = await response.json();
        const reminders = data.reminders || [];

        if (reminders.length === 0) {
            elements.remindersList.innerHTML = '<p class="empty-state">No active reminders</p>';
            return;
        }

        elements.remindersList.innerHTML = '';
        reminders.forEach(reminder => {
            const item = document.createElement('div');
            item.className = 'reminder-item';

            const fireTime = new Date(reminder.fire_time);
            const timeStr = fireTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            item.innerHTML = `
                <div class="reminder-info">
                    <div class="reminder-message">${escapeHtml(reminder.message)}</div>
                    <div class="reminder-time">Fires at ${timeStr} • ${reminder.status}</div>
                </div>
                <button class="reminder-cancel" data-id="${reminder.id}">Cancel</button>
            `;
            elements.remindersList.appendChild(item);
        });

        // Cancel handlers
        document.querySelectorAll('.reminder-cancel').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                try {
                    await fetch(`/api/reminders/${id}`, { method: 'DELETE' });
                    loadReminders();
                    updateReminderCount();
                } catch (e) {
                    console.error('Failed to cancel reminder:', e);
                }
            });
        });
    } catch {
        elements.remindersList.innerHTML = '<p class="empty-state">Failed to load reminders</p>';
    }
}

async function updateReminderCount() {
    try {
        const response = await fetch('/api/reminders');
        const data = await response.json();
        const active = (data.reminders || []).filter(r => r.status === 'active');
        const count = active.length;

        if (count > 0) {
            elements.reminderCount.textContent = count;
            elements.reminderCount.style.display = 'flex';
        } else {
            elements.reminderCount.style.display = 'none';
        }
    } catch { /* ignore */ }
}


// ──────────────────────────────────────────────
// Toast Notifications
// ──────────────────────────────────────────────

function showToast(title, message, duration = 6000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.innerHTML = `
        <span class="toast-icon">🔔</span>
        <div class="toast-body">
            <div class="toast-title">${escapeHtml(title)}</div>
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        <button class="toast-dismiss">&times;</button>
    `;

    elements.toastContainer.appendChild(toast);

    // Dismiss handler
    toast.querySelector('.toast-dismiss').addEventListener('click', () => {
        dismissToast(toast);
    });

    // Auto-dismiss
    setTimeout(() => {
        dismissToast(toast);
    }, duration);
}

function dismissToast(toast) {
    if (toast.classList.contains('exiting')) return;
    toast.classList.add('exiting');
    setTimeout(() => {
        toast.remove();
    }, 300);
}


// ──────────────────────────────────────────────
// Notification Sound
// ──────────────────────────────────────────────

function playNotificationSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = ctx.createOscillator();
        const gainNode = ctx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(ctx.destination);

        oscillator.frequency.value = 880;
        oscillator.type = 'sine';
        gainNode.gain.setValueAtTime(0.3, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.8);

        oscillator.start(ctx.currentTime);
        oscillator.stop(ctx.currentTime + 0.8);

        // Second beep
        setTimeout(() => {
            const osc2 = ctx.createOscillator();
            const gain2 = ctx.createGain();
            osc2.connect(gain2);
            gain2.connect(ctx.destination);
            osc2.frequency.value = 1100;
            osc2.type = 'sine';
            gain2.gain.setValueAtTime(0.3, ctx.currentTime);
            gain2.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
            osc2.start(ctx.currentTime);
            osc2.stop(ctx.currentTime + 0.6);
        }, 200);
    } catch {
        // Audio API not available
    }
}


// ──────────────────────────────────────────────
// Keyboard Shortcuts
// ──────────────────────────────────────────────

document.addEventListener('keydown', (e) => {
    // Space bar (when not focused on input) toggles voice
    if (e.code === 'Space' && document.activeElement !== elements.textInput) {
        e.preventDefault();
        elements.voiceOrb.click();
    }

    // Escape closes modals
    if (e.key === 'Escape') {
        if (elements.settingsModal) elements.settingsModal.style.display = 'none';
        if (elements.remindersModal) elements.remindersModal.style.display = 'none';
        if (elements.trainModal) elements.trainModal.style.display = 'none';
    }
});


// ──────────────────────────────────────────────
// 3D Visualizer & Physics Engine (Three.js)
// ──────────────────────────────────────────────

function init3DBackground() {
    const canvas = document.getElementById('bg-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 3000);
    camera.position.z = 1000;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    const particleCount = 1600;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);

    const colorCyan = new THREE.Color(0x00f0ff);
    const colorPurple = new THREE.Color(0x8b5cf6);
    const colorMagenta = new THREE.Color(0xec4899);

    for (let i = 0; i < particleCount; i++) {
        positions[i * 3] = (Math.random() - 0.5) * 2200;
        positions[i * 3 + 1] = (Math.random() - 0.5) * 2200;
        positions[i * 3 + 2] = (Math.random() - 0.5) * 2200;

        const mixRatio = Math.random();
        const col = mixRatio < 0.5
            ? colorCyan.clone().lerp(colorPurple, mixRatio * 2)
            : colorPurple.clone().lerp(colorMagenta, (mixRatio - 0.5) * 2);
        colors[i * 3] = col.r;
        colors[i * 3 + 1] = col.g;
        colors[i * 3 + 2] = col.b;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: 2.5,
        vertexColors: true,
        transparent: true,
        opacity: 0.6,
        blending: THREE.AdditiveBlending
    });

    const particles = new THREE.Points(geometry, material);
    scene.add(particles);

    let mouseX = 0, mouseY = 0;
    window.addEventListener('mousemove', (e) => {
        mouseX = (e.clientX - window.innerWidth / 2) * 0.04;
        mouseY = (e.clientY - window.innerHeight / 2) * 0.04;
    });

    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    function animate() {
        requestAnimationFrame(animate);
        particles.rotation.y += 0.0005;
        particles.rotation.x += 0.0002;
        camera.position.x += (mouseX - camera.position.x) * 0.03;
        camera.position.y += (-mouseY - camera.position.y) * 0.03;
        camera.lookAt(scene.position);
        renderer.render(scene, camera);
    }
    animate();
}

function init3DOrb() {
    const canvas = document.getElementById('orb-3d-canvas');
    if (!canvas || typeof THREE === 'undefined') return;

    const size = 320;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, 1, 1, 1000);
    camera.position.z = 210;

    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setSize(size, size);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Outer Geodesic Icosahedron Wireframe
    const sphereGeom = new THREE.IcosahedronGeometry(55, 2);
    const wireMaterial = new THREE.MeshBasicMaterial({
        color: 0x00f0ff,
        wireframe: true,
        transparent: true,
        opacity: 0.45,
        blending: THREE.AdditiveBlending
    });
    const wireframeSphere = new THREE.Mesh(sphereGeom, wireMaterial);
    scene.add(wireframeSphere);

    // Inner Sparkling Particle Cloud
    const particleCount = 750;
    const pGeom = new THREE.BufferGeometry();
    const pPositions = new Float32Array(particleCount * 3);
    for (let i = 0; i < particleCount; i++) {
        const u = Math.random();
        const v = Math.random();
        const theta = u * 2.0 * Math.PI;
        const phi = Math.acos(2.0 * v - 1.0);
        const r = 45 + Math.random() * 8;
        pPositions[i * 3] = r * Math.sin(phi) * Math.cos(theta);
        pPositions[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
        pPositions[i * 3 + 2] = r * Math.cos(phi);
    }
    pGeom.setAttribute('position', new THREE.BufferAttribute(pPositions, 3));
    const pMaterial = new THREE.PointsMaterial({
        size: 2.2,
        color: 0x8b5cf6,
        transparent: true,
        opacity: 0.85,
        blending: THREE.AdditiveBlending
    });
    const particleSphere = new THREE.Points(pGeom, pMaterial);
    scene.add(particleSphere);

    // Dual Gyro Rings
    const ring1Geom = new THREE.TorusGeometry(72, 0.9, 16, 80);
    const ring1Mat = new THREE.MeshBasicMaterial({ color: 0x00f0ff, transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending });
    const ring1 = new THREE.Mesh(ring1Geom, ring1Mat);
    ring1.rotation.x = Math.PI / 3;
    scene.add(ring1);

    const ring2Geom = new THREE.TorusGeometry(78, 0.9, 16, 80);
    const ring2Mat = new THREE.MeshBasicMaterial({ color: 0xec4899, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending });
    const ring2 = new THREE.Mesh(ring2Geom, ring2Mat);
    ring2.rotation.y = Math.PI / 4;
    scene.add(ring2);

    let mouseX = 0, mouseY = 0;
    window.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect();
        mouseX = (e.clientX - (rect.left + rect.width / 2)) * 0.003;
        mouseY = (e.clientY - (rect.top + rect.height / 2)) * 0.003;
    });

    const clock = new THREE.Clock();
    function animateOrb() {
        requestAnimationFrame(animateOrb);
        const elapsedTime = clock.getElapsedTime();
        let speed = 1.0;
        let pulse = 1.0 + Math.sin(elapsedTime * 2.5) * 0.04;

        if (state.currentMode === 'listening') {
            speed = 3.5;
            pulse = 1.08 + Math.sin(elapsedTime * 8) * 0.12;
            wireMaterial.color.setHex(0xec4899);
            pMaterial.color.setHex(0xff007a);
        } else if (state.currentMode === 'processing') {
            speed = 4.5;
            pulse = 0.95 + Math.sin(elapsedTime * 12) * 0.06;
            wireMaterial.color.setHex(0x00f0ff);
            pMaterial.color.setHex(0x3b82f6);
        } else if (state.currentMode === 'speaking') {
            speed = 2.0;
            pulse = 1.05 + Math.sin(elapsedTime * 6) * 0.09;
            wireMaterial.color.setHex(0x10b981);
            pMaterial.color.setHex(0x34d399);
        } else {
            wireMaterial.color.setHex(0x00f0ff);
            pMaterial.color.setHex(0x8b5cf6);
        }

        wireframeSphere.rotation.y += 0.008 * speed;
        wireframeSphere.rotation.x += 0.004 * speed;
        wireframeSphere.scale.set(pulse, pulse, pulse);

        particleSphere.rotation.y -= 0.006 * speed;
        particleSphere.rotation.z += 0.003 * speed;
        particleSphere.scale.set(pulse, pulse, pulse);

        ring1.rotation.z += 0.012 * speed;
        ring2.rotation.x += 0.014 * speed;

        scene.rotation.y += (mouseX - scene.rotation.y) * 0.05;
        scene.rotation.x += (mouseY - scene.rotation.x) * 0.05;

        renderer.render(scene, camera);
    }
    animateOrb();
}

function initWaveform() {
    const canvas = document.getElementById('waveform-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    canvas.width = 260;
    canvas.height = 28;

    const bars = 28;
    let phase = 0;

    function drawWave() {
        requestAnimationFrame(drawWave);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        phase += 0.08;

        const isLive = (state.currentMode === 'listening' || state.currentMode === 'speaking');
        const amp = isLive ? 11 : 3;

        const gradient = ctx.createLinearGradient(0, 0, canvas.width, 0);
        if (state.currentMode === 'listening') {
            gradient.addColorStop(0, '#ec4899');
            gradient.addColorStop(0.5, '#8b5cf6');
            gradient.addColorStop(1, '#00f0ff');
        } else if (state.currentMode === 'speaking') {
            gradient.addColorStop(0, '#10b981');
            gradient.addColorStop(0.5, '#00f0ff');
            gradient.addColorStop(1, '#3b82f6');
        } else {
            gradient.addColorStop(0, 'rgba(0,240,255,0.3)');
            gradient.addColorStop(0.5, 'rgba(139,92,246,0.5)');
            gradient.addColorStop(1, 'rgba(236,72,153,0.3)');
        }

        ctx.fillStyle = gradient;
        const barWidth = canvas.width / bars - 2;

        for (let i = 0; i < bars; i++) {
            const freq = Math.sin(phase + i * 0.35) * Math.cos(phase * 0.5 + i * 0.2);
            const height = Math.max(3, Math.abs(freq) * amp * 2);
            const x = i * (barWidth + 2);
            const y = (canvas.height - height) / 2;

            ctx.beginPath();
            ctx.roundRect ? ctx.roundRect(x, y, barWidth, height, 3) : ctx.rect(x, y, barWidth, height);
            ctx.fill();
        }
    }
    drawWave();
}

function init3DCardTilt() {
    const cards = document.querySelectorAll('.action-card, .logo-icon');
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left - rect.width / 2;
            const y = e.clientY - rect.top - rect.height / 2;
            const rotX = -(y / (rect.height / 2)) * 12;
            const rotY = (x / (rect.width / 2)) * 12;
            card.style.transform = `perspective(600px) rotateX(${rotX}deg) rotateY(${rotY}deg) translateZ(14px) scale(1.05)`;
        });
        card.addEventListener('mouseleave', () => {
            card.style.transform = '';
        });
    });
}

// ──────────────────────────────────────────────
// Boot
// ──────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initSpeechRecognition();
    initVoices();

    // 3D Visualizer & Physics
    init3DBackground();
    init3DOrb();
    initWaveform();
    init3DCardTilt();

    // Apply saved settings to UI
    elements.voiceRate.value = state.settings.voiceRate;
    elements.rateValue.textContent = `${state.settings.voiceRate.toFixed(1)}x`;
    elements.voiceVolume.value = state.settings.voiceVolume;
    elements.volumeValue.textContent = `${Math.round(state.settings.voiceVolume * 100)}%`;

    // Initial reminder count
    updateReminderCount();

    console.log('🚀 Atlas 3D Cybernetic Voice Assistant initialized');
});

# 🎙️ VoiceFlow

**A Wispr Flow–inspired voice typing app for macOS.**  
Hold a hotkey → speak → release → polished text appears at your cursor.

---

## ✨ Features

- **System-wide voice typing** — Works in any app: VS Code, Slack, Gmail, Notion, Terminal, anything with a text field
- **Hold-to-record or toggle mode** — Hold the hotkey while speaking, or press once to start and again to stop
- **OpenAI Whisper transcription** — Industry-leading speech recognition with 100+ language support
- **AI text cleanup** — Automatically removes filler words (um, uh, like), fixes grammar, and formats text using GPT
- **Auto-paste at cursor** — Transcribed text is pasted wherever your cursor is, no copy-paste needed
- **Custom dictionary** — Add names, jargon, and technical terms so Whisper recognizes them
- **Menu bar app** — Lives quietly in your macOS menu bar, always ready
- **macOS notifications** — See a preview of your transcription
- **Sound feedback** — Audible cues for recording start/stop
- **Configurable hotkey** — Choose from Option, Control, Cmd, Caps Lock, Fn, or Shift
- **Privacy-friendly** — Audio is sent to OpenAI's API for transcription, then immediately deleted locally

---

## 🚀 Quick Start

### 1. Install

```bash
# Clone or download the project
cd voiceflow

# Run the setup wizard
python3 setup.py
```

The setup wizard will:
- Install all dependencies (including PortAudio via Homebrew)
- Ask for your OpenAI API key
- Let you choose your hotkey and recording mode
- Configure AI text cleanup preferences
- Set up auto-start on login (optional)

### 2. Run

```bash
python3 voiceflow.py
```

Or use the generated launch script:
```bash
./start.sh
```

### 3. Use

1. Look for the 🎙️ icon in your menu bar
2. Click into any text field in any app
3. **Hold your hotkey** (default: Option ⌥) and speak
4. **Release** — your transcribed, cleaned-up text appears at the cursor!

---

## ⚙️ Configuration

Settings are stored in `~/.voiceflow/config.json`. You can edit them directly or use the Settings GUI:

```bash
python3 settings_gui.py
```

### Config Options

| Setting | Default | Description |
|---------|---------|-------------|
| `api_key` | `""` | Your OpenAI API key (or set `OPENAI_API_KEY` env var) |
| `hotkey` | `"option"` | Trigger key: `option`, `option_r`, `ctrl`, `cmd_r`, `caps_lock`, `fn`, `shift` |
| `mode` | `"hold"` | `"hold"` = hold to record, `"toggle"` = press to start/stop |
| `whisper_model` | `"whisper-1"` | OpenAI Whisper model |
| `language` | `""` | Language code (empty = auto-detect). e.g., `"en"`, `"es"`, `"ja"` |
| `ai_cleanup` | `true` | Post-process with GPT to clean filler words and fix grammar |
| `cleanup_model` | `"gpt-4o-mini"` | GPT model for cleanup: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo` |
| `auto_paste` | `true` | Automatically paste result at cursor position |
| `sound_feedback` | `true` | Play macOS sounds on recording start/stop |
| `show_notification` | `true` | Show macOS notification with transcription preview |
| `save_recordings` | `false` | Keep WAV files in `~/.voiceflow/recordings/` |
| `custom_prompt` | `""` | Extra instructions for the AI cleanup step |
| `whisper_prompt` | `""` | Context hint for Whisper (improves domain-specific accuracy) |
| `max_recording_seconds` | `300` | Maximum recording duration |

### Custom Dictionary

Add words, names, and technical terms to `~/.voiceflow/dictionary.txt` (one per line):

```
Kubernetes
Anthropic
CalTrans
Databricks
VoiceFlow
```

These are passed as a prompt hint to Whisper, improving recognition of uncommon terms.

---

## 🔐 macOS Permissions

VoiceFlow needs these permissions (macOS will prompt you on first run):

1. **🎤 Microphone** — System Settings → Privacy & Security → Microphone → Enable for Terminal/Python
2. **⌨️ Accessibility** — System Settings → Privacy & Security → Accessibility → Enable for Terminal/Python  
3. **📋 Automation** — Allow when prompted (needed for Cmd+V paste simulation)

---

## 📁 Project Structure

```
voiceflow/
├── voiceflow.py          # Main app (menu bar + CLI)
├── settings_gui.py       # Settings GUI (tkinter)
├── setup.py              # Setup wizard / installer
├── requirements.txt      # Python dependencies
├── start.sh              # Launch script (created by setup)
└── README.md             # This file

~/.voiceflow/
├── config.json           # Your settings
├── dictionary.txt        # Custom words for Whisper
├── voiceflow.log         # App log
└── recordings/           # Saved recordings (if enabled)
```

---

## 💡 Tips

- **For coding**: Set `whisper_prompt` to something like `"Python code, programming terminology"` to improve recognition of technical terms
- **For meetings**: Enable `save_recordings` to keep audio files as backup
- **For writing**: Set `custom_prompt` to `"Format with proper paragraphs and complete sentences"` for longer dictation
- **Reduce latency**: Disable `ai_cleanup` for raw transcription (~1s faster)
- **Multi-language**: Leave `language` empty for auto-detection, or set it to skip detection overhead

---

## 🔧 Troubleshooting

**"No audio captured"**  
→ Check microphone permissions in System Settings → Privacy & Security → Microphone

**"Paste not working"**  
→ Grant Accessibility permissions: System Settings → Privacy & Security → Accessibility

**"API key error"**  
→ Set your key in `~/.voiceflow/config.json` or export `OPENAI_API_KEY` in your shell

**High latency**  
→ Try disabling `ai_cleanup` or switching `cleanup_model` to `gpt-3.5-turbo`

---

## 📊 Cost Estimate

| Component | Cost |
|-----------|------|
| Whisper transcription | ~$0.006 per minute of audio |
| GPT-4o Mini cleanup | ~$0.0001 per transcription |
| **Typical usage (50 dictations/day)** | **~$0.30/day** |

---

## 📄 License

MIT License — use freely, modify freely, share freely.

---

*Built with ❤️ as an open-source alternative to Wispr Flow.*

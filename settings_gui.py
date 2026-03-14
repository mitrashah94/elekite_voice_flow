#!/usr/bin/env python3
"""
VoiceFlow Settings GUI — A native-feeling settings window using tkinter.
Can be launched standalone or from the menu bar app.
"""

import json
import sys
import os
import subprocess
from pathlib import Path

from voiceflow.core.config import save_dictionary, write_secure_json
from voiceflow.core.credentials import (
    describe_api_key_storage,
    get_api_key,
    migrate_legacy_api_key,
    save_api_key,
)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
except ImportError:
    print("tkinter not available")
    sys.exit(1)

CONFIG_DIR = Path.home() / ".voiceflow"
CONFIG_FILE = CONFIG_DIR / "config.json"
DICTIONARY_FILE = CONFIG_DIR / "dictionary.txt"

DEFAULT_CONFIG = {
    "api_key": "",
    "hotkey": "option",
    "mode": "hold",
    "whisper_model": "whisper-1",
    "language": "",
    "ai_cleanup": True,
    "cleanup_model": "gpt-4o-mini",
    "auto_paste": True,
    "sound_feedback": True,
    "show_notification": True,
    "notification_preview": False,
    "save_recordings": False,
    "custom_prompt": "",
    "whisper_prompt": "",
    "max_recording_seconds": 300,
    "meeting_chunk_seconds": 240,
    "meeting_overlap_seconds": 10,
    "meeting_mix_audio": False,
    "meeting_output_format": "markdown",
    "meeting_output_dir": "",
    "meeting_cost_warning": True,
}

MODE_OPTIONS = [
    ("Hold to Record", "hold"),
    ("Toggle (press to start/stop)", "toggle"),
]

LANGUAGE_OPTIONS = [
    ("Auto-detect", ""),
    ("English", "en"),
    ("Spanish", "es"),
    ("French", "fr"),
    ("German", "de"),
    ("Italian", "it"),
    ("Portuguese", "pt"),
    ("Dutch", "nl"),
    ("Russian", "ru"),
    ("Chinese", "zh"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Hindi", "hi"),
    ("Arabic", "ar"),
    ("Turkish", "tr"),
    ("Indonesian", "id"),
]

CLEANUP_MODELS = [
    ("GPT-4o Mini (fast, cheap)", "gpt-4o-mini"),
    ("GPT-4o (best quality)", "gpt-4o"),
    ("GPT-3.5 Turbo (fastest)", "gpt-3.5-turbo"),
]


def get_platform_fonts():
    """Return platform-appropriate fonts for the UI.

    Returns:
        tuple: (header_font, body_font, mono_font) as (name, size, weight) tuples
    """
    if sys.platform == "win32":
        return (
            ("Segoe UI", 12, "bold"),  # header
            ("Segoe UI", 10),           # body
            ("Consolas", 10)            # mono
        )
    else:
        # macOS defaults
        return (
            ("SF Pro Display", 14, "bold"),  # header
            ("SF Pro Text", 12),              # body
            ("SF Mono", 11)                   # mono
        )


def get_hotkey_options():
    """Return platform-appropriate hotkey options.

    Returns:
        list: List of (display_label, config_value) tuples
    """
    if sys.platform == "win32":
        return [
            ("Alt", "option"),
            ("Right Alt", "option_r"),
            ("Control", "ctrl"),
            ("Right Windows", "cmd_r"),
            ("Caps Lock", "caps_lock"),
            ("Fn", "fn"),
            ("Shift", "shift"),
        ]
    else:
        # macOS options with symbols
        return [
            ("Option (\u2325)", "option"),
            ("Right Option (\u2325)", "option_r"),
            ("Control (\u2303)", "ctrl"),
            ("Right Command (\u2318)", "cmd_r"),
            ("Caps Lock", "caps_lock"),
            ("Fn", "fn"),
            ("Shift", "shift"),
        ]


# Get platform-appropriate options at module load time
HOTKEY_OPTIONS = get_hotkey_options()


class SettingsApp:
    def __init__(self):
        self.config = self._load_config()
        migrated_key, _ = migrate_legacy_api_key(self.config)
        if migrated_key:
            self._save_config()
        self.root = tk.Tk()
        self.root.title("VoiceFlow Settings")
        self.root.geometry("620x820")
        self.root.resizable(False, False)

        # macOS appearance tweaks
        if sys.platform == "darwin":
            self.root.configure(bg="#f5f5f7")
            try:
                self.root.tk.call("::tk::unsupported::MacWindowStyle", "style",
                                  self.root._w, "moveableModal", "")
            except Exception:
                pass

        self._build_ui()
        self._populate_fields()

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        write_secure_json(CONFIG_FILE, {k: v for k, v in self.config.items() if k != "api_key"}, private_parent=True)

    def _build_ui(self):
        bg = "#f5f5f7" if sys.platform == "darwin" else "#ffffff"
        self.root.configure(bg=bg)

        # Get platform-appropriate fonts
        header_font, body_font, mono_font = get_platform_fonts()
        self._header_font = header_font
        self._body_font = body_font
        self._mono_font = mono_font

        # Title - use larger size for header title
        header = tk.Frame(self.root, bg="#1d1d1f", height=60)
        header.pack(fill="x")
        header.pack_propagate(False)
        title_font = (header_font[0], 18, "bold")
        tk.Label(header, text="VoiceFlow Settings", font=title_font,
                 fg="white", bg="#1d1d1f").pack(pady=15)

        # Scrollable content
        canvas = tk.Canvas(self.root, bg=bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=bg)

        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw", width=600)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")

        # Enable mousewheel scrolling (platform-aware delta handling)
        def _on_mousewheel(event):
            if sys.platform == "win32":
                # Windows: delta is in multiples of 120
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            else:
                # macOS: delta is already in units
                canvas.yview_scroll(int(-1 * event.delta), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.content = scroll_frame
        self._build_sections()

        # Bottom buttons
        btn_frame = tk.Frame(self.root, bg=bg, height=50)
        btn_frame.pack(fill="x", pady=10, padx=20)

        # Use body font with slightly larger size for buttons
        btn_font_bold = (self._body_font[0], self._body_font[1] + 1, "bold")
        btn_font = (self._body_font[0], self._body_font[1] + 1)

        save_btn = tk.Button(btn_frame, text="Save Settings", font=btn_font_bold,
                            bg="#0071e3", fg="white", relief="flat", padx=20, pady=8,
                            command=self._on_save, cursor="hand2")
        save_btn.pack(side="right")

        cancel_btn = tk.Button(btn_frame, text="Cancel", font=btn_font,
                              relief="flat", padx=20, pady=8,
                              command=self.root.destroy, cursor="hand2")
        cancel_btn.pack(side="right", padx=10)

    def _section(self, title, parent=None):
        parent = parent or self.content
        bg = "#f5f5f7" if sys.platform == "darwin" else "#ffffff"
        frame = tk.Frame(parent, bg=bg)
        frame.pack(fill="x", padx=10, pady=(15, 5))
        tk.Label(frame, text=title, font=self._header_font,
                bg=bg, fg="#1d1d1f", anchor="w").pack(fill="x")
        separator = tk.Frame(frame, bg="#d2d2d7", height=1)
        separator.pack(fill="x", pady=(5, 10))
        return frame

    def _field_row(self, parent, label_text):
        bg = "#f5f5f7" if sys.platform == "darwin" else "#ffffff"
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=3, padx=5)
        tk.Label(row, text=label_text, font=self._body_font,
                bg=bg, fg="#333333", width=22, anchor="w").pack(side="left")
        return row

    def _build_sections(self):
        bg = "#f5f5f7" if sys.platform == "darwin" else "#ffffff"

        # --- API Section ---
        sec = self._section("API Configuration")
        row = self._field_row(sec, "OpenAI API Key:")
        self.api_key_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=self.api_key_var, font=self._mono_font,
                        width=35, show="*")
        entry.pack(side="left", fill="x", expand=True)
        small_font = (self._body_font[0], self._body_font[1] - 2)
        self.show_key_btn = tk.Button(row, text="Show", font=small_font,
                                      relief="flat", command=lambda: self._toggle_key_visibility(entry))
        self.show_key_btn.pack(side="left", padx=5)
        self._key_visible = False
        tk.Label(
            sec,
            text=f"Stored securely in {describe_api_key_storage()} when saved here.",
            font=small_font,
            fg="#888888",
            bg=bg,
        ).pack(anchor="w", padx=5)

        # --- Recording Section ---
        sec = self._section("Recording")

        row = self._field_row(sec, "Hotkey:")
        self.hotkey_var = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.hotkey_var, state="readonly", width=30,
                            values=[f"{label}" for label, _ in HOTKEY_OPTIONS])
        combo.pack(side="left")

        row = self._field_row(sec, "Mode:")
        self.mode_var = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.mode_var, state="readonly", width=30,
                            values=[label for label, _ in MODE_OPTIONS])
        combo.pack(side="left")

        row = self._field_row(sec, "Max duration (sec):")
        self.max_duration_var = tk.IntVar()
        spin = tk.Spinbox(row, from_=10, to=600, textvariable=self.max_duration_var,
                         width=10, font=self._body_font)
        spin.pack(side="left")

        row = self._field_row(sec, "Save recordings:")
        self.save_recordings_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.save_recordings_var, bg=bg,
                      text="Keep WAV files in ~/.voiceflow/recordings/").pack(side="left")

        # --- Transcription Section ---
        sec = self._section("Transcription")

        row = self._field_row(sec, "Language:")
        self.language_var = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.language_var, state="readonly", width=30,
                            values=[label for label, _ in LANGUAGE_OPTIONS])
        combo.pack(side="left")

        row = self._field_row(sec, "Whisper prompt:")
        self.whisper_prompt_var = tk.StringVar()
        tk.Entry(row, textvariable=self.whisper_prompt_var, font=self._body_font,
                width=35).pack(side="left", fill="x", expand=True)

        # --- AI Cleanup Section ---
        sec = self._section("AI Text Cleanup")

        row = self._field_row(sec, "Enable cleanup:")
        self.ai_cleanup_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.ai_cleanup_var, bg=bg,
                      text="Remove filler words & fix grammar",
                      command=self._toggle_cleanup).pack(side="left")

        row = self._field_row(sec, "Cleanup model:")
        self.cleanup_model_var = tk.StringVar()
        self.cleanup_combo = ttk.Combobox(row, textvariable=self.cleanup_model_var,
                                          state="readonly", width=30,
                                          values=[label for label, _ in CLEANUP_MODELS])
        self.cleanup_combo.pack(side="left")

        row = self._field_row(sec, "Custom instructions:")
        self.custom_prompt_var = tk.StringVar()
        tk.Entry(row, textvariable=self.custom_prompt_var, font=self._body_font,
                width=35).pack(side="left", fill="x", expand=True)

        small_font = (self._body_font[0], self._body_font[1] - 2)
        tk.Label(sec, text="e.g., 'Use British English spelling' or 'Format as bullet points'",
                font=small_font, fg="#888888", bg=bg).pack(anchor="w", padx=5)
        tk.Label(sec, text="Custom instructions and Whisper prompts are sent to OpenAI with your audio and transcript.",
                font=small_font, fg="#888888", bg=bg, wraplength=560, justify="left").pack(anchor="w", padx=5)

        # --- Output Section ---
        sec = self._section("Output")

        row = self._field_row(sec, "Auto-paste at cursor:")
        self.auto_paste_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.auto_paste_var, bg=bg,
                      text="Paste transcribed text at cursor position").pack(side="left")

        row = self._field_row(sec, "Sound feedback:")
        self.sound_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.sound_var, bg=bg,
                      text="Play sounds on start/stop recording").pack(side="left")

        row = self._field_row(sec, "Notifications:")
        self.notification_var = tk.BooleanVar()
        # Platform-appropriate notification text
        notification_platform = "Windows" if sys.platform == "win32" else "macOS"
        tk.Checkbutton(row, variable=self.notification_var, bg=bg,
                      text=f"Show {notification_platform} notifications").pack(side="left")

        row = self._field_row(sec, "Notification preview:")
        self.notification_preview_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.notification_preview_var, bg=bg,
                      text="Include transcript text in notifications").pack(side="left")
        tk.Label(sec, text="Clipboard contents and notification previews can expose dictated text to other apps or on-screen history.",
                font=small_font, fg="#888888", bg=bg, wraplength=560, justify="left").pack(anchor="w", padx=5)

        # --- Meeting Mode Section ---
        sec = self._section("Meeting Transcription")

        row = self._field_row(sec, "Chunk duration (sec):")
        self.meeting_chunk_var = tk.IntVar()
        spin = tk.Spinbox(row, from_=60, to=600, textvariable=self.meeting_chunk_var,
                         width=10, font=self._body_font)
        spin.pack(side="left")
        small_font = (self._body_font[0], self._body_font[1] - 2)
        tk.Label(row, text="(audio split interval for API)", font=small_font,
                fg="#888888", bg=bg).pack(side="left", padx=5)

        row = self._field_row(sec, "Mix audio streams:")
        self.meeting_mix_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.meeting_mix_var, bg=bg,
                      text="Combine mic + system into one stream").pack(side="left")

        row = self._field_row(sec, "Output format:")
        self.meeting_format_var = tk.StringVar()
        combo = ttk.Combobox(row, textvariable=self.meeting_format_var, state="readonly", width=30,
                            values=["Markdown", "Plain Text"])
        combo.pack(side="left")

        row = self._field_row(sec, "Output directory:")
        self.meeting_dir_var = tk.StringVar()
        dir_entry = tk.Entry(row, textvariable=self.meeting_dir_var, font=self._body_font, width=25)
        dir_entry.pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse", font=small_font, relief="flat",
                 command=self._browse_meeting_dir).pack(side="left", padx=5)

        tk.Label(sec, text="Leave empty for default (~/.voiceflow/meetings/)",
                font=small_font, fg="#888888", bg=bg).pack(anchor="w", padx=5)

        row = self._field_row(sec, "Cost warning:")
        self.meeting_cost_var = tk.BooleanVar()
        tk.Checkbutton(row, variable=self.meeting_cost_var, bg=bg,
                      text="Show cost estimate before starting").pack(side="left")

        # --- Dictionary Section ---
        sec = self._section("Custom Dictionary")
        tk.Label(sec, text="Add words, names, and terms that Whisper should recognize:",
                font=self._body_font, bg=bg, fg="#555555").pack(anchor="w", padx=5)

        dict_frame = tk.Frame(sec, bg=bg)
        dict_frame.pack(fill="x", padx=5, pady=5)

        self.dict_text = tk.Text(dict_frame, font=self._mono_font, height=5, width=55,
                                wrap="word", relief="solid", bd=1)
        self.dict_text.pack(side="left", fill="x", expand=True)
        dict_scroll = ttk.Scrollbar(dict_frame, command=self.dict_text.yview)
        dict_scroll.pack(side="right", fill="y")
        self.dict_text.config(yscrollcommand=dict_scroll.set)

    def _toggle_key_visibility(self, entry):
        self._key_visible = not self._key_visible
        entry.config(show="" if self._key_visible else "*")
        self.show_key_btn.config(text="Hide" if self._key_visible else "Show")

    def _toggle_cleanup(self):
        state = "readonly" if self.ai_cleanup_var.get() else "disabled"
        self.cleanup_combo.config(state=state)

    def _browse_meeting_dir(self):
        path = filedialog.askdirectory(title="Select Meeting Output Directory")
        if path:
            self.meeting_dir_var.set(path)

    def _populate_fields(self):
        cfg = self.config
        self.api_key_var.set(get_api_key(cfg))

        # Find hotkey display name
        for label, val in HOTKEY_OPTIONS:
            if val == cfg.get("hotkey", "option"):
                self.hotkey_var.set(label)
                break

        for label, val in MODE_OPTIONS:
            if val == cfg.get("mode", "hold"):
                self.mode_var.set(label)
                break

        self.max_duration_var.set(cfg.get("max_recording_seconds", 300))
        self.save_recordings_var.set(cfg.get("save_recordings", False))

        for label, val in LANGUAGE_OPTIONS:
            if val == cfg.get("language", ""):
                self.language_var.set(label)
                break

        self.whisper_prompt_var.set(cfg.get("whisper_prompt", ""))
        self.ai_cleanup_var.set(cfg.get("ai_cleanup", True))

        for label, val in CLEANUP_MODELS:
            if val == cfg.get("cleanup_model", "gpt-4o-mini"):
                self.cleanup_model_var.set(label)
                break

        self.custom_prompt_var.set(cfg.get("custom_prompt", ""))
        self.auto_paste_var.set(cfg.get("auto_paste", True))
        self.sound_var.set(cfg.get("sound_feedback", True))
        self.notification_var.set(cfg.get("show_notification", True))
        self.notification_preview_var.set(cfg.get("notification_preview", False))

        # Meeting settings
        self.meeting_chunk_var.set(cfg.get("meeting_chunk_seconds", 240))
        self.meeting_mix_var.set(cfg.get("meeting_mix_audio", False))
        fmt = cfg.get("meeting_output_format", "markdown")
        self.meeting_format_var.set("Markdown" if fmt == "markdown" else "Plain Text")
        self.meeting_dir_var.set(cfg.get("meeting_output_dir", ""))
        self.meeting_cost_var.set(cfg.get("meeting_cost_warning", True))

        # Load dictionary
        if DICTIONARY_FILE.exists():
            self.dict_text.insert("1.0", DICTIONARY_FILE.read_text())

        self._toggle_cleanup()

    def _on_save(self):
        # Resolve hotkey value
        hotkey_val = "option"
        for label, val in HOTKEY_OPTIONS:
            if label == self.hotkey_var.get():
                hotkey_val = val
                break

        mode_val = "hold"
        for label, val in MODE_OPTIONS:
            if label == self.mode_var.get():
                mode_val = val
                break

        lang_val = ""
        for label, val in LANGUAGE_OPTIONS:
            if label == self.language_var.get():
                lang_val = val
                break

        cleanup_model_val = "gpt-4o-mini"
        for label, val in CLEANUP_MODELS:
            if label == self.cleanup_model_var.get():
                cleanup_model_val = val
                break

        meeting_format = "markdown" if self.meeting_format_var.get() == "Markdown" else "text"

        self.config.update({
            "hotkey": hotkey_val,
            "mode": mode_val,
            "whisper_model": "whisper-1",
            "language": lang_val,
            "ai_cleanup": self.ai_cleanup_var.get(),
            "cleanup_model": cleanup_model_val,
            "auto_paste": self.auto_paste_var.get(),
            "sound_feedback": self.sound_var.get(),
            "show_notification": self.notification_var.get(),
            "notification_preview": self.notification_preview_var.get(),
            "save_recordings": self.save_recordings_var.get(),
            "custom_prompt": self.custom_prompt_var.get(),
            "whisper_prompt": self.whisper_prompt_var.get(),
            "max_recording_seconds": self.max_duration_var.get(),
            "meeting_chunk_seconds": self.meeting_chunk_var.get(),
            "meeting_mix_audio": self.meeting_mix_var.get(),
            "meeting_output_format": meeting_format,
            "meeting_output_dir": self.meeting_dir_var.get(),
            "meeting_cost_warning": self.meeting_cost_var.get(),
        })

        ok, error = save_api_key(self.api_key_var.get())
        if not ok:
            messagebox.showerror(
                "VoiceFlow",
                f"Could not save the API key securely.\n\n{error}\n\n"
                "You can still use OPENAI_API_KEY as an environment variable.",
            )
            return

        self._save_config()

        # Save dictionary
        dict_content = self.dict_text.get("1.0", tk.END).strip()
        save_dictionary(dict_content)

        messagebox.showinfo("VoiceFlow", "Settings saved!\n\nRestart VoiceFlow for changes to take effect.")
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = SettingsApp()
    app.run()

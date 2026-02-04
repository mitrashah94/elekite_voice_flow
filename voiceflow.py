#!/usr/bin/env python3
"""
VoiceFlow - A voice typing app for macOS.

This file is a compatibility shim. The actual implementation
is in the voiceflow/ package. Run with:
    python -m voiceflow
    OR
    python voiceflow.py
"""

if __name__ == "__main__":
    from voiceflow.core.app import main
    main()

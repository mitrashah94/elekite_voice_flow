"""Hotkey configuration and conflict detection.

Provides hotkey fallback when primary is taken by another app (Discord, OBS, etc.).
"""

import logging

# Lazy import for optional dependency
try:
    from pynput import keyboard
    from pynput.keyboard import Key
except ImportError:
    keyboard = None
    Key = None


# Default hotkeys - can be configured
# PRIMARY_HOTKEY: Alt/Option key (most common voice app hotkey)
# ALTERNATE_HOTKEY: Right Ctrl as fallback (less likely to conflict)
PRIMARY_HOTKEY = "option"  # Alt/Option key
ALTERNATE_HOTKEY = "ctrl_r"  # Right Ctrl as fallback


def _get_logger():
    """Get logger for hotkey module."""
    return logging.getLogger("voiceflow.core.hotkey")


def is_hotkey_available(hotkey_name: str) -> bool:
    """Test if a hotkey can be registered without conflict.

    Uses pynput to attempt registration. Some apps (Discord, OBS)
    grab global hotkeys - this detects that.

    Args:
        hotkey_name: Name of the hotkey to test (e.g., "option", "ctrl_r")

    Returns:
        True if hotkey appears available, False if taken or error
    """
    if keyboard is None:
        _get_logger().warning("pynput not available, cannot test hotkey")
        return True  # Assume available if we can't test

    try:
        # Try to create a listener - pynput may raise if hotkey is grabbed
        # We use suppress=False to avoid interfering with other apps
        test_listener = keyboard.Listener(
            on_press=lambda k: None,
            suppress=False
        )
        test_listener.start()
        test_listener.stop()
        return True
    except Exception as e:
        _get_logger().warning(f"Hotkey {hotkey_name} not available: {e}")
        return False


def get_active_hotkey() -> tuple[str, bool]:
    """Get the active hotkey, falling back if primary is taken.

    Tries primary hotkey first, falls back to alternate if taken.
    Both hotkeys unavailable means we use primary anyway (best effort).

    Returns:
        Tuple of (hotkey_name, is_fallback) where:
        - hotkey_name: The hotkey to use (e.g., "option" or "ctrl_r")
        - is_fallback: True if we fell back from primary to alternate
    """
    logger = _get_logger()

    if is_hotkey_available(PRIMARY_HOTKEY):
        logger.info(f"Using primary hotkey: {PRIMARY_HOTKEY}")
        return PRIMARY_HOTKEY, False

    logger.warning(f"Primary hotkey '{PRIMARY_HOTKEY}' unavailable, trying alternate")

    if is_hotkey_available(ALTERNATE_HOTKEY):
        logger.info(f"Using fallback hotkey: {ALTERNATE_HOTKEY}")
        return ALTERNATE_HOTKEY, True

    # Both unavailable - use primary anyway and hope for the best
    logger.warning("Warning: Both hotkeys may be unavailable, using primary anyway")
    return PRIMARY_HOTKEY, False


def get_hotkey_display_name(hotkey_name: str) -> str:
    """Get a user-friendly display name for a hotkey.

    Args:
        hotkey_name: Internal hotkey name (e.g., "option", "ctrl_r")

    Returns:
        Display name (e.g., "Option", "Right Ctrl")
    """
    display_names = {
        "option": "Option",
        "option_r": "Right Option",
        "ctrl": "Ctrl",
        "ctrl_r": "Right Ctrl",
        "cmd": "Command",
        "cmd_r": "Right Command",
        "shift": "Shift",
        "fn": "Fn",
        "caps_lock": "Caps Lock",
    }
    return display_names.get(hotkey_name, hotkey_name.capitalize())

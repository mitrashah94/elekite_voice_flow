"""Secure API key storage helpers."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .config import CONFIG_DIR, ensure_private_dir, write_secure_bytes


SERVICE_NAME = "VoiceFlow"
ACCOUNT_NAME = "openai_api_key"
WINDOWS_KEY_FILE = CONFIG_DIR / "api_key.bin"


def get_api_key(config: dict | None = None) -> str:
    """Resolve API key with env override, secure storage, then legacy config fallback."""
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if env_key:
        return env_key

    stored_key = load_stored_api_key()
    if stored_key:
        return stored_key

    if config:
        return str(config.get("api_key", "")).strip()
    return ""


def load_stored_api_key() -> str:
    """Load API key from the platform secure store."""
    try:
        if sys.platform == "darwin":
            return _load_api_key_macos()
        if sys.platform == "win32":
            return _load_api_key_windows()
    except Exception:
        return ""
    return ""


def save_api_key(api_key: str) -> tuple[bool, str | None]:
    """Persist API key securely for the current user."""
    api_key = api_key.strip()
    if not api_key:
        return delete_api_key()

    try:
        if sys.platform == "darwin":
            _save_api_key_macos(api_key)
            return True, None
        if sys.platform == "win32":
            _save_api_key_windows(api_key)
            return True, None
    except Exception as exc:
        return False, str(exc)
    return False, "Secure API key storage is not supported on this platform."


def delete_api_key() -> tuple[bool, str | None]:
    """Remove API key from secure storage."""
    try:
        if sys.platform == "darwin":
            _delete_api_key_macos()
            return True, None
        if sys.platform == "win32":
            _delete_api_key_windows()
            return True, None
    except Exception as exc:
        return False, str(exc)
    return True, None


def migrate_legacy_api_key(config: dict) -> tuple[bool, str | None]:
    """Move a plaintext config API key into secure storage when possible."""
    legacy_key = str(config.get("api_key", "")).strip()
    if not legacy_key:
        return False, None

    ok, error = save_api_key(legacy_key)
    if ok:
        config["api_key"] = ""
        return True, None
    return False, error


def describe_api_key_storage() -> str:
    """Human-readable description of the secure storage backend."""
    if sys.platform == "darwin":
        return "macOS Keychain"
    if sys.platform == "win32":
        return "Windows protected storage"
    return "OPENAI_API_KEY environment variable"


def _load_api_key_macos() -> str:
    result = subprocess.run(
        [
            "security",
            "find-generic-password",
            "-a",
            ACCOUNT_NAME,
            "-s",
            SERVICE_NAME,
            "-w",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _save_api_key_macos(api_key: str) -> None:
    result = subprocess.run(
        [
            "security",
            "add-generic-password",
            "-U",
            "-a",
            ACCOUNT_NAME,
            "-s",
            SERVICE_NAME,
            "-w",
            api_key,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Unable to store API key in Keychain.")


def _delete_api_key_macos() -> None:
    subprocess.run(
        [
            "security",
            "delete-generic-password",
            "-a",
            ACCOUNT_NAME,
            "-s",
            SERVICE_NAME,
        ],
        capture_output=True,
        text=True,
    )


def _load_api_key_windows() -> str:
    if not WINDOWS_KEY_FILE.exists():
        return ""
    encrypted = WINDOWS_KEY_FILE.read_bytes()
    return _windows_unprotect(encrypted).decode("utf-8")


def _save_api_key_windows(api_key: str) -> None:
    ensure_private_dir(CONFIG_DIR)
    encrypted = _windows_protect(api_key.encode("utf-8"))
    write_secure_bytes(WINDOWS_KEY_FILE, encrypted, private_parent=True)


def _delete_api_key_windows() -> None:
    if WINDOWS_KEY_FILE.exists():
        WINDOWS_KEY_FILE.unlink()


def _windows_protect(data: bytes) -> bytes:
    import ctypes
    from ctypes import POINTER, byref, c_char, c_void_p, c_wchar_p, windll
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", POINTER(c_char))]

    def _to_blob(raw: bytes) -> DATA_BLOB:
        buffer = ctypes.create_string_buffer(raw)
        return DATA_BLOB(len(raw), ctypes.cast(buffer, POINTER(c_char)))

    in_blob = _to_blob(data)
    out_blob = DATA_BLOB()

    if not windll.crypt32.CryptProtectData(
        byref(in_blob),
        c_wchar_p("VoiceFlow API key"),
        None,
        None,
        None,
        0,
        byref(out_blob),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        windll.kernel32.LocalFree(c_void_p(out_blob.pbData))


def _windows_unprotect(data: bytes) -> bytes:
    import ctypes
    from ctypes import POINTER, byref, c_char, c_void_p, windll
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", POINTER(c_char))]

    def _to_blob(raw: bytes) -> DATA_BLOB:
        buffer = ctypes.create_string_buffer(raw)
        return DATA_BLOB(len(raw), ctypes.cast(buffer, POINTER(c_char)))

    in_blob = _to_blob(data)
    out_blob = DATA_BLOB()

    if not windll.crypt32.CryptUnprotectData(
        byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        byref(out_blob),
    ):
        raise ctypes.WinError()

    try:
        return ctypes.string_at(out_blob.pbData, out_blob.cbData)
    finally:
        windll.kernel32.LocalFree(c_void_p(out_blob.pbData))

import tkinter as tk
from tkinter import ttk
import re
import os
import io
import sys
import json
import math
import wave
import struct
import ctypes
import threading
import subprocess
import webbrowser
try:
    import winsound  # stdlib on Windows; absent on other OSes
    _SOUND_AVAILABLE = True
except Exception:
    _SOUND_AVAILABLE = False
import traceback
from ctypes import wintypes
from tkinter import messagebox

# Optional system-tray support. If pystray + Pillow aren't installed,
# we silently fall back to normal taskbar minimize/close behavior.
_TRAY_IMPORT_ERROR = None
try:
    import pystray
    from PIL import Image, ImageDraw
    _TRAY_AVAILABLE = True
except Exception as _e:
    _TRAY_AVAILABLE = False
    _TRAY_IMPORT_ERROR = f"{type(_e).__name__}: {_e}"

# ================== THEME ==================
# ============================================================================
#  COLOR PALETTES
# ============================================================================
# The GUI references these names as module globals. On theme switch we
# reassign them in-place so the next time any widget is constructed it
# picks up the new colors. Existing widgets get rebuilt by `apply_theme`.

_PALETTE_COLOR = dict(
    BG_MAIN     = "#0d1117",
    BG_CARD     = "#161b22",
    BG_HEADER   = "#1c2128",
    BG_INPUT    = "#21262d",
    BORDER      = "#30363d",

    ACCENT_RED    = "#ff3366",
    ACCENT_BLUE   = "#1f6feb",
    ACCENT_PURPLE = "#a371f7",
    SLIDER_TROUGH = "#6e7681",
    SUCCESS       = "#3fb950",
    DANGER        = "#f85149",
    INFO          = "#58a6ff",
    YELLOW        = "#ffd33d",

    TEXT_HEAD = "#f0f6fc",
    TEXT_BODY = "#c9d1d9",
    TEXT_MUTED= "#7d8590",
)

# Dark mode: the colored accents go black/near-black; buttons all become
# dark grey; bullet/text colors stay bright enough to read against black.
_PALETTE_DARK = dict(
    BG_MAIN     = "#000000",
    BG_CARD     = "#0a0a0a",
    BG_HEADER   = "#1f1f1f",   # dark grey strip behind logo + status bar
    BG_INPUT    = "#1a1a1a",
    BORDER      = "#333333",

    # Accents collapse to greys/blacks. Section headers + ring borders read
    # as a thin dark outline rather than colored bands. We keep them just
    # bright enough to stay visible against the BG_CARD.
    ACCENT_RED    = "#2a2a2a",
    ACCENT_BLUE   = "#2a2a2a",
    ACCENT_PURPLE = "#2a2a2a",
    SLIDER_TROUGH = "#5a5a5a",
    SUCCESS       = "#2a2a2a",
    DANGER        = "#2a2a2a",
    INFO          = "#2a2a2a",
    YELLOW        = "#cccccc",   # bullets stay visible (light grey)

    TEXT_HEAD = "#ffffff",
    TEXT_BODY = "#dddddd",
    TEXT_MUTED= "#888888",
)

# Light mode: white + light-grey backgrounds, black text, cyan hover accents.
_PALETTE_LIGHT = dict(
    BG_MAIN     = "#f5f7fa",   # very light grey body
    BG_CARD     = "#ffffff",   # white cards
    BG_HEADER   = "#e8ecf1",   # slightly darker grey for header / status bar
    BG_INPUT    = "#ffffff",
    BORDER      = "#c9d1d9",

    # Accents flatten to a soft mid-grey so section headers / ring borders
    # don't fight the white cards.
    ACCENT_RED    = "#b8bec6",
    ACCENT_BLUE   = "#b8bec6",
    ACCENT_PURPLE = "#b8bec6",
    SLIDER_TROUGH = "#d0d7de",
    SUCCESS       = "#b8bec6",
    DANGER        = "#b8bec6",
    INFO          = "#b8bec6",
    YELLOW        = "#525860",   # bullets stay visible (dark grey)

    TEXT_HEAD = "#0d1117",       # near-black headings
    TEXT_BODY = "#262c34",
    TEXT_MUTED= "#6a737d",
)

def _apply_palette(palette):
    """Reassign module globals from a palette dict so subsequent widget
    construction (and ttk style reconfiguration) sees the new colors."""
    g = globals()
    for k, v in palette.items():
        g[k] = v

# Apply the colorful palette by default. Theme switch flips between them.
_apply_palette(_PALETTE_COLOR)

FONT_TITLE   = ("Segoe UI Semibold", 16)
FONT_SUB     = ("Segoe UI", 9)
FONT_SECTION = ("Segoe UI Semibold", 11)
FONT_LABEL   = ("Segoe UI", 9)
FONT_BULLET  = ("Segoe UI", 11)
FONT_BTN     = ("Segoe UI Semibold", 9)
FONT_STATUS  = ("Segoe UI", 9)

# ================== PATHS ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MOUSE_SCRIPT_PATH = os.path.join(BASE_DIR, r"scripts\profiles\HeadToMouse.py")
JOY_SCRIPT_PATH   = os.path.join(BASE_DIR, r"scripts\profiles\HeadToJoy.py")
SIXDOF_SCRIPT_PATH = os.path.join(BASE_DIR, r"scripts\profiles\6DOFtoUDP.py")
MOUSE_BAT_PATH    = os.path.join(BASE_DIR, r"a VR Companion - HeadToMouse.bat")
JOY_BAT_PATH      = os.path.join(BASE_DIR, r"a VR Companion - HeadToJoy.bat")

# Direct-launch FreePIE config (replaces the .bat indirection so no terminal
# ever appears and Stop can reliably kill what we started).
FREEPIE_EXE       = "FreePIE.Console.exe"   # resolved against BASE_DIR or PATH
VR_COMPANION_PY   = os.path.join(BASE_DIR, "scripts", "vr_companion.py")
PROFILE_MOUSE     = "HeadToMouse"
PROFILE_JOY       = "HeadToJoy"
PROFILE_6DOF      = "6DOFtoUDP"
SIXDOF_GITHUB_URL = "https://github.com/itsloopyo"

CREATE_NO_WINDOW = 0x08000000
CURVE_OFF_LABEL  = "Curve: OFF (Comment Out)"


def _hover(btn, normal, hovered):
    btn.bind("<Enter>", lambda e: btn.config(bg=hovered))
    btn.bind("<Leave>", lambda e: btn.config(bg=normal))


def _build_chime_wav(notes, volume=0.6, sample_rate=22050):
    """Build an in-memory WAV from a list of (freq_hz, duration_ms) notes.

    Each note gets a short attack and a gentle decay so consecutive tones
    blend into a USB-like chime instead of clicking.
    """
    frames = bytearray()
    amp = volume * 32767
    attack_samples = int(sample_rate * 0.005)  # 5 ms attack to avoid clicks
    for freq, duration_ms in notes:
        n = int(sample_rate * duration_ms / 1000)
        for i in range(n):
            attack = min(1.0, i / attack_samples) if attack_samples else 1.0
            decay = 1.0 - 0.55 * (i / max(1, n - 1))
            env = attack * decay
            sample = int(amp * env * math.sin(2.0 * math.pi * freq * i / sample_rate))
            frames += struct.pack("<h", sample)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)        # 16-bit
        w.setframerate(sample_rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


# Lazily-built chime cache. Generating the WAVs at module load runs before
# the elevation re-launch, and any silent failure there leaves us with no
# audio. Building on first use sidesteps that and gives us a place to log
# any exception to launch_error.log.
_CHIME_CACHE = {}

def _get_chime(starting):
    key = "connect" if starting else "disconnect"
    wav = _CHIME_CACHE.get(key)
    if wav is not None:
        return wav
    try:
        if starting:
            wav = _build_chime_wav([(1200, 70), (1800, 110)], volume=0.3)
        else:
            wav = _build_chime_wav([(1800, 70), (1200, 110)], volume=0.3)
        _CHIME_CACHE[key] = wav
        return wav
    except Exception as e:
        try:
            with open(os.path.join(BASE_DIR, "launch_error.log"), "a",
                      encoding="utf-8") as f:
                f.write(f"\n--- _build_chime_wav({key}) ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass
        return None


def _play_tracking_sound(starting):
    """Play a higher-pitched USB-style chime (rising for start, falling for stop).

    Tries the synthesized in-memory WAV first. If that fails for any reason,
    falls back to the Windows system alias (DeviceConnect / DeviceDisconnect)
    so the user still gets audible feedback.
    """
    if not _SOUND_AVAILABLE:
        return

    wav = _get_chime(starting)
    if wav is not None:
        try:
            winsound.PlaySound(wav, winsound.SND_MEMORY | winsound.SND_ASYNC)
            return
        except Exception:
            pass  # fall through to alias fallback

    # Fallback path — system-themed USB chime via registry alias.
    try:
        alias = "DeviceConnect" if starting else "DeviceDisconnect"
        winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
    except Exception:
        pass


# ================== HOTKEYS ==================
HOTKEYS_PATH = os.path.join(BASE_DIR, "hotkeys.json")
WINDOW_STATE_PATH = os.path.join(BASE_DIR, "window_state.json")

# Win32 modifier flags / messages
_MOD_ALT, _MOD_CTRL, _MOD_SHIFT, _MOD_WIN = 0x0001, 0x0002, 0x0004, 0x0008
_MOD_NOREPEAT = 0x4000
_WM_HOTKEY = 0x0312
_WM_QUIT   = 0x0012

# Tk keysym -> Win32 virtual-key code (for non-alphanumeric keys)
_VK_NAMED = {
    # Function keys F1..F24
    "F1":0x70,"F2":0x71,"F3":0x72,"F4":0x73,"F5":0x74,"F6":0x75,
    "F7":0x76,"F8":0x77,"F9":0x78,"F10":0x79,"F11":0x7A,"F12":0x7B,
    "F13":0x7C,"F14":0x7D,"F15":0x7E,"F16":0x7F,"F17":0x80,"F18":0x81,
    "F19":0x82,"F20":0x83,"F21":0x84,"F22":0x85,"F23":0x86,"F24":0x87,

    # Whitespace / control
    "Space":0x20,"Tab":0x09,"Return":0x0D,"Escape":0x1B,"BackSpace":0x08,
    "Pause":0x13,"Cancel":0x03,"Clear":0x0C,

    # Editing/navigation
    "Insert":0x2D,"Delete":0x2E,"Home":0x24,"End":0x23,
    "Page_Up":0x21,"Page_Down":0x22,"Prior":0x21,"Next":0x22,
    "Up":0x26,"Down":0x28,"Left":0x25,"Right":0x27,
    "Print":0x2C,"Sys_Req":0x2C,"Help":0x2F,"Select":0x29,

    # Lock keys (yes — these are valid hotkey targets too)
    "Caps_Lock":0x14,"Num_Lock":0x90,"Scroll_Lock":0x91,

    # Application/menu key (between right Win and right Ctrl)
    "Menu":0x5D,

    # Numpad — store the NumLock-ON VK here. The non-NumLock fallback VKs
    # for KP_Insert / KP_End / KP_Down / etc. are added as additional
    # registrations by `_parse_binding` so the hotkey fires regardless of
    # whether NumLock is on or off.
    "KP_0":0x60,"KP_1":0x61,"KP_2":0x62,"KP_3":0x63,"KP_4":0x64,
    "KP_5":0x65,"KP_6":0x66,"KP_7":0x67,"KP_8":0x68,"KP_9":0x69,
    "KP_Multiply":0x6A,"KP_Add":0x6B,"KP_Separator":0x6C,
    "KP_Subtract":0x6D,"KP_Decimal":0x6E,"KP_Divide":0x6F,
    "KP_Enter":0x0D,
    # When the user presses a numpad key with NumLock OFF, Tk emits a
    # navigation keysym instead of KP_N. We accept those at capture time
    # and treat them as their numpad equivalents.
    "KP_Insert":0x60,"KP_End":0x61,"KP_Down":0x62,"KP_Next":0x63,
    "KP_Left":0x64,"KP_Begin":0x65,"KP_Right":0x66,"KP_Home":0x67,
    "KP_Up":0x68,"KP_Prior":0x69,"KP_Delete":0x6E,

    # Punctuation — Tk reports these as named keysyms, not as their char.
    "minus":0xBD,"equal":0xBB,
    "bracketleft":0xDB,"bracketright":0xDD,
    "semicolon":0xBA,"apostrophe":0xDE,
    "comma":0xBC,"period":0xBE,
    "slash":0xBF,"backslash":0xDC,
    "grave":0xC0,"asciitilde":0xC0,
    "quoteleft":0xC0,"quoteright":0xDE,

    # Media / browser keys (laptops, multimedia keyboards)
    "XF86AudioMute":0xAD,"XF86AudioLowerVolume":0xAE,"XF86AudioRaiseVolume":0xAF,
    "XF86AudioPlay":0xB3,"XF86AudioStop":0xB2,
    "XF86AudioNext":0xB0,"XF86AudioPrev":0xB1,
    "XF86Mail":0xB4,"XF86HomePage":0xAC,"XF86Search":0xAA,
    "XF86Calculator":0xB7,"XF86MyComputer":0xB6,
}

# Numpad keys map to TWO Win32 VKs depending on NumLock state.
# Registering both makes hotkeys work whether NumLock is on or off.
# Maps NumLock-ON VK -> NumLock-OFF VK that Windows fires instead.
_NUMPAD_ALT_VK = {
    0x60: 0x2D,   # NUMPAD0  <-> INSERT
    0x61: 0x23,   # NUMPAD1  <-> END
    0x62: 0x28,   # NUMPAD2  <-> DOWN
    0x63: 0x22,   # NUMPAD3  <-> NEXT       (Page Down)
    0x64: 0x25,   # NUMPAD4  <-> LEFT
    0x65: 0x0C,   # NUMPAD5  <-> CLEAR      (5 with NumLock OFF on most layouts)
    0x66: 0x27,   # NUMPAD6  <-> RIGHT
    0x67: 0x24,   # NUMPAD7  <-> HOME
    0x68: 0x26,   # NUMPAD8  <-> UP
    0x69: 0x21,   # NUMPAD9  <-> PRIOR      (Page Up)
    0x6E: 0x2E,   # DECIMAL  <-> DELETE     (".")
}

# Pretty display labels — turn 'KP_Add' into 'Num +', 'semicolon' into ';', etc.
_KEY_DISPLAY = {
    # Numpad
    "KP_0":"Num 0","KP_1":"Num 1","KP_2":"Num 2","KP_3":"Num 3","KP_4":"Num 4",
    "KP_5":"Num 5","KP_6":"Num 6","KP_7":"Num 7","KP_8":"Num 8","KP_9":"Num 9",
    "KP_Add":"Num +","KP_Subtract":"Num -","KP_Multiply":"Num *",
    "KP_Divide":"Num /","KP_Decimal":"Num .","KP_Enter":"Num Enter",
    "KP_Insert":"Num 0","KP_End":"Num 1","KP_Down":"Num 2","KP_Next":"Num 3",
    "KP_Left":"Num 4","KP_Begin":"Num 5","KP_Right":"Num 6","KP_Home":"Num 7",
    "KP_Up":"Num 8","KP_Prior":"Num 9","KP_Delete":"Num .",
    # Navigation
    "Page_Up":"PgUp","Page_Down":"PgDn","Prior":"PgUp","Next":"PgDn",
    "BackSpace":"Backspace","Return":"Enter","Escape":"Esc",
    # Punctuation
    "minus":"-","equal":"=",
    "bracketleft":"[","bracketright":"]",
    "semicolon":";","apostrophe":"'",
    "comma":",","period":".",
    "slash":"/","backslash":"\\",
    "grave":"`","asciitilde":"`",
    "quoteleft":"`","quoteright":"'",
    # Locks/specials
    "Caps_Lock":"Caps","Num_Lock":"NumLk","Scroll_Lock":"ScrLk",
    "Print":"PrtSc","Sys_Req":"PrtSc","Pause":"Pause","Menu":"Menu",
    # Media
    "XF86AudioMute":"Mute","XF86AudioLowerVolume":"Vol-","XF86AudioRaiseVolume":"Vol+",
    "XF86AudioPlay":"Play","XF86AudioStop":"Stop",
    "XF86AudioNext":"Next","XF86AudioPrev":"Prev",
}

def _parse_binding(s):
    """'Ctrl+Shift+F9' -> list of (mods, vk) pairs, or None if invalid/empty.

    Most keys produce a single (mods, vk) pair. Numpad keys produce TWO
    pairs — one for the NumLock-ON VK and one for the NumLock-OFF VK —
    so RegisterHotKey works regardless of NumLock state.
    Also accepts 'VK<keycode>' for keys without a named keysym.
    """
    if not s:
        return None
    parts = s.split("+")
    mods = 0
    mod_map = {"Ctrl":_MOD_CTRL,"Shift":_MOD_SHIFT,"Alt":_MOD_ALT,"Win":_MOD_WIN}
    for p in parts[:-1]:
        if p not in mod_map:
            return None
        mods |= mod_map[p]
    key = parts[-1]
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif key.startswith("VK") and key[2:].isdigit():
        # Universal escape hatch: any VK code by number.
        vk = int(key[2:])
        if not (1 <= vk <= 254):
            return None
    else:
        vk = _VK_NAMED.get(key)
    if vk is None:
        return None

    pairs = [(mods, vk)]
    # If this is a numpad key, also register its NumLock-OFF alias VK so
    # the hotkey fires whether NumLock is on or off.
    alt = _NUMPAD_ALT_VK.get(vk)
    if alt is not None:
        pairs.append((mods, alt))
    return pairs


def _format_binding(s):
    """Pretty display: 'Ctrl+KP_5' -> 'Ctrl + Num 5', 'VK191' -> 'Key 191'."""
    if not s:
        return ""
    parts = s.split("+")
    last = parts[-1]
    if last.startswith("VK") and last[2:].isdigit():
        pretty_last = f"Key {last[2:]}"
    else:
        pretty_last = _KEY_DISPLAY.get(last, last)
    return " + ".join(parts[:-1] + [pretty_last])


class HotkeyManager:
    """Background-thread manager for global hotkeys.

    Most bindings go through Win32 RegisterHotKey on a daemon thread.
    Numpad bindings (digits + operators) use a low-level keyboard hook
    instead, because RegisterHotKey is unreliable for those — they're
    often silently swallowed by Windows or other apps even when the
    registration call succeeds.

    Callbacks are dispatched onto the Tk main thread via root.after().
    """

    # VKs we route through the low-level keyboard hook instead of
    # RegisterHotKey. All numpad digits and operators.
    _HOOK_VKS = frozenset({
        0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69,  # NUMPAD0..9
        0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F,  # MULT, ADD, SEP, SUB, DEC, DIV
    })

    def __init__(self, tk_root):
        self.tk_root = tk_root
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        # Without argtypes, 64-bit Windows mangles handle/integer args
        # and RegisterHotKey silently fails. Declare them explicitly.
        u = self._user32
        u.RegisterHotKey.argtypes = [
            wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        u.RegisterHotKey.restype = wintypes.BOOL

        u.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        u.UnregisterHotKey.restype = wintypes.BOOL

        u.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT]
        u.GetMessageW.restype = ctypes.c_int   # -1 on error, 0 on WM_QUIT

        u.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG), wintypes.HWND,
            wintypes.UINT, wintypes.UINT, wintypes.UINT]
        u.PeekMessageW.restype = wintypes.BOOL

        u.PostThreadMessageW.argtypes = [
            wintypes.DWORD, wintypes.UINT,
            wintypes.WPARAM, wintypes.LPARAM]
        u.PostThreadMessageW.restype = wintypes.BOOL

        # Low-level keyboard hook plumbing.
        u.SetWindowsHookExW.argtypes = [
            ctypes.c_int, ctypes.c_void_p, wintypes.HINSTANCE, wintypes.DWORD]
        u.SetWindowsHookExW.restype = wintypes.HHOOK
        u.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
        u.UnhookWindowsHookEx.restype = wintypes.BOOL
        u.CallNextHookEx.argtypes = [
            wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        u.CallNextHookEx.restype = wintypes.LPARAM
        u.GetAsyncKeyState.argtypes = [ctypes.c_int]
        u.GetAsyncKeyState.restype = ctypes.c_short

        self._kernel32.GetCurrentThreadId.argtypes = []
        self._kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        self._kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        self._kernel32.GetModuleHandleW.restype = wintypes.HMODULE

        # RegisterHotKey thread state
        self._thread = None
        self._thread_id = None

        # Hook thread state
        self._hook_thread = None
        self._hook_thread_id = None
        self._hook_handle = None
        self._hook_proc_ref = None  # MUST keep a reference so it isn't GC'd
        # List of (mods_required, vk, name) for hook matching. Populated
        # by update() based on which bindings need the hook fallback.
        self._hook_bindings = []

        self._callbacks = {}
        self.last_errors = []   # list of (name, binding, win32_error_code)

    def update(self, bindings, callbacks):
        """bindings: name->'Ctrl+F9' string. callbacks: name->callable.
        Restarts the hotkey threads with the new set."""
        self.stop()
        parsed = {}
        hook_bindings = []   # (mods, vk, name)
        for name, s in bindings.items():
            p = _parse_binding(s)
            if not p:
                continue
            # Decide per-pair whether each (mods, vk) goes to RegisterHotKey
            # or the keyboard hook. We split the pair list so a numpad key's
            # NumLock-OFF alias VK still gets registered normally if it
            # isn't itself a numpad VK (it isn't — Insert/End/etc are nav).
            reg_pairs  = []
            hook_pairs = []
            for (mods, vk) in p:
                if vk in self._HOOK_VKS:
                    hook_pairs.append((mods, vk))
                else:
                    reg_pairs.append((mods, vk))
            if reg_pairs:
                parsed[name] = (s, reg_pairs)
            for (mods, vk) in hook_pairs:
                hook_bindings.append((mods, vk, name))

        self._callbacks = dict(callbacks)
        self._hook_bindings = hook_bindings
        self.last_errors = []

        if parsed:
            self._thread = threading.Thread(
                target=self._run, args=(parsed,), daemon=True)
            self._thread.start()
        if hook_bindings:
            self._hook_thread = threading.Thread(
                target=self._run_hook, daemon=True)
            self._hook_thread.start()

    def stop(self):
        # Stop RegisterHotKey thread
        if self._thread and self._thread_id:
            self._user32.PostThreadMessageW(
                self._thread_id, _WM_QUIT, 0, 0)
            self._thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = None

        # Stop hook thread (PostThreadMessage WM_QUIT breaks its GetMessage loop)
        if self._hook_thread and self._hook_thread_id:
            self._user32.PostThreadMessageW(
                self._hook_thread_id, _WM_QUIT, 0, 0)
            self._hook_thread.join(timeout=1.0)
        self._hook_thread = None
        self._hook_thread_id = None
        self._hook_handle = None
        self._hook_proc_ref = None

    def _run(self, parsed):
        self._thread_id = self._kernel32.GetCurrentThreadId()
        # Force creation of the thread message queue so PostThreadMessage works.
        msg = wintypes.MSG()
        self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        ids = {}
        local_errors = []
        next_id = 1
        # `parsed[name]` is (original_str, [(mods, vk), ...]). Each pair
        # gets its own RegisterHotKey ID but maps back to the same `name`,
        # so either VK firing triggers the same callback.
        for name, (orig, pairs) in parsed.items():
            any_ok = False
            for (mods, vk) in pairs:
                hk_id = next_id
                next_id += 1
                ok = self._user32.RegisterHotKey(
                    None, hk_id, mods | _MOD_NOREPEAT, vk)
                if ok:
                    ids[hk_id] = name
                    any_ok = True
            if not any_ok:
                local_errors.append(
                    (name, orig, ctypes.get_last_error()))
        self.last_errors = local_errors

        if local_errors and self.tk_root:
            try:
                self.tk_root.after(0, lambda errs=local_errors:
                                   _report_hotkey_errors(errs))
            except Exception:
                pass

        try:
            while True:
                ret = self._user32.GetMessageW(
                    ctypes.byref(msg), None, 0, 0)
                if ret in (0, -1):
                    break
                if msg.message == _WM_HOTKEY:
                    name = ids.get(msg.wParam)
                    cb = self._callbacks.get(name)
                    if cb and self.tk_root:
                        try:
                            self.tk_root.after(0, cb)
                        except Exception:
                            pass
        finally:
            for hk_id in ids:
                self._user32.UnregisterHotKey(None, hk_id)

    # -------- Low-level keyboard hook fallback --------

    # WH_KEYBOARD_LL = 13. Hook proc receives a virtual-key code in the
    # KBDLLHOOKSTRUCT; we read modifier state via GetAsyncKeyState because
    # the hook runs before normal modifier-tracking is updated for THIS key.
    _WH_KEYBOARD_LL = 13
    _WM_KEYDOWN     = 0x0100
    _WM_KEYUP       = 0x0101
    _WM_SYSKEYDOWN  = 0x0104
    _WM_SYSKEYUP    = 0x0105
    _HC_ACTION      = 0

    def _run_hook(self):
        self._hook_thread_id = self._kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        # KBDLLHOOKSTRUCT layout: vkCode, scanCode, flags, time, dwExtraInfo
        class _KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode",      wintypes.DWORD),
                ("scanCode",    wintypes.DWORD),
                ("flags",       wintypes.DWORD),
                ("time",        wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_void_p),
            ]

        HOOKPROC = ctypes.WINFUNCTYPE(
            wintypes.LPARAM,
            ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

        # Track repeat suppression — Windows fires WM_KEYDOWN repeatedly
        # while the key is held. We only want to trigger once per press.
        held = set()

        def _proc(nCode, wParam, lParam):
            try:
                if nCode == self._HC_ACTION:
                    msg_kind = wParam & 0xFFFFFFFF
                    if msg_kind in (self._WM_KEYDOWN, self._WM_SYSKEYDOWN):
                        kb = ctypes.cast(
                            lParam,
                            ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                        vk = kb.vkCode
                        # Build current modifier mask (high bit = pressed).
                        mods = 0
                        if self._user32.GetAsyncKeyState(0x11) & 0x8000:  # CTRL
                            mods |= _MOD_CTRL
                        if self._user32.GetAsyncKeyState(0x10) & 0x8000:  # SHIFT
                            mods |= _MOD_SHIFT
                        if self._user32.GetAsyncKeyState(0x12) & 0x8000:  # ALT
                            mods |= _MOD_ALT
                        if (self._user32.GetAsyncKeyState(0x5B) & 0x8000  # LWIN
                                or self._user32.GetAsyncKeyState(0x5C) & 0x8000):
                            mods |= _MOD_WIN

                        # Match against bindings. Match IS exact mods + vk.
                        for (req_mods, req_vk, name) in self._hook_bindings:
                            if vk == req_vk and mods == req_mods:
                                key = (req_mods, req_vk)
                                if key in held:
                                    break
                                held.add(key)
                                cb = self._callbacks.get(name)
                                if cb and self.tk_root:
                                    try:
                                        self.tk_root.after(0, cb)
                                    except Exception:
                                        pass
                                break
                    elif msg_kind in (self._WM_KEYUP, self._WM_SYSKEYUP):
                        # Clear held flag for this VK so next press fires.
                        kb = ctypes.cast(
                            lParam,
                            ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                        for k in [k for k in held if k[1] == kb.vkCode]:
                            held.discard(k)
            except Exception:
                pass
            return self._user32.CallNextHookEx(None, nCode, wParam, lParam)

        # Keep references alive so ctypes doesn't GC the trampoline mid-hook.
        self._hook_proc_ref = HOOKPROC(_proc)
        h_module = self._kernel32.GetModuleHandleW(None)
        self._hook_handle = self._user32.SetWindowsHookExW(
            self._WH_KEYBOARD_LL, self._hook_proc_ref, h_module, 0)
        if not self._hook_handle:
            return  # Hook install failed; nothing to do

        try:
            while True:
                ret = self._user32.GetMessageW(
                    ctypes.byref(msg), None, 0, 0)
                if ret in (0, -1):
                    break
        finally:
            try:
                self._user32.UnhookWindowsHookEx(self._hook_handle)
            except Exception:
                pass
            self._hook_handle = None


def _report_hotkey_errors(errs):
    """No-op kept for API compatibility — warnings are silenced by user request."""
    return


# ================== TRAY ==================

def _make_tray_icon_image(size=64):
    """Tray icon: two overlapping balls (red + blue) with 'VR' in black across them."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    RED   = (255, 51, 102, 255)
    BLUE  = (31, 111, 235, 255)
    BLACK = (0, 0, 0, 255)

    # Two overlapping balls. Diameter ~70% of canvas, centered vertically,
    # offset horizontally so they overlap in the middle.
    ball_d = int(size * 0.72)
    cy = size // 2
    pad = (size - ball_d) // 2
    overlap = int(ball_d * 0.30)

    left  = (pad - overlap // 2,            cy - ball_d // 2,
             pad - overlap // 2 + ball_d,   cy + ball_d // 2)
    right = (size - pad + overlap // 2 - ball_d, cy - ball_d // 2,
             size - pad + overlap // 2,          cy + ball_d // 2)
    d.ellipse(left,  fill=RED)
    d.ellipse(right, fill=BLUE)

    # 'VR' centered. Try a real font; fall back to PIL's default if missing.
    text = "VR"
    font = None
    try:
        from PIL import ImageFont
        # Pick a size that comfortably fits both balls.
        for candidate in ("arialbd.ttf", "arial.ttf", "segoeuib.ttf", "DejaVuSans-Bold.ttf"):
            try:
                font = ImageFont.truetype(candidate, int(size * 0.42))
                break
            except Exception:
                continue
    except Exception:
        font = None

    if font is not None:
        bbox = d.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        tx = (size - tw) // 2 - bbox[0]
        ty = (size - th) // 2 - bbox[1]
        d.text((tx, ty), text, fill=BLACK, font=font)
    else:
        # Fallback path — default bitmap font, still centered.
        tw, th = d.textsize(text)
        d.text(((size - tw) // 2, (size - th) // 2), text, fill=BLACK)

    return img


class TrayController:
    """Wraps a pystray icon. Runs the icon's blocking loop on a daemon thread
    so Tk's mainloop stays responsive. All callbacks marshal back onto Tk
    via root.after() because pystray's menu callbacks fire on its own thread.
    """
    def __init__(self, root, on_show, on_quit):
        self.root = root
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon = None
        self._thread = None
        self.init_error = None   # populated if construction fails

        if not _TRAY_AVAILABLE:
            self.init_error = (
                "pystray/Pillow not importable: "
                + (_TRAY_IMPORT_ERROR or "unknown")
            )
            return

        try:
            image = _make_tray_icon_image()
            menu = pystray.Menu(
                pystray.MenuItem("Show VR Head Tracking GUI",
                                 self._invoke_show, default=True),
                pystray.MenuItem("Quit", self._invoke_quit),
            )
            self._icon = pystray.Icon(
                "VRHeadTrackingGUI", image, "VR Head Tracking GUI", menu)
        except Exception as e:
            self.init_error = f"{type(e).__name__}: {e}"
            self._icon = None

    @property
    def available(self):
        return self._icon is not None

    def start(self):
        """Spin up the tray icon on a background thread (idempotent)."""
        if not self.available:
            return
        if self._thread and self._thread.is_alive():
            return

        def _runner():
            try:
                self._icon.run()
            except Exception as e:
                # Capture so the GUI can surface it.
                self.init_error = f"icon.run() crashed: {type(e).__name__}: {e}"

        self._thread = threading.Thread(target=_runner, daemon=True)
        self._thread.start()

    def stop(self):
        if self.available:
            try:
                self._icon.stop()
            except Exception:
                pass

    # --- Menu callbacks (run on pystray's thread) ---
    def _invoke_show(self, icon=None, item=None):
        try:
            self.root.after(0, self._on_show)
        except Exception:
            pass

    def _invoke_quit(self, icon=None, item=None):
        try:
            self.root.after(0, self._on_quit)
        except Exception:
            pass


class HotkeyEntry(tk.Frame):
    """Pixel-square 'click to capture' hotkey widget.

    Visual: thin red outer frame, thin yellow inner frame, darker grey button.
    Esc clears the binding.
    """
    _MOD_KEYS = {"Control_L","Control_R","Shift_L","Shift_R",
                 "Alt_L","Alt_R","Super_L","Super_R","Meta_L","Meta_R"}

    _SIZE = 40             # outer pixel side length

    def __init__(self, parent, label="", initial="", on_change=None, btn_width=None):
        super().__init__(parent, bg=BG_CARD)
        self._binding = initial or ""
        self._on_change = on_change
        self._capturing = False

        # Detect which palette is currently active by looking at BG_MAIN.
        # That way we don't need a 'self.theme_mode' on every parent.
        if BG_MAIN == "#000000":
            mode = "dark"
        elif BG_MAIN == "#f5f7fa":
            mode = "light"
        else:
            mode = "color"

        if mode == "dark":
            self._frame_color = BORDER
            self._face        = "#5a5a5a"
            self._face_hover  = "#388bfd"   # blue on hover
            self._fg          = "#ffffff"
        elif mode == "light":
            self._frame_color = "#b8bec6"   # subtle grey ring
            self._face        = "#e8ecf1"   # pale grey
            self._face_hover  = "#06b6d4"   # cyan on hover
            self._fg          = "#0d1117"
        else:  # color
            self._frame_color = ACCENT_RED
            self._face        = "#8b949e"
            self._face_hover  = "#7d8590"
            self._fg          = "#0d1117"

        # Single thin frame around the button face.
        red_frame = tk.Frame(
            self, bg=self._face,
            width=self._SIZE, height=self._SIZE,
            highlightthickness=1,
            highlightbackground=self._frame_color,
            highlightcolor=self._frame_color,
        )
        red_frame.pack(side="top")
        red_frame.pack_propagate(False)

        self._btn = tk.Button(
            red_frame, text=self._display(), command=self._begin_capture,
            bg=self._face, fg=self._fg,
            font=("Segoe UI", 8, "bold"),
            relief="flat", borderwidth=0, cursor="hand2",
            highlightthickness=0,
            activebackground=self._face_hover, activeforeground=self._fg,
            wraplength=self._SIZE - 6,
            justify="center",
        )
        self._btn.pack(fill="both", expand=True)

    def get(self):
        return self._binding

    def set(self, s):
        self._binding = s or ""
        self._btn.config(text=self._display())

    def _display(self):
        if not self._binding:
            return "—"
        return _format_binding(self._binding)

    def _begin_capture(self):
        if self._capturing:
            return
        self._capturing = True
        self._btn.config(text="…", bg=ACCENT_BLUE, fg="white")
        self._btn.focus_set()
        self._btn.bind("<KeyPress>", self._on_key)
        self._btn.bind("<FocusOut>", lambda e: self._end_capture())

    def _end_capture(self):
        self._capturing = False
        self._btn.config(text=self._display(), bg=self._face, fg=self._fg)
        self._btn.unbind("<KeyPress>")
        self._btn.unbind("<FocusOut>")

    def _on_key(self, event):
        keysym = event.keysym
        if keysym in self._MOD_KEYS:
            return "break"

        if keysym == "Escape":
            new_binding = ""
        else:
            mods = []
            if event.state & 0x4:     mods.append("Ctrl")
            if event.state & 0x1:     mods.append("Shift")
            if event.state & 0x20000: mods.append("Alt")

            # Pick the best key identifier in priority order:
            #   1) Single alnum char  -> store uppercase letter/digit
            #   2) Known named keysym -> store the name (pretty)
            #   3) Tk keycode         -> universal fallback (Tk's keycode IS
            #      the Win32 VK on Windows, so this works for ANY key the
            #      user presses, including ones I haven't named explicitly).
            if len(keysym) == 1 and keysym.isalnum():
                key = keysym.upper()
            elif keysym in _VK_NAMED:
                key = keysym
            elif getattr(event, "keycode", 0):
                key = f"VK{event.keycode}"
            else:
                return "break"   # truly unidentifiable — extremely rare

            candidate = "+".join(mods + [key])
            if _parse_binding(candidate) is None:
                return "break"
            new_binding = candidate

        self._binding = new_binding
        self._end_capture()
        if self._on_change:
            self._on_change(new_binding)
        return "break"


class VRHeadTrackingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("VR Head Tracking GUI")
        self.root.configure(bg=BG_MAIN)
        self.root.minsize(560, 600)

        # Geometry is restored later from window_state.json (or falls back
        # to a sensible default if no saved state exists / is invalid).

        self.curve_options = {
            CURVE_OFF_LABEL:           None,
            "Linear (Mouse-like)":     0.0,
            "Aggressive (Fast Onset)": 0.5,
            "Smooth (Gentle Center)":  1.5,
            "Precision (Deep Curve)":  2.5,
        }

        # Track launched .bat processes so we can stop them cleanly
        # without a visible terminal to target by window title.
        self.processes = {}  # bat_path -> subprocess.Popen

        # Hotkey state — loaded from disk, edited via HotkeyEntry widgets,
        # registered globally via HotkeyManager.
        self.hotkeys = self._load_hotkeys()
        self._hotkey_widgets = {}   # name -> list[HotkeyEntry]  (stop has 2)
        self.hotkey_mgr = HotkeyManager(self.root)

        # System tray controller (no-op if pystray/Pillow are unavailable).
        self.tray = TrayController(
            self.root, on_show=self.show_window, on_quit=self.quit_app)

        # Layout mode (vertical = stacked, horizontal = side-by-side).
        # Loaded from window_state.json so it persists across launches.
        self.layout_mode = self._load_layout_mode()
        self.theme_mode = self._load_theme_mode()
        # Apply the saved theme palette before any widgets are created.
        _apply_palette({
            "color": _PALETTE_COLOR,
            "dark":  _PALETTE_DARK,
            "light": _PALETTE_LIGHT,
        }.get(self.theme_mode, _PALETTE_COLOR))
        self._sections_container = None  # set by _build_ui

        self._setup_ttk_style()
        self._build_ui()
        self._refresh_hotkeys()
        self._load_window_geometry()

        # X (close button) always quits the app. Minimize-to-tray is handled
        # separately by the state-polling watcher when tray is available.
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

        if self.tray.available:
            # Defer tray startup until after Tk has finished initializing —
            # starting pystray during __init__ can race with Tk's window
            # creation on Windows and leave the icon thread stuck.
            self.root.after(150, self.tray.start)
            # Poll for the iconified state instead of relying on <Unmap>,
            # which is unreliable across Windows builds and fires for many
            # unrelated reasons.
            self._was_iconic = False
            self.root.after(200, self._watch_minimize)

        try:
            self.sync_from_files()
        except Exception:
            self.status_label.config(text="●  Ready (sync skipped)", fg=TEXT_MUTED)

    # ================== STYLE ==================

    def _setup_ttk_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Dark.TCombobox",
            fieldbackground=BG_INPUT, background=BG_INPUT,
            foreground=TEXT_HEAD, arrowcolor=ACCENT_BLUE,
            bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
            borderwidth=1, relief="flat", padding=6,
        )
        style.map(
            "Dark.TCombobox",
            fieldbackground=[("readonly", BG_INPUT)],
            foreground=[("readonly", TEXT_HEAD)],
            background=[("active", BG_INPUT)],
        )

        # Slider thumb colors are palette-aware:
        # - COLORED: red/purple thumb with brighter hover.
        # - DARK: dark-blue thumb, brighter blue on hover.
        # - LIGHT: muted-grey thumb, cyan on hover.
        mode = getattr(self, "theme_mode", "color")
        if mode == "dark":
            thumb_red       = "#1f4488"
            thumb_red_hover = "#388bfd"
            thumb_pur       = "#1f4488"
            thumb_pur_hover = "#388bfd"
        elif mode == "light":
            thumb_red       = "#8b949e"   # mid grey thumb on white
            thumb_red_hover = "#06b6d4"   # cyan on hover
            thumb_pur       = "#8b949e"
            thumb_pur_hover = "#06b6d4"
        else:
            thumb_red       = ACCENT_RED
            thumb_red_hover = "#ff5478"
            thumb_pur       = ACCENT_PURPLE
            thumb_pur_hover = "#bb8aff"

        style.configure(
            "Red.Horizontal.TScale",
            troughcolor=SLIDER_TROUGH,
            background=thumb_red,
            bordercolor=BORDER,
            lightcolor=thumb_red, darkcolor=thumb_red,
            sliderthickness=18, sliderlength=16,
        )
        style.map(
            "Red.Horizontal.TScale",
            background=[("active", thumb_red_hover)],
        )

        style.configure(
            "Purple.Horizontal.TScale",
            troughcolor=SLIDER_TROUGH,
            background=thumb_pur,
            bordercolor=BORDER,
            lightcolor=thumb_pur, darkcolor=thumb_pur,
            sliderthickness=18, sliderlength=16,
        )
        style.map(
            "Purple.Horizontal.TScale",
            background=[("active", thumb_pur_hover)],
        )

    # ================== BUILD ==================

    def _build_ui(self):
        self._build_header()

        # Sections live in their own container so we can destroy/rebuild
        # them when the user toggles the layout, without touching the
        # header or status bar.
        self._sections_container = tk.Frame(self.root, bg=BG_MAIN)
        self._populate_sections()

        self._build_status_bar()

    def _populate_sections(self):
        """(Re)build all section cards according to the current layout mode."""
        # Pack the container appropriately first (must happen before children).
        if self.layout_mode == "horizontal":
            # Insert container BEFORE the status bar (status bar is already
            # packed at the bottom). fill="both" + expand=True lets sections
            # spread evenly side-by-side.
            self._sections_container.pack(fill="both", expand=True)
        else:
            self._sections_container.pack(fill="x")

        self._build_mouse_section()
        self._build_joy_section()
        self._build_sixdof_section()

    def toggle_layout(self):
        """Flip between vertical and horizontal layouts. Rebuilds sections,
        re-binds the hotkey widgets, and resizes the window appropriately."""
        # Capture all current values from the UI vars BEFORE destroying widgets
        # — Tk DoubleVar/StringVar objects survive widget destruction, but
        # any closure-bound widget references would be stale.
        self.layout_mode = ("horizontal"
                            if self.layout_mode == "vertical"
                            else "vertical")

        # Hotkey widgets get re-created on rebuild, so reset the registry
        # of HotkeyEntry instances (the bindings dict self.hotkeys is unchanged).
        self._hotkey_widgets = {}

        # Tear down old sections and recreate.
        for child in self._sections_container.winfo_children():
            child.destroy()
        self._sections_container.pack_forget()
        self._populate_sections()

        # Update the toggle button label.
        if hasattr(self, "_layout_btn"):
            self._layout_btn.config(text=self._layout_button_label())

        # Pick a sensible window size for the new orientation.
        if self.layout_mode == "horizontal":
            self.root.geometry("1500x720")
        else:
            self.root.geometry("580x1620")

        # Re-sync values from disk so newly-created sliders/inputs show
        # the same data as before the toggle.
        try:
            self.sync_from_files()
        except Exception:
            pass

        self._save_layout_mode()

    # Logo dimensions (small constants so _draw_logo can scale).
    _LOGO_W = 56
    _LOGO_H = 36

    # Map theme -> filename to look for next to the GUI.
    _HEADER_IMAGES = {
        "color": "color.png",
        "dark":  "dark.png",
        "light": "light.png",
    }

    def _load_header_image(self, target_w, target_h):
        """Return a PIL-backed PhotoImage for the active theme's header art,
        or None if the file is missing / unreadable / Pillow unavailable.
        Result is cached on the instance so toggle/resize doesn't re-decode."""
        if not _TRAY_AVAILABLE:   # PIL is the gate; tray import covers it
            return None
        fname = self._HEADER_IMAGES.get(getattr(self, "theme_mode", "color"))
        if not fname:
            return None
        path = os.path.join(BASE_DIR, fname)
        if not os.path.exists(path):
            return None

        cache = getattr(self, "_header_img_cache", {})
        key = (path, target_w, target_h)
        if key in cache:
            return cache[key]

        try:
            from PIL import Image as _PILImage, ImageTk as _PILImageTk
            img = _PILImage.open(path).convert("RGBA")
            # Cover-fit: scale so image fills the header strip horizontally,
            # preserving aspect ratio. If taller than the strip, center-crop.
            scale = target_w / img.width
            new_w = target_w
            new_h = max(1, int(img.height * scale))
            img = img.resize((new_w, new_h), _PILImage.LANCZOS)
            if new_h > target_h:
                top = (new_h - target_h) // 2
                img = img.crop((0, top, new_w, top + target_h))
            elif new_h < target_h:
                # Pad the rest with the active header bg color.
                bg = _PILImage.new("RGBA", (target_w, target_h),
                                   self._hex_to_rgb(BG_HEADER) + (255,))
                bg.paste(img, (0, (target_h - new_h) // 2), img)
                img = bg
            photo = _PILImageTk.PhotoImage(img)
            cache[key] = photo
            self._header_img_cache = cache
            return photo
        except Exception:
            return None

    @staticmethod
    def _hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def _build_header(self):
        HEADER_H = 64
        # Use a single Canvas for the whole strip so we can paint an optional
        # background image and overlay the logo + title cleanly. The toggle
        # buttons are real Tk widgets embedded via create_window so they stay
        # clickable.
        canvas = tk.Canvas(
            self.root, height=HEADER_H, bg=BG_HEADER,
            highlightthickness=0, bd=0,
        )
        canvas.pack(fill="x")
        self._header_canvas = canvas

        # Reserve a slim accent line at the very top.
        canvas.create_rectangle(0, 0, 9999, 2, fill=ACCENT_RED, outline="",
                                tags=("header_static",))

        # Defer image + content layout to a function we can re-run on resize
        # so the image always covers the full window width.
        def _paint(event=None):
            w = canvas.winfo_width()
            if w <= 1:
                return
            canvas.delete("all")
            # Optional background image first.
            photo = self._load_header_image(w, HEADER_H)
            if photo is not None:
                canvas.create_image(0, 0, image=photo, anchor="nw")
                # Hold a reference so Tk's GC doesn't drop it.
                self._header_photo = photo
            # Top accent line on top of the image.
            canvas.create_rectangle(0, 0, w, 2, fill=ACCENT_RED, outline="")

            # Logo: draw onto the same canvas at fixed offset.
            self._draw_logo_on(canvas, x0=14, y0=(HEADER_H - self._LOGO_H) // 2 + 1)

            # Title + subtitle text via create_text (transparent bg).
            text_x = 14 + self._LOGO_W + 10
            canvas.create_text(
                text_x, HEADER_H // 2 - 8,
                text="VR Head Tracking GUI", anchor="w",
                fill=TEXT_HEAD, font=("Segoe UI Semibold", 12),
            )
            canvas.create_text(
                text_x, HEADER_H // 2 + 10,
                text="Configuration & Profile Manager", anchor="w",
                fill=TEXT_MUTED, font=("Segoe UI", 8),
            )

            # Embed the toggle buttons on the right.
            toggle_hover = self._theme_hover() or BORDER
            if not hasattr(self, "_layout_btn") or not self._layout_btn.winfo_exists():
                self._layout_btn = tk.Button(
                    canvas, text=self._layout_button_label(),
                    command=self.toggle_layout,
                    bg=BG_INPUT, fg=TEXT_HEAD,
                    font=("Segoe UI Semibold", 8),
                    relief="flat", borderwidth=0, cursor="hand2",
                    activebackground=toggle_hover, activeforeground=TEXT_HEAD,
                    padx=10, pady=4,
                )
                _hover(self._layout_btn, BG_INPUT, toggle_hover)
                self._theme_btn = tk.Button(
                    canvas, text=self._theme_button_label(),
                    command=self.toggle_theme,
                    bg=BG_INPUT, fg=TEXT_HEAD,
                    font=("Segoe UI Semibold", 8),
                    relief="flat", borderwidth=0, cursor="hand2",
                    activebackground=toggle_hover, activeforeground=TEXT_HEAD,
                    padx=10, pady=4,
                )
                _hover(self._theme_btn, BG_INPUT, toggle_hover)
            # Position buttons via create_window from the right edge.
            canvas.create_window(w - 14, HEADER_H // 2,
                                 anchor="e", window=self._layout_btn)
            canvas.update_idletasks()
            layout_w = self._layout_btn.winfo_reqwidth()
            canvas.create_window(w - 14 - layout_w - 6, HEADER_H // 2,
                                 anchor="e", window=self._theme_btn)

        canvas.bind("<Configure>", _paint)
        # First paint will fire from the Configure event once Tk maps the canvas.

        tk.Frame(self.root, bg=BORDER, height=1).pack(fill="x")

    def _layout_button_label(self):
        # Show what the press WILL DO (i.e. the target orientation), with arrows.
        if getattr(self, "layout_mode", "vertical") == "vertical":
            return "⇄  Horizontal"
        return "⇅  Vertical"

    # Theme cycle order: color -> dark -> light -> color ...
    _THEME_ORDER = ("color", "dark", "light")

    def _next_theme(self):
        cur = getattr(self, "theme_mode", "color")
        try:
            idx = self._THEME_ORDER.index(cur)
        except ValueError:
            idx = 0
        return self._THEME_ORDER[(idx + 1) % len(self._THEME_ORDER)]

    def _theme_button_label(self):
        # Show what the press WILL DO (target theme).
        target = self._next_theme()
        return {
            "color": "◑  Color",
            "dark":  "◐  Dark",
            "light": "○  Light",
        }.get(target, "◑  Color")

    def _theme_hover(self):
        """Hover accent color for buttons / hotkey square / slider thumb,
        keyed by active theme. None means 'use the default per-widget color'."""
        return {
            "dark":  "#388bfd",   # blue
            "light": "#06b6d4",   # cyan
        }.get(getattr(self, "theme_mode", "color"))

    def _theme_button_face(self):
        """Resting button face for monochrome themes; None to use the
        accented value (red/green/blue) supplied by the caller."""
        return {
            "dark":  "#2a2a2a",
            "light": "#e8ecf1",
        }.get(getattr(self, "theme_mode", "color"))

    def _draw_logo_on(self, c, x0=0, y0=0):
        """Paint the VR headset onto canvas `c` at the given pixel offset.
        The headset body color adapts to the active theme so it doesn't
        wash out against light backgrounds."""
        W, H = self._LOGO_W, self._LOGO_H

        # Pick a body color that has good contrast on the active header bg.
        # In light mode the header is pale, so the white headset would
        # disappear -- switch to a soft mid-grey instead.
        if BG_MAIN == "#f5f7fa":   # light mode
            BODY  = "#262c34"
            STRAP = "#525860"
            SHADE = "#0d1117"
        else:                       # color or dark
            BODY  = "#f0f6fc"
            STRAP = "#c9d1d9"
            SHADE = "#7d8590"

        def x(p): return x0 + p * W / 56.0
        def y(p): return y0 + p * H / 36.0

        # Strap band across top
        c.create_rectangle(x(10), y(2), x(46), y(6), fill=STRAP, outline="")
        c.create_rectangle(x(13), y(6), x(16), y(11), fill=STRAP, outline="")
        c.create_rectangle(x(40), y(6), x(43), y(11), fill=STRAP, outline="")

        # Headset body — pill made of left oval + filler rect + right oval
        c.create_oval(x(1), y(9), x(25), y(33), fill=BODY, outline=SHADE)
        c.create_oval(x(31), y(9), x(55), y(33), fill=BODY, outline=SHADE)
        c.create_rectangle(x(13), y(10), x(43), y(32), fill=BODY, outline="")
        # Subtle nose-bridge notch (matches the surrounding header bg).
        c.create_oval(x(23), y(28), x(33), y(36), fill=BG_HEADER, outline="")

        # Lens colors come from the COLORFUL palette directly so the logo
        # stays vibrant red+blue regardless of which theme is active.
        LENS_RED  = _PALETTE_COLOR["ACCENT_RED"]
        LENS_BLUE = _PALETTE_COLOR["ACCENT_BLUE"]

        # Left lens (red)
        c.create_oval(x(5), y(13), x(21), y(29), fill=LENS_RED, outline="")
        c.create_oval(x(8), y(15), x(11), y(18), fill="white", outline="")  # highlight

        # Right lens (blue)
        c.create_oval(x(35), y(13), x(51), y(29), fill=LENS_BLUE, outline="")
        c.create_oval(x(38), y(15), x(41), y(18), fill="white", outline="")  # highlight

    # Backwards-compatible wrapper for callers that pass a standalone canvas.
    def _draw_logo(self, c):
        self._draw_logo_on(c, x0=0, y0=0)

    def _section_card(self, accent_color, label_text):
        # In horizontal mode, sections sit side-by-side and the outer frame
        # uses fill="y" + side="left"; in vertical, the original fill="x" stack.
        parent = self._sections_container or self.root
        if self.layout_mode == "horizontal":
            outer = tk.Frame(parent, bg=BG_MAIN, padx=10, pady=8)
            outer.pack(side="left", fill="y", expand=True)
        else:
            outer = tk.Frame(parent, bg=BG_MAIN, padx=18, pady=10)
            outer.pack(fill="x")

        ring = tk.Frame(outer, bg=accent_color)
        ring.pack(fill="both", expand=True)
        gap = tk.Frame(ring, bg=BG_MAIN)
        gap.pack(fill="both", expand=True, padx=2, pady=2)
        card = tk.Frame(gap, bg=BG_CARD)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        head = tk.Frame(card, bg=accent_color, height=36)
        head.pack(fill="x", side="top")
        head.pack_propagate(False)
        tk.Label(head, text=label_text,
                 fg=TEXT_HEAD, bg=accent_color, font=FONT_SECTION
                 ).pack(side="left", padx=16, pady=6)

        content = tk.Frame(card, bg=BG_CARD)
        content.pack(fill="both", expand=True, padx=18, pady=(12, 16))
        return content

    def _option_label(self, parent, text, bullet_color=YELLOW):
        """White label preceded by a colored bullet (●)."""
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(anchor="w", pady=(8, 2))
        tk.Label(row, text="●", fg=bullet_color, bg=BG_CARD,
                 font=FONT_BULLET).pack(side="left", padx=(0, 6))
        tk.Label(row, text=text, fg=TEXT_HEAD, bg=BG_CARD,
                 font=FONT_LABEL).pack(side="left")

    def _slider(self, parent, var, from_, to_, step=None, fmt="{:g}",
                style="Red.Horizontal.TScale"):
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=4)

        ttk.Scale(row, from_=from_, to=to_, variable=var,
                  orient="horizontal", style=style
                  ).pack(side="left", fill="x", expand=True)

        val_lbl = tk.Label(row, text=fmt.format(var.get()),
                           fg=TEXT_HEAD, bg=BG_CARD, width=6,
                           font=FONT_LABEL, anchor="e")
        val_lbl.pack(side="right", padx=(10, 0))

        if step is not None:
            snapping = [False]
            def on_change(*_):
                if snapping[0]: return
                try: v = var.get()
                except Exception: return
                snapped = round(v / step) * step
                if abs(snapped - v) > 1e-6:
                    snapping[0] = True
                    var.set(snapped)
                    snapping[0] = False
                val_lbl.config(text=fmt.format(var.get()))
            var.trace_add("write", on_change)
        else:
            var.trace_add("write",
                          lambda *_: val_lbl.config(text=fmt.format(var.get())))

    def _btn(self, parent, text, command, bg, hover_bg, side="left", width=12):
        # In monochrome themes (dark/light) all accented buttons collapse to
        # a uniform face. Hover uses the theme accent (blue for dark,
        # cyan for light) so the user gets a clear interaction cue.
        face = self._theme_button_face()
        hover = self._theme_hover()
        if face is not None:
            bg = face
        if hover is not None:
            hover_bg = hover
        # Pick legible text color — light mode needs black on the pale face.
        fg = "black" if self.theme_mode == "light" else "white"
        b = tk.Button(parent, text=text, command=command,
                      bg=bg, fg=fg, font=FONT_BTN, width=width,
                      relief="flat", borderwidth=0, cursor="hand2",
                      activebackground=hover_bg, activeforeground="white",
                      pady=6)
        b.pack(side=side, padx=2)
        _hover(b, bg, hover_bg)
        return b

    def _build_mouse_section(self):
        c = self._section_card(ACCENT_RED, "MOUSE EMULATION")

        self.mouse_sens_val = tk.DoubleVar(value=500)
        self._option_label(c, "Mouse Sensitivity")
        self._slider(c, self.mouse_sens_val, 0, 2000, step=1, fmt="{:.0f}")

        row = tk.Frame(c, bg=BG_CARD)
        row.pack(fill="x", pady=(12, 0))
        self._btn(row, "APPLY & SAVE", self.save_mouse, SUCCESS, "#2ea043", "left", 14)
        self._btn(row, "STOP",  self.stop_bat, DANGER, "#da3633", "right", 10)
        self._btn(row, "START", lambda: self.run_profile(PROFILE_MOUSE),
                  INFO, "#388bfd", "right", 10)

        self._build_hotkey_row(c, "toggle_mouse")

    def _build_joy_section(self):
        c = self._section_card(ACCENT_BLUE, "JOYSTICK EMULATION")

        self._option_label(c, "Sensitivity Curve")
        self.curve_var = tk.StringVar(value="Linear (Mouse-like)")
        ttk.Combobox(
            c, textvariable=self.curve_var, state="readonly",
            values=list(self.curve_options.keys()),
            style="Dark.TCombobox", font=FONT_LABEL,
        ).pack(fill="x", pady=4)

        self._option_label(c, "Max Angle  (lower = more responsive  /  5–180°)")
        self.joy_sens_val = tk.DoubleVar(value=15)
        self._slider(c, self.joy_sens_val, 5, 180, step=1, fmt="{:.0f}")

        self._option_label(c, "Deadzone  (degrees ignored / suppresses tremor  /  0.0–20.0)")
        self.joy_dz_val = tk.DoubleVar(value=1.5)
        self._slider(c, self.joy_dz_val, 0.0, 20.0, step=0.5, fmt="{:.1f}")

        # Disable Deadzone row -- checkbox + RED bullet + white text
        self.joy_dz_disabled = tk.BooleanVar(value=False)
        dz_row = tk.Frame(c, bg=BG_CARD)
        dz_row.pack(anchor="w", pady=(2, 6))

        tk.Checkbutton(
            dz_row, text="", variable=self.joy_dz_disabled,
            bg=BG_CARD, selectcolor=BG_CARD,
            activebackground=BG_CARD, activeforeground=TEXT_HEAD,
            relief="flat", borderwidth=0, cursor="hand2",
        ).pack(side="left")

        red_bullet = tk.Label(dz_row, text="●", fg=ACCENT_RED, bg=BG_CARD,
                              font=FONT_BULLET, cursor="hand2")
        red_bullet.pack(side="left", padx=(2, 6))

        dz_text = tk.Label(dz_row, text="Disable Deadzone (comment out line)",
                           fg=TEXT_HEAD, bg=BG_CARD, font=FONT_LABEL, cursor="hand2")
        dz_text.pack(side="left")

        # Click on bullet/text also toggles the checkbox
        def _toggle(*_):
            self.joy_dz_disabled.set(not self.joy_dz_disabled.get())
        red_bullet.bind("<Button-1>", _toggle)
        dz_text.bind("<Button-1>", _toggle)

        self._option_label(c, "Output Scale  (stick output multiplier  /  0.2–3.0)")
        self.joy_scale_val = tk.DoubleVar(value=1.0)
        self._slider(c, self.joy_scale_val, 0.2, 3.0, step=0.05, fmt="{:.2f}")

        row = tk.Frame(c, bg=BG_CARD)
        row.pack(fill="x", pady=(12, 0))
        self._btn(row, "APPLY & SAVE", self.save_joy, SUCCESS, "#2ea043", "left", 14)
        self._btn(row, "STOP",  self.stop_bat, DANGER, "#da3633", "right", 10)
        self._btn(row, "START", lambda: self.run_profile(PROFILE_JOY),
                  INFO, "#388bfd", "right", 10)

        self._build_hotkey_row(c, "toggle_joy")

    def _build_sixdof_section(self):
        c = self._section_card(ACCENT_PURPLE, "6DOF HEADTRACKING MOD")

        # Smaller clickable subtitle linking to the original author's GitHub.
        link_color = TEXT_BODY if self.theme_mode == "dark" else ACCENT_PURPLE
        link = tk.Label(
            c, text=SIXDOF_GITHUB_URL, fg=link_color, bg=BG_CARD,
            font=("Segoe UI", 8, "underline"), cursor="hand2",
        )
        link.pack(anchor="w", pady=(0, 6))
        link.bind("<Button-1>", lambda e: webbrowser.open(SIXDOF_GITHUB_URL))

        # ---- IP / Port row ----
        net_row = tk.Frame(c, bg=BG_CARD)
        net_row.pack(fill="x", pady=(2, 6))

        # IP block
        ip_block = tk.Frame(net_row, bg=BG_CARD)
        ip_block.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Label(ip_block, text="IP Address",
                 fg=TEXT_HEAD, bg=BG_CARD, font=FONT_LABEL
                 ).pack(anchor="w")
        self.sixdof_ip_var = tk.StringVar(value="127.0.0.1")
        tk.Entry(
            ip_block, textvariable=self.sixdof_ip_var,
            bg=BG_INPUT, fg=TEXT_HEAD, insertbackground=TEXT_HEAD,
            relief="flat", borderwidth=1, font=FONT_LABEL,
            highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT_PURPLE,
        ).pack(fill="x", ipady=4)

        # Port block (smaller)
        port_block = tk.Frame(net_row, bg=BG_CARD)
        port_block.pack(side="left")
        tk.Label(port_block, text="Port",
                 fg=TEXT_HEAD, bg=BG_CARD, font=FONT_LABEL
                 ).pack(anchor="w")
        self.sixdof_port_var = tk.StringVar(value="4242")
        tk.Entry(
            port_block, textvariable=self.sixdof_port_var,
            bg=BG_INPUT, fg=TEXT_HEAD, insertbackground=TEXT_HEAD,
            relief="flat", borderwidth=1, font=FONT_LABEL, width=8,
            highlightthickness=1,
            highlightbackground=BORDER, highlightcolor=ACCENT_PURPLE,
            justify="center",
        ).pack(ipady=4)

        # ---- Rotation gains (Yaw / Pitch / Roll) ----
        self._option_label(c, "Rotation Gains  (multipliers, 0.0–5.0)")
        self.sixdof_yaw_val   = tk.DoubleVar(value=1.0)
        self.sixdof_pitch_val = tk.DoubleVar(value=1.0)
        self.sixdof_roll_val  = tk.DoubleVar(value=1.0)
        self._labeled_slider(c, "Yaw",   self.sixdof_yaw_val)
        self._labeled_slider(c, "Pitch", self.sixdof_pitch_val)
        self._labeled_slider(c, "Roll",  self.sixdof_roll_val)

        # ---- Position gains (X / Y / Z) ----
        self._option_label(c, "Position Gains  (multipliers, 0.0–5.0)")
        self.sixdof_x_val = tk.DoubleVar(value=1.0)
        self.sixdof_y_val = tk.DoubleVar(value=1.0)
        self.sixdof_z_val = tk.DoubleVar(value=1.0)
        self._labeled_slider(c, "X", self.sixdof_x_val)
        self._labeled_slider(c, "Y", self.sixdof_y_val)
        self._labeled_slider(c, "Z", self.sixdof_z_val)

        # ---- Recenter delay ----
        self._option_label(c, "Recenter Delay  (seconds before zero-point capture, 0.0–5.0)")
        self.sixdof_delay_val = tk.DoubleVar(value=1.0)
        self._slider(c, self.sixdof_delay_val, 0.0, 5.0, step=0.1, fmt="{:.1f}")

        # ---- Action buttons ----
        row = tk.Frame(c, bg=BG_CARD)
        row.pack(fill="x", pady=(12, 0))
        self._btn(row, "APPLY & SAVE", self.save_sixdof, SUCCESS, "#2ea043", "left", 14)
        self._btn(row, "STOP",  self.stop_bat, DANGER, "#da3633", "right", 10)
        self._btn(row, "START", lambda: self.run_profile(PROFILE_6DOF),
                  INFO, "#388bfd", "right", 10)

        self._build_hotkey_row(c, "toggle_6dof")

    def _labeled_slider(self, parent, label_text, var):
        """Compact 'Yaw  [====slider====]  1.0' row used by the 6DOF section."""
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=2)

        tk.Label(row, text=label_text, fg=TEXT_BODY, bg=BG_CARD,
                 font=FONT_LABEL, width=6, anchor="w"
                 ).pack(side="left")

        ttk.Scale(row, from_=0.0, to=5.0, variable=var,
                  orient="horizontal",
                  style="Red.Horizontal.TScale"
                  ).pack(side="left", fill="x", expand=True)

        val_lbl = tk.Label(row, text="{:.1f}".format(var.get()),
                           fg=TEXT_HEAD, bg=BG_CARD, width=5,
                           font=FONT_LABEL, anchor="e")
        val_lbl.pack(side="right", padx=(10, 0))

        # Snap to 0.1 steps and update the readout.
        snapping = [False]
        def on_change(*_):
            if snapping[0]:
                return
            try:
                v = var.get()
            except Exception:
                return
            snapped = round(v * 10) / 10.0
            if abs(snapped - v) > 1e-6:
                snapping[0] = True
                var.set(snapped)
                snapping[0] = False
            val_lbl.config(text="{:.1f}".format(var.get()))
        var.trace_add("write", on_change)

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=BG_HEADER, height=32)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=BORDER, height=1).pack(fill="x", side="top")

        self.status_label = tk.Label(
            bar, text="●  Ready", fg=TEXT_MUTED, bg=BG_HEADER, font=FONT_STATUS
        )
        self.status_label.pack(side="left", padx=20)
        tk.Label(bar, text="ofisare/VRCompanion",
                 fg=TEXT_MUTED, bg=BG_HEADER, font=FONT_SUB
                 ).pack(side="right", padx=20)

    # ================== HOTKEYS ==================

    def _build_hotkey_row(self, parent, toggle_name):
        """Square red-bordered hotkey button + 'Hotkey' caption, flush-left
        directly below APPLY & SAVE."""
        row = tk.Frame(parent, bg=BG_CARD)
        row.pack(fill="x", pady=(6, 0))

        entry = HotkeyEntry(
            row,
            initial=self.hotkeys.get(toggle_name, ""),
            on_change=lambda v, n=toggle_name: self._on_hotkey_change(n, v),
        )
        entry.pack(side="left")
        self._hotkey_widgets.setdefault(toggle_name, []).append(entry)

    def _load_hotkeys(self):
        defaults = {"toggle_mouse": "", "toggle_joy": "", "toggle_6dof": ""}
        try:
            with open(HOTKEYS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                # One-time migration from older start_*/stop schema.
                if "start_mouse" in data and "toggle_mouse" not in data:
                    data["toggle_mouse"] = data.get("start_mouse", "")
                if "start_joy" in data and "toggle_joy" not in data:
                    data["toggle_joy"] = data.get("start_joy", "")
                defaults.update({k: str(v or "") for k, v in data.items()
                                 if k in defaults})
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return defaults

    def _save_hotkeys(self):
        try:
            with open(HOTKEYS_PATH, "w", encoding="utf-8") as f:
                json.dump(self.hotkeys, f, indent=2)
        except Exception:
            pass

    def _load_window_geometry(self):
        """Apply saved geometry, or fall back to a default size for the layout."""
        default = ("1500x720" if getattr(self, "layout_mode", "vertical") == "horizontal"
                   else "580x1620")
        try:
            with open(WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            geom = data.get("geometry") if isinstance(data, dict) else None
            if isinstance(geom, str) and re.match(r"^\d+x\d+([+\-]\d+[+\-]\d+)?$", geom):
                self.root.geometry(geom)
                return
        except FileNotFoundError:
            pass
        except Exception:
            pass
        self.root.geometry(default)

    def _load_layout_mode(self):
        try:
            with open(WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            mode = data.get("layout_mode") if isinstance(data, dict) else None
            if mode in ("vertical", "horizontal"):
                return mode
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return "vertical"

    def _save_layout_mode(self):
        """Merge layout_mode into the existing window_state JSON."""
        try:
            data = {}
            try:
                with open(WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except FileNotFoundError:
                pass
            data["layout_mode"] = self.layout_mode
            with open(WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def toggle_theme(self):
        """Cycle through the three themes (color -> dark -> light -> color).
        Rebuilds the entire UI so all widgets pick up the new palette."""
        self.theme_mode = self._next_theme()
        palette = {
            "color": _PALETTE_COLOR,
            "dark":  _PALETTE_DARK,
            "light": _PALETTE_LIGHT,
        }.get(self.theme_mode, _PALETTE_COLOR)
        _apply_palette(palette)

        # Save geometry before tearing down so it isn't lost in the rebuild.
        try:
            self.save_window_geometry()
        except Exception:
            pass

        # Hotkey widgets get re-created on rebuild, so reset the registry.
        self._hotkey_widgets = {}

        # Tear down everything inside the root window. The Toplevel itself
        # stays, preserving WM_DELETE protocol, hotkey registrations, tray
        # icon, and running tracking processes.
        for child in list(self.root.winfo_children()):
            child.destroy()
        self._sections_container = None

        # Apply the new palette to ttk styles, then rebuild the UI tree.
        self.root.configure(bg=BG_MAIN)
        self._setup_ttk_style()
        self._build_ui()

        # Restore current values from disk so freshly-created widgets
        # show the same data as before the toggle.
        try:
            self.sync_from_files()
        except Exception:
            pass

        self._save_theme_mode()

    def _load_theme_mode(self):
        try:
            with open(WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            mode = data.get("theme_mode") if isinstance(data, dict) else None
            if mode in ("color", "dark", "light"):
                return mode
        except FileNotFoundError:
            pass
        except Exception:
            pass
        return "color"

    def _save_theme_mode(self):
        """Merge theme_mode into the existing window_state JSON."""
        try:
            data = {}
            try:
                with open(WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except FileNotFoundError:
                pass
            data["theme_mode"] = self.theme_mode
            with open(WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def save_window_geometry(self):
        """Persist current window position + size (preserves layout_mode)."""
        try:
            geom = self.root.geometry()  # 'WxH+X+Y'
            data = {}
            try:
                with open(WINDOW_STATE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    data = loaded
            except FileNotFoundError:
                pass
            data["geometry"] = geom
            data["layout_mode"] = getattr(self, "layout_mode", "vertical")
            with open(WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    # ================== TRAY LIFECYCLE ==================

    def _watch_minimize(self):
        """Poll window state every 200ms. When it transitions to iconic
        (user clicked the minimize button), redirect to tray.

        This is more reliable than binding <Unmap> — that event is noisy
        (fires for many widget changes) and on some Windows builds doesn't
        fire at all when minimizing a withdrawn-and-redeiconified window.
        """
        try:
            state = self.root.state()
        except Exception:
            # Window destroyed; stop polling.
            return

        if state == "iconic" and not self._was_iconic:
            self._was_iconic = True
            self.hide_to_tray()
        elif state == "normal":
            self._was_iconic = False

        # Reschedule.
        try:
            self.root.after(200, self._watch_minimize)
        except Exception:
            pass

    def hide_to_tray(self):
        """Save geometry, hide the window, leave hotkeys + processes running."""
        try:
            self.save_window_geometry()
        except Exception:
            pass
        try:
            # If we're being called because the user just clicked minimize,
            # the window is currently 'iconic'. Withdrawing from that state
            # works, but we explicitly normalize first so subsequent
            # deiconify() restores cleanly.
            if self.root.state() == "iconic":
                self.root.state("normal")
            self.root.withdraw()
        except Exception:
            pass

    def show_window(self):
        """Restore the window from the tray."""
        try:
            self.root.deiconify()
            self.root.state("normal")
            # Reapply saved geometry — withdraw can lose position on some builds.
            self._load_window_geometry()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(50, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
            # Reset minimize-watcher state so next minimize is detected.
            self._was_iconic = False
        except Exception:
            pass

    def quit_app(self):
        """Real shutdown — fired from the tray 'Quit' menu or when no tray."""
        try:
            self.save_window_geometry()
        except Exception:
            pass
        try:
            self.hotkey_mgr.stop()
        except Exception:
            pass
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_hotkey_change(self, name, value):
        # Detect duplicates against the OTHER bindings; refuse if conflict.
        if value:
            for other_name, other_val in self.hotkeys.items():
                if other_name != name and other_val == value:
                    # Silently revert widget(s) to old value.
                    for w in self._hotkey_widgets.get(name, []):
                        w.set(self.hotkeys[name])
                    try:
                        self.status_label.config(
                            text=f"●  Hotkey '{value}' already in use",
                            fg=DANGER)
                    except Exception:
                        pass
                    return

        self.hotkeys[name] = value
        # Sync sibling widgets (the 'stop' field appears in both sections).
        for w in self._hotkey_widgets.get(name, []):
            if w.get() != value:
                w.set(value)
        self._save_hotkeys()
        self._refresh_hotkeys()

    def _refresh_hotkeys(self):
        callbacks = {
            "toggle_mouse": lambda: self.toggle_profile(PROFILE_MOUSE),
            "toggle_joy":   lambda: self.toggle_profile(PROFILE_JOY),
            "toggle_6dof":  lambda: self.toggle_profile(PROFILE_6DOF),
        }
        try:
            self.hotkey_mgr.update(self.hotkeys, callbacks)
        except Exception as e:
            self._log_error("refresh_hotkeys", e)

    # ================== ACTIONS ==================

    def _resolve_freepie(self):
        """Return absolute path to FreePIE.Console.exe, or None if missing."""
        candidates = [
            os.path.join(BASE_DIR, FREEPIE_EXE),
            r"C:\Program Files (x86)\FreePIE\FreePIE.Console.exe",
            r"C:\Program Files\FreePIE\FreePIE.Console.exe",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        from shutil import which
        return which(FREEPIE_EXE)

    def _log_error(self, where, exc):
        """Write full traceback to launch_error.log next to the GUI."""
        log_path = os.path.join(BASE_DIR, "launch_error.log")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- {where} ---\n")
                traceback.print_exc(file=f)
        except Exception:
            pass

    def run_profile(self, profile):
        """Launch FreePIE.Console.exe directly with the given profile, hidden."""
        exe = self._resolve_freepie()
        if exe is None:
            self.status_label.config(
                text="●  FreePIE.Console.exe not found", fg=DANGER)
            return
        if not os.path.exists(VR_COMPANION_PY):
            self.status_label.config(
                text="●  vr_companion.py not found", fg=DANGER)
            return

        existing = self.processes.get(profile)
        if existing is not None and existing.poll() is None:
            self.status_label.config(
                text=f"●  Already running: {profile}", fg=INFO)
            return

        try:
            # Give FreePIE its own console (it needs one to function properly,
            # same as the .bat's `start /min` did) but hide that console window.
            # Do NOT redirect stdio — FreePIE may read stdin and would exit on EOF.
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            si.wShowWindow = subprocess.SW_HIDE

            proc = subprocess.Popen(
                [exe, VR_COMPANION_PY, profile],
                cwd=BASE_DIR,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
                startupinfo=si,
            )
            self.processes[profile] = proc
            self.status_label.config(text=f"●  Started: {profile}", fg=INFO)
            _play_tracking_sound(starting=True)
        except Exception as e:
            self.status_label.config(
                text=f"●  Launch failed: {type(e).__name__}", fg=DANGER)
            self._log_error(f"run_profile({profile})", e)

    def toggle_profile(self, profile):
        """Hotkey handler: stop the profile if it's running, otherwise start it.
        Unlike stop_bat, this only stops the matching profile — it leaves any
        other running profile alone."""
        proc = self.processes.get(profile)
        if proc is not None and proc.poll() is None:
            try:
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                    capture_output=True, creationflags=CREATE_NO_WINDOW,
                )
            except Exception:
                pass
            self.processes.pop(profile, None)
            self.status_label.config(text=f"●  Stopped: {profile}", fg=DANGER)
            _play_tracking_sound(starting=False)
        else:
            self.run_profile(profile)

    def stop_bat(self):
        # Track whether we actually killed something so we only beep when
        # the button did real work (avoids a "stop" chirp when nothing's running).
        killed_any = False

        # 1) Kill each tracked FreePIE process tree by PID.
        for key, proc in list(self.processes.items()):
            if proc is not None and proc.poll() is None:
                try:
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                        capture_output=True, creationflags=CREATE_NO_WINDOW,
                    )
                    killed_any = True
                except Exception:
                    pass
            self.processes.pop(key, None)

        # 2) Safety net: kill any FreePIE instance the user may have started
        #    outside the GUI (or older zombies from previous sessions).
        for image in ("FreePIE.Console.exe", "FreePIE.exe", "FreePIE64.exe"):
            try:
                result = subprocess.run(
                    ['taskkill', '/F', '/IM', image],
                    capture_output=True, creationflags=CREATE_NO_WINDOW)
                # taskkill returns 0 only when something matched and was killed.
                if result.returncode == 0:
                    killed_any = True
            except Exception:
                pass

        self.status_label.config(text="●  All scripts stopped", fg=DANGER)
        if killed_any:
            _play_tracking_sound(starting=False)

    @staticmethod
    def _fmt(v):
        return "{:g}".format(float(v))

    def sync_from_files(self):
        if os.path.exists(MOUSE_SCRIPT_PATH):
            with open(MOUSE_SCRIPT_PATH, "r") as f:
                c = f.read()
                m = re.search(r"mouseSensitivityX\s*=\s*(\d+)", c)
                if m: self.mouse_sens_val.set(int(m.group(1)))

        if os.path.exists(JOY_SCRIPT_PATH):
            with open(JOY_SCRIPT_PATH, "r") as f:
                c = f.read()

            m = re.search(r"(?m)^(\s*)(#?)\s*deadzone\s*=\s*([\d.]+)", c)
            if m:
                _, comment, val = m.groups()
                self.joy_dz_disabled.set(comment == "#")
                self.joy_dz_val.set(float(val))

            m = re.search(r"(?m)^(\s*)(#?)\s*exponent\s*=\s*([\d.]+)", c)
            if m:
                _, comment, val = m.groups()
                if comment == "#":
                    self.curve_var.set(CURVE_OFF_LABEL)
                else:
                    v = float(val)
                    best_lbl, best_d = "Linear (Mouse-like)", 1e9
                    for lbl, preset in self.curve_options.items():
                        if preset is None: continue
                        d = abs(preset - v)
                        if d < best_d:
                            best_d, best_lbl = d, lbl
                    self.curve_var.set(best_lbl)

            m = re.search(r"(?m)^\s*maxAngle\s*=\s*([\d.]+)", c)
            if m: self.joy_sens_val.set(float(m.group(1)))

            m = re.search(r"(?m)^\s*scale\s*=\s*([\d.]+)", c)
            if m: self.joy_scale_val.set(float(m.group(1)))

        if os.path.exists(SIXDOF_SCRIPT_PATH):
            with open(SIXDOF_SCRIPT_PATH, "r") as f:
                c = f.read()

            m = re.search(r'(?m)^\s*IP_ADDRESS\s*=\s*"([^"]*)"', c)
            if m: self.sixdof_ip_var.set(m.group(1))

            m = re.search(r"(?m)^\s*PORT\s*=\s*(\d+)", c)
            if m: self.sixdof_port_var.set(m.group(1))

            gains_to_vars = {
                "YAW_GAIN":   self.sixdof_yaw_val,
                "PITCH_GAIN": self.sixdof_pitch_val,
                "ROLL_GAIN":  self.sixdof_roll_val,
                "X_GAIN":     self.sixdof_x_val,
                "Y_GAIN":     self.sixdof_y_val,
                "Z_GAIN":     self.sixdof_z_val,
            }
            for name, var in gains_to_vars.items():
                v = self._sixdof_lookup_constant(c, name)
                if v is not None:
                    try:
                        # Clamp to slider range (0–5) so out-of-range values
                        # in the file don't break the UI.
                        v = max(0.0, min(5.0, float(v)))
                        var.set(v)
                    except Exception:
                        pass

            v = self._sixdof_lookup_constant(c, "RECENTER_DELAY_SEC")
            if v is not None:
                try:
                    self.sixdof_delay_val.set(max(0.0, min(5.0, float(v))))
                except Exception:
                    pass

    def _sixdof_lookup_constant(self, content, name):
        """Return the float-value-string for `name`, whether it appears
        on its own line or in a tuple assignment. None if not found."""
        # Plain line first.
        m = re.search(r"(?m)^\s*" + name + r"\s*=\s*([\d.]+)\s*$", content)
        if m:
            return m.group(1)
        # Tuple-assignment form: scan each line, find one that contains
        # `name` on the LHS, then pick the matching position on the RHS.
        tup_re = re.compile(
            r"^(\s*)([A-Z_][A-Z0-9_]*(?:\s*,\s*[A-Z_][A-Z0-9_]*)+)\s*=\s*"
            r"([^\n#]+?)(\s*(?:#.*)?)$"
        )
        for line in content.splitlines():
            m = tup_re.match(line)
            if not m:
                continue
            names = [n.strip() for n in m.group(2).split(",")]
            vals  = [v.strip() for v in m.group(3).split(",")]
            if len(names) != len(vals):
                continue
            if name in names:
                return vals[names.index(name)]
        return None

    def save_mouse(self):
        try:
            with open(MOUSE_SCRIPT_PATH, "r") as f: c = f.read()
            v = int(self.mouse_sens_val.get())
            c = re.sub(r"(mouseSensitivity[XY]\s*=\s*)\d+", rf"\g<1>{v}", c)
            with open(MOUSE_SCRIPT_PATH, "w") as f: f.write(c)
            self.status_label.config(text="●  Mouse applied", fg=SUCCESS)
        except Exception:
            self.status_label.config(text="●  Mouse save failed", fg=DANGER)

    def save_joy(self):
        try:
            with open(JOY_SCRIPT_PATH, "r") as f: content = f.read()

            dz_val    = self.joy_dz_val.get()
            mx_val    = int(self.joy_sens_val.get())
            scl_val   = self.joy_scale_val.get()
            dz_off    = self.joy_dz_disabled.get()
            curve_lbl = self.curve_var.get()
            curve_off = (curve_lbl == CURVE_OFF_LABEL)
            exp_val   = self.curve_options.get(curve_lbl) if not curve_off else 0

            dz_prefix = "# " if dz_off else ""
            content = re.sub(
                r"(?m)^(\s*)#?\s*deadzone\s*=\s*[\d.]+",
                lambda m: "{0}{1}deadzone = {2}".format(m.group(1), dz_prefix, self._fmt(dz_val)),
                content
            )

            exp_prefix = "# " if curve_off else ""
            content = re.sub(
                r"(?m)^(\s*)#?\s*exponent\s*=\s*[\d.]+",
                lambda m: "{0}{1}exponent = {2}".format(m.group(1), exp_prefix, self._fmt(exp_val if exp_val is not None else 0)),
                content
            )

            content = re.sub(
                r"(?m)^(\s*)maxAngle\s*=\s*[\d.]+",
                lambda m: "{0}maxAngle = {1}".format(m.group(1), self._fmt(mx_val)),
                content
            )

            content = re.sub(
                r"(?m)^(\s*)scale(\s*)=\s*[\d.]+",
                lambda m: "{0}scale{1}= {2}".format(m.group(1), m.group(2), self._fmt(scl_val)),
                content
            )

            with open(JOY_SCRIPT_PATH, "w") as f: f.write(content)
            self.status_label.config(text="●  Joystick applied", fg=SUCCESS)
        except Exception:
            self.status_label.config(text="●  Joystick save failed", fg=DANGER)

    def save_sixdof(self):
        """Patch IP, port, gains, and recenter delay in 6DOFtoUDP.py.

        Handles BOTH the older one-name-per-line format
            YAW_GAIN = 1.0
        AND the newer tuple-assignment format
            YAW_GAIN, PITCH_GAIN, ROLL_GAIN = 1.0, 1.0, 1.0
        """
        try:
            if not os.path.exists(SIXDOF_SCRIPT_PATH):
                self.status_label.config(
                    text="●  6DOFtoUDP.py not found", fg=DANGER)
                return
            with open(SIXDOF_SCRIPT_PATH, "r") as f:
                content = f.read()

            # ---- Validate IP / Port ----
            ip = self.sixdof_ip_var.get().strip()
            port_s = self.sixdof_port_var.get().strip()
            if not ip:
                self.status_label.config(text="●  IP cannot be empty", fg=DANGER)
                return
            try:
                port = int(port_s)
                if not (1 <= port <= 65535):
                    raise ValueError
            except Exception:
                self.status_label.config(
                    text="●  Port must be 1–65535", fg=DANGER)
                return

            # ---- Patch IP / Port (top-of-file constants) ----
            content = re.sub(
                r'(?m)^(\s*IP_ADDRESS\s*=\s*)"[^"]*"',
                lambda m: '{0}"{1}"'.format(m.group(1), ip),
                content,
            )
            content = re.sub(
                r"(?m)^(\s*PORT\s*=\s*)\d+",
                lambda m: "{0}{1}".format(m.group(1), port),
                content,
            )

            # ---- Patch gain constants (handles both formats) ----
            gain_values = {
                "YAW_GAIN":   self.sixdof_yaw_val.get(),
                "PITCH_GAIN": self.sixdof_pitch_val.get(),
                "ROLL_GAIN":  self.sixdof_roll_val.get(),
                "X_GAIN":     self.sixdof_x_val.get(),
                "Y_GAIN":     self.sixdof_y_val.get(),
                "Z_GAIN":     self.sixdof_z_val.get(),
            }
            content = self._sixdof_patch_constants(content, gain_values)

            # ---- Recenter delay (always its own line in both formats) ----
            content = re.sub(
                r"(?m)^(\s*RECENTER_DELAY_SEC\s*=\s*)[\d.]+",
                lambda m: "{0}{1}".format(m.group(1),
                                          self._fmt(self.sixdof_delay_val.get())),
                content,
            )

            with open(SIXDOF_SCRIPT_PATH, "w") as f:
                f.write(content)
            self.status_label.config(text="●  6DOF applied", fg=SUCCESS)
        except Exception:
            self.status_label.config(text="●  6DOF save failed", fg=DANGER)

    def _sixdof_patch_constants(self, content, values):
        """Update constants in `content` regardless of whether they're written
        one-per-line or as tuple assignments. `values` maps NAME -> new float."""
        # First pass: handle tuple-style assignments line by line. We iterate
        # the file by lines (preserving trailing newlines) so we only rewrite
        # whole lines that match the comma-separated-LHS pattern.
        lines = content.splitlines(keepends=True)
        # Pattern: optional indent, NAME (, NAME)+ = value (, value)+ optional trailing junk.
        tup_re = re.compile(
            r"^(\s*)([A-Z_][A-Z0-9_]*(?:\s*,\s*[A-Z_][A-Z0-9_]*)+)\s*=\s*"
            r"([^\n#]+?)(\s*(?:#.*)?)$"
        )
        for i, line in enumerate(lines):
            m = tup_re.match(line.rstrip("\r\n"))
            if not m:
                continue
            indent, names_part, vals_part, tail = m.groups()
            names = [n.strip() for n in names_part.split(",")]
            vals  = [v.strip() for v in vals_part.split(",")]
            if len(names) != len(vals):
                continue
            # Only rewrite if at least one of OUR target names is on this line.
            if not any(n in values for n in names):
                continue
            new_vals = []
            for n, v in zip(names, vals):
                if n in values:
                    new_vals.append(self._fmt(values[n]))
                else:
                    new_vals.append(v)
            # Preserve trailing newline.
            ending = "\n" if line.endswith("\n") else ""
            if line.endswith("\r\n"):
                ending = "\r\n"
            lines[i] = "{0}{1} = {2}{3}{4}".format(
                indent, ", ".join(names), ", ".join(new_vals), tail, ending)
        content = "".join(lines)

        # Second pass: handle plain `NAME = value` lines for any constants
        # that DIDN'T appear in a tuple assignment above. The tuple pass
        # already updated those, so a one-per-line regex here is a safe no-op
        # for anything we already changed.
        for name, val in values.items():
            content = re.sub(
                r"(?m)^(\s*" + name + r"\s*=\s*)[\d.]+\s*$",
                lambda m, v=val: "{0}{1}".format(m.group(1), self._fmt(v)),
                content,
            )
        return content


if __name__ == "__main__":
    # FreePIE.Console.exe requires admin (WinError 740 from CreateProcess otherwise).
    # Elevate the whole GUI once so all subsequent subprocess.Popen calls inherit
    # admin rights and work without further UAC prompts.
    def _is_admin():
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False

    if not _is_admin():
        # Re-launch this script elevated, then exit the non-elevated copy.
        params = " ".join(f'"{a}"' for a in sys.argv)
        # SW_SHOWNORMAL = 1 ; "runas" verb triggers UAC.
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, f'"{__file__}" {params}', None, 1
        )
        sys.exit(0)

    root = tk.Tk()
    app = VRHeadTrackingGUI(root)
    root.mainloop()

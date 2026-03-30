from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical modifier order
# ---------------------------------------------------------------------------

MODIFIER_ORDER = ["ctrl", "opt", "shift", "cmd", "fn", "hyper"]

# ---------------------------------------------------------------------------
# BTT bitmask constants
# ---------------------------------------------------------------------------

BTT_SHIFT = 1 << 17   # 131072
BTT_CTRL  = 1 << 18   # 262144
BTT_OPT   = 1 << 19   # 524288
BTT_CMD   = 1 << 20   # 1048576
BTT_FN    = 1 << 23   # 8388608

# ---------------------------------------------------------------------------
# macOS virtual keycode table
# ---------------------------------------------------------------------------

KEYCODE_TABLE: dict[int, str] = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g",
    6: "z", 7: "x", 8: "c", 9: "v", 11: "b",
    12: "q", 13: "w", 14: "e", 15: "r", 16: "y", 17: "t",
    18: "1", 19: "2", 20: "3", 21: "4", 22: "6", 23: "5",
    24: "=", 25: "9", 26: "7", 27: "-", 28: "8", 29: "0",
    30: "]", 31: "o", 32: "u", 33: "[", 34: "i", 35: "p",
    36: "return", 37: "l", 38: "j", 39: "'", 40: "k", 41: ";",
    42: "\\", 43: ",", 44: "/", 45: "n", 46: "m", 47: ".",
    48: "tab", 49: "space", 50: "`", 51: "delete", 53: "escape",
    96: "f5", 97: "f6", 98: "f7", 99: "f3", 100: "f8", 101: "f9",
    103: "f11", 105: "f13", 107: "f14", 109: "f10", 111: "f12",
    113: "f15", 114: "help", 115: "home", 116: "pageup",
    117: "forward_delete", 118: "f4", 119: "end", 120: "f2",
    121: "pagedown", 122: "f1", 123: "left", 124: "right",
    125: "down", 126: "up",
}

# ---------------------------------------------------------------------------
# Raw → canonical modifier name maps per tool
# ---------------------------------------------------------------------------

_KARABINER_MAP: dict[str, str] = {
    "left_command": "cmd",   "right_command": "cmd",
    "left_option":  "opt",   "right_option":  "opt",
    "left_shift":   "shift", "right_shift":   "shift",
    "left_control": "ctrl",  "right_control": "ctrl",
    "fn":           "fn",
    "command":      "cmd",   "option": "opt",
    "shift":        "shift", "control": "ctrl",
}

_HOMEROW_MAP: dict[str, str] = {
    "⌃": "ctrl",
    "⌥": "opt",
    "⇧": "shift",
    "⌘": "cmd",
}

_GENERIC_MAP: dict[str, str] = {
    "ctrl":    "ctrl", "control": "ctrl", "ctl": "ctrl",
    "opt":     "opt",  "option":  "opt",  "alt": "opt",
    "shift":   "shift",
    "cmd":     "cmd",  "command": "cmd",  "super": "cmd",
    "fn":      "fn",
    "hyper":   "hyper",
}


def normalize_modifier(raw: str) -> str:
    """Map any modifier string to normalized form."""
    raw = raw.strip()
    lowered = raw.lower()

    if lowered in _GENERIC_MAP:
        return _GENERIC_MAP[lowered]
    if lowered in _KARABINER_MAP:
        return _KARABINER_MAP[lowered]
    if raw in _HOMEROW_MAP:
        return _HOMEROW_MAP[raw]

    raise ValueError(f"Unknown modifier: {raw!r}")


# ---------------------------------------------------------------------------
# Modifier sorting / collapsing
# ---------------------------------------------------------------------------

def _sort_modifiers(mods: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for m in mods:
        seen[m] = None
    return [m for m in MODIFIER_ORDER if m in seen]


def _collapse_hyper(mods: list[str]) -> list[str]:
    hyper_set = {"ctrl", "opt", "shift", "cmd"}
    if hyper_set.issubset(set(mods)):
        remaining = [m for m in mods if m not in hyper_set]
        remaining.append("hyper")
        return _sort_modifiers(remaining)
    return mods


def _build_combo(mods: list[str], key: str) -> str:
    mods = _collapse_hyper(_sort_modifiers(mods))
    parts = mods + [key]
    return "+".join(parts)


# ---------------------------------------------------------------------------
# BTT helpers
# ---------------------------------------------------------------------------

def decode_btt_modifiers(bitmask: int) -> list[str]:
    """Decode a BTT modifier bitmask into a sorted list of canonical modifiers."""
    mods: list[str] = []
    if bitmask & BTT_CTRL:
        mods.append("ctrl")
    if bitmask & BTT_OPT:
        mods.append("opt")
    if bitmask & BTT_SHIFT:
        mods.append("shift")
    if bitmask & BTT_CMD:
        mods.append("cmd")
    if bitmask & BTT_FN:
        mods.append("fn")
    return _collapse_hyper(_sort_modifiers(mods))


def btt_keycode_to_char(keycode: int) -> str:
    """Convert a macOS virtual keycode to a character/name string."""
    if keycode not in KEYCODE_TABLE:
        raise ValueError(f"Unknown macOS virtual keycode: {keycode}")
    return KEYCODE_TABLE[keycode]


# ---------------------------------------------------------------------------
# Per-style combo parsers
# ---------------------------------------------------------------------------

def _normalize_karabiner(key_code: str, modifiers: list[str]) -> str:
    norm_mods = [_KARABINER_MAP.get(m.lower(), normalize_modifier(m)) for m in modifiers]
    return _build_combo(norm_mods, key_code.lower())


def _normalize_tmux(raw: str) -> str:
    """Parse tmux key notation like C-h, M-Up, prefix p."""
    raw = raw.strip()

    # Preserve prefix notation as-is (just normalize the trailing key).
    if raw.lower().startswith("prefix "):
        rest = raw[len("prefix "):]
        return "prefix " + rest.strip().lower()

    mods: list[str] = []
    token = raw

    while True:
        upper = token.upper()
        if upper.startswith("C-"):
            mods.append("ctrl")
            token = token[2:]
        elif upper.startswith("M-"):
            mods.append("opt")
            token = token[2:]
        elif upper.startswith("S-"):
            mods.append("shift")
            token = token[2:]
        else:
            break

    key = token.lower() if token else ""
    return _build_combo(mods, key)


def _normalize_nvim(raw: str) -> str:
    """Parse nvim key notation like <C-d>, <leader>, <M-x>."""
    raw = raw.strip()

    if raw.lower() == "<leader>":
        return "space"

    if raw.startswith("<") and raw.endswith(">"):
        inner = raw[1:-1]
        mods: list[str] = []
        while True:
            upper = inner.upper()
            if upper.startswith("C-"):
                mods.append("ctrl")
                inner = inner[2:]
            elif upper.startswith("M-") or upper.startswith("A-"):
                mods.append("opt")
                inner = inner[2:]
            elif upper.startswith("S-"):
                mods.append("shift")
                inner = inner[2:]
            elif upper.startswith("D-"):
                mods.append("cmd")
                inner = inner[2:]
            else:
                break
        key = inner.lower() if inner else ""
        return _build_combo(mods, key)

    return raw.lower()


def _normalize_zed(raw: str) -> str:
    """Parse zed notation like cmd-shift-g."""
    parts = raw.strip().split("-")
    mods: list[str] = []
    key = ""
    for part in parts:
        low = part.lower()
        if low in ("ctrl", "control"):
            mods.append("ctrl")
        elif low in ("alt", "opt", "option"):
            mods.append("opt")
        elif low == "shift":
            mods.append("shift")
        elif low in ("cmd", "command", "super"):
            mods.append("cmd")
        elif low == "fn":
            mods.append("fn")
        else:
            key = low
    return _build_combo(mods, key)


def _normalize_homerow(raw: str) -> str:
    """Parse homerow unicode notation like ⌃⌥⇧⌘F."""
    mods: list[str] = []
    key = ""
    i = 0
    while i < len(raw):
        ch = raw[i]
        if ch in _HOMEROW_MAP:
            mods.append(_HOMEROW_MAP[ch])
            i += 1
        else:
            key = raw[i:].lower()
            break
    return _build_combo(mods, key)


def _normalize_btt(keycode: int, bitmask: int) -> str:
    mods = decode_btt_modifiers(bitmask)
    key = btt_keycode_to_char(keycode)
    # mods already sorted/collapsed; just build the string directly
    parts = mods + [key]
    return "+".join(parts)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def normalize_key_combo(raw: str | int, style: str, **kwargs) -> str:
    """Normalize a full key combo to canonical form.

    style="karabiner": raw is key_code str; pass modifiers=list[str] in kwargs.
    style="btt":       raw is keycode int; pass bitmask=int in kwargs.
    style="tmux"|"nvim"|"zed"|"homerow": raw is the notation string.
    """
    if style == "karabiner":
        if not isinstance(raw, str):
            raise TypeError("karabiner style expects raw as str (key_code)")
        modifiers: list[str] = kwargs.get("modifiers", [])
        return _normalize_karabiner(raw, modifiers)

    if style == "btt":
        if not isinstance(raw, int):
            raise TypeError("btt style expects raw as int (keycode)")
        bitmask: int = kwargs["bitmask"]
        return _normalize_btt(raw, bitmask)

    if not isinstance(raw, str):
        raise TypeError(f"{style} style expects raw as str")

    if style == "tmux":
        return _normalize_tmux(raw)
    if style == "nvim":
        return _normalize_nvim(raw)
    if style == "zed":
        return _normalize_zed(raw)
    if style == "homerow":
        return _normalize_homerow(raw)

    raise ValueError(f"Unknown style: {style!r}")

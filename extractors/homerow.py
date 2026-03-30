import plistlib
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo


def extract(config: dict) -> list[Keybinding]:
    domain = config["plist_domain"]
    plist_path = Path(f"~/Library/Preferences/{domain}.plist").expanduser().resolve()

    if not plist_path.exists():
        print(f"Warning: Homerow plist not found: {plist_path}")
        return []

    try:
        with plist_path.open("rb") as f:
            data = plistlib.load(f)
    except Exception as e:
        print(f"Warning: could not read Homerow plist {plist_path}: {e}")
        return []

    shortcut_actions = [
        ("non-search-shortcut", "Homerow Labels"),
        ("scroll-shortcut", "Homerow Scroll"),
    ]

    results: list[Keybinding] = []

    for plist_key, action in shortcut_actions:
        raw = data.get(plist_key)
        if not raw:
            print(f"Warning: Homerow plist missing key {plist_key!r}")
            continue

        try:
            key = normalize_key_combo(raw, style="homerow")
        except Exception as e:
            print(f"Warning: could not normalize Homerow shortcut {raw!r}: {e}")
            continue

        results.append(Keybinding(
            tool="homerow",
            key=key,
            action=action,
            context="global",
            enabled=True,
            source_file=plist_path.name,
            raw_key=raw,
        ))

    return results

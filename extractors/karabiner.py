import json
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo


def extract(config: dict) -> list[Keybinding]:
    path = Path(config["path"]).expanduser().resolve()

    if not path.exists():
        print(f"Warning: karabiner config not found: {path}")
        return []

    with path.open() as f:
        data = json.load(f)

    source_file = str(path)
    results: list[Keybinding] = []

    try:
        profile = data["profiles"][0]
        rules = profile["complex_modifications"]["rules"]
    except (KeyError, IndexError):
        return []

    for rule in rules:
        description = rule.get("description", "")
        for manipulator in rule.get("manipulators", []):
            from_block = manipulator.get("from", {})
            mandatory = from_block.get("modifiers", {}).get("mandatory", [])

            simultaneous = from_block.get("simultaneous", [])
            if simultaneous:
                key_codes = [s["key_code"] for s in simultaneous if "key_code" in s]
                raw_key = "+".join(key_codes)
                # Normalize each key in simultaneous with the modifiers, join results
                normalized_parts = [
                    normalize_key_combo(kc, style="karabiner", modifiers=mandatory)
                    for kc in key_codes
                ]
                key = "+".join(normalized_parts)
            else:
                key_code = from_block.get("key_code")
                if not key_code:
                    continue
                raw_key = key_code
                key = normalize_key_combo(key_code, style="karabiner", modifiers=mandatory)

            results.append(Keybinding(
                tool="karabiner",
                key=key,
                action=description,
                context="global",
                enabled=True,
                source_file=source_file,
                raw_key=raw_key,
            ))

    return results

import json
import re
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo


def _strip_jsonc(text: str) -> str:
    # Strip line comments
    text = re.sub(r"//[^\n]*", "", text)
    # Strip trailing commas before ] or }
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def extract(config: dict) -> list[Keybinding]:
    path = Path(config["path"]).expanduser().resolve()

    if not path.exists():
        print(f"Warning: zed keymap not found: {path}")
        return []

    with path.open() as f:
        raw = f.read()

    data = json.loads(_strip_jsonc(raw))

    source_file = str(path)
    results: list[Keybinding] = []

    for entry in data:
        context = entry.get("context") or "global"
        bindings = entry.get("bindings", {})

        for combo, action in bindings.items():
            raw_key = combo
            key = normalize_key_combo(combo, style="zed")

            if isinstance(action, list):
                action_str = " ".join(
                    str(a) if not isinstance(a, str) else a for a in action
                )
            elif isinstance(action, dict):
                action_str = str(action)
            else:
                action_str = str(action)

            results.append(Keybinding(
                tool="zed",
                key=key,
                action=action_str,
                context=context,
                enabled=True,
                source_file=source_file,
                raw_key=raw_key,
            ))

    return results

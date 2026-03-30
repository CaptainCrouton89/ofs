from lib.keymap import Keybinding


def extract(config: dict) -> list[Keybinding]:
    manual_bindings = config.get("manual_bindings", [])

    results: list[Keybinding] = []

    for entry in manual_bindings:
        key = entry["key"]
        action = entry["action"]
        context = entry.get("context", "global")

        results.append(Keybinding(
            tool="raycast",
            key=key,
            action=action,
            context=context,
            enabled=True,
            source_file="manual",
            raw_key=key,
        ))

    return results

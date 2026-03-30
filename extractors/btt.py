import json
import sqlite3
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo

# BTT ZACTION codes → human-readable descriptions.
# Covers the most common action types; unknown codes fall back to "Action {code}".
ACTION_NAMES = {
    17: "Move Mouse",
    18: "Keyboard Shortcut",
    19: "Open App",
    20: "Open URL",
    21: "Paste Text",
    45: "Run AppleScript",
    90: "Move Window Left Half",
    91: "Move Window Right Half",
    92: "Move Window Top Half",
    93: "Move Window Bottom Half",
    94: "Open Menu Item",
    106: "Toggle App",
    108: "Open File",
    118: "Paste Custom Text",
    129: "Trigger Menubar Menu",
    151: "Move Window Left",
    152: "Move Window Right",
    165: "Run Shell Script",
    175: "Open App / Launch",
    182: "Named Trigger",
    184: "Named Trigger",
    186: "Named Trigger",
    207: "Send Keyboard Shortcut",
    208: "Send Keyboard Shortcut (sequence)",
    251: "Resize Window",
    272: "Conditional Activation",
    285: "Move Mouse to Position",
    293: "Run Shortcut",
    295: "Open URL / Web",
    384: "ChatGPT Menu",
    386: "Open ChatGPT Menu",
    449: "ChatGPT Transform",
    470: "ChatGPT",
    471: "ChatGPT with Variable",
    527: "Move to Space",
    528: "Move Window to Space",
    550: "Go to Space",
}


def _describe_action(action_code: int, action_data_text: str | None) -> str:
    """Build a human-readable description from action code + JSON data."""
    base = ACTION_NAMES.get(action_code, f"Action {action_code}")

    if not action_data_text:
        return base

    try:
        data = json.loads(action_data_text)
    except (json.JSONDecodeError, TypeError):
        return base

    # Try to extract useful details from common fields
    if action_code == 550 and "BTTActionGoToSpaceByIndex" in data:
        idx = data["BTTActionGoToSpaceByIndex"]
        return f"Go to Space {idx}"
    if action_code in (175, 19) and "BTTAppToOpen" in data:
        return f"Open {data['BTTAppToOpen']}"
    if action_code == 94 and "BTTMenuActionMenuID" in data:
        return f"Menu: {data['BTTMenuActionMenuID']}"
    if action_code == 386 and "BTTMenuActionMenuID" in data:
        return f"Menu: {data['BTTMenuActionMenuID']}"
    if action_code in (449, 470, 471) and "BTTChatGPTModelSelection" in data:
        model = data.get("BTTChatGPTModelSelection", "")
        return f"ChatGPT ({model})"

    return base


def extract(config: dict) -> list[Keybinding]:
    directory = Path(config["path"]).expanduser().resolve()
    pattern = config["db_pattern"]

    if not directory.exists():
        print(f"Warning: BTT config directory not found: {directory}")
        return []

    exclude_suffixes = ("-shm", "-wal", "_tmp_backup")
    candidates = [
        p for p in directory.glob(pattern)
        if not any(p.name.endswith(s) for s in exclude_suffixes)
    ]

    if not candidates:
        print(f"Warning: no BTT DB files found in {directory} matching {pattern!r}")
        return []

    db_path = max(candidates, key=lambda p: p.stat().st_mtime)

    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError as e:
        print(f"Warning: could not open BTT DB {db_path}: {e}")
        return []

    results: list[Keybinding] = []

    try:
        cur = con.cursor()

        # Map PK → app name for context resolution
        app_rows = cur.execute(
            "SELECT Z_PK, ZNAME FROM ZBTTBASEENTITY WHERE Z_ENT != 9"
        ).fetchall()
        pk_to_app: dict[int, str] = {
            pk: name for pk, name in app_rows if name
        }

        # BTT stores keyboard triggers as parent-child:
        # - Parent (Z_ENT=9, ZACTION=366): holds the keycode/modifiers
        # - Children (Z_ENT=9, ZACTION!=366): hold the actual actions
        # We join parent triggers to their children to get meaningful descriptions.
        rows = cur.execute("""
            SELECT p.ZKEYCODE, p.ZMODIFIERKEYS, p.Z_PK, p.ZPARENT,
                   c.ZACTION, c.ZNAME, CAST(c.ZACTIONDATA AS TEXT),
                   c.ZADDITIONALACTIONSTRING
            FROM ZBTTBASEENTITY p
            JOIN ZBTTBASEENTITY c ON c.ZPARENT = p.Z_PK
            WHERE p.Z_ENT = 9 AND p.ZISENABLED = 1
              AND p.ZKEYCODE IS NOT NULL AND p.ZKEYCODE > 0
              AND c.ZACTION NOT IN (49, -1, 366)
        """).fetchall()
    except sqlite3.DatabaseError as e:
        print(f"Warning: error querying BTT DB {db_path}: {e}")
        return []
    finally:
        con.close()

    source_file = db_path.name

    for keycode, modifier_bitmask, _pk, parent_pk, action_code, child_name, action_data, action_str in rows:
        try:
            keycode_int = int(keycode)
        except (TypeError, ValueError):
            continue

        if keycode_int <= 0:
            continue

        bitmask = int(modifier_bitmask) if modifier_bitmask is not None else 0

        try:
            key = normalize_key_combo(keycode_int, style="btt", bitmask=bitmask)
        except ValueError:
            continue

        # Build action description: prefer child name, then derived description
        if child_name:
            action = child_name
        else:
            action = _describe_action(action_code, action_data)
            if action_str:
                action = f"{action}: {action_str}"

        # Context: walk up to find the app container
        context = pk_to_app.get(parent_pk, "global") if parent_pk else "global"

        results.append(Keybinding(
            tool="btt",
            key=key,
            action=action,
            context=context,
            enabled=True,
            source_file=source_file,
            raw_key=f"{keycode_int}:{bitmask}",
        ))

    return results

import sqlite3
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo


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

        # Build a map of PK -> app name for all app-level entities.
        # App entities are Z_ENT values that are NOT 9 (trigger) and have a ZNAME.
        # In practice, app rows have a non-null ZBUNDLEID or sit at the parent level.
        # We fetch every row that could be a parent and use ZNAME as the app label.
        app_rows = cur.execute(
            "SELECT Z_PK, ZNAME FROM ZBTTBASEENTITY WHERE Z_ENT != 9"
        ).fetchall()
        pk_to_app: dict[int, str] = {
            pk: name for pk, name in app_rows if name
        }

        triggers = cur.execute(
            "SELECT ZNAME, ZKEYCODE, ZMODIFIERKEYS, ZISENABLED, Z_PK, ZPARENT "
            "FROM ZBTTBASEENTITY "
            "WHERE Z_ENT = 9 AND ZISENABLED = 1"
        ).fetchall()
    except sqlite3.DatabaseError as e:
        print(f"Warning: error querying BTT DB {db_path}: {e}")
        return []
    finally:
        con.close()

    source_file = db_path.name

    for name, keycode, modifier_bitmask, _enabled, _pk, parent_pk in triggers:
        if keycode is None:
            continue

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

        context = pk_to_app.get(parent_pk, "global") if parent_pk else "global"

        results.append(Keybinding(
            tool="btt",
            key=key,
            action=name or "",
            context=context,
            enabled=True,
            source_file=source_file,
            raw_key=f"{keycode_int}:{bitmask}",
        ))

    return results

import re
import sys
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo

_BIND_RE = re.compile(
    r"^bind(?:-key)?\s+(-n\s+)?(-r\s+)?(?:-T\s+(\S+)\s+)?(\S+)\s+(.+)$"
)


def _context_from_flags(no_prefix: str | None, table: str | None) -> str:
    if no_prefix:
        return "root"
    if table:
        return table.lower()
    return "prefix"


def _join_continuation_lines(lines: list[str]) -> list[tuple[int, str]]:
    """Merge lines ending with backslash; yields (original_line_index, merged_line)."""
    result: list[tuple[int, str]] = []
    i = 0
    while i < len(lines):
        start = i
        buf = lines[i].rstrip("\n")
        while buf.endswith("\\"):
            buf = buf[:-1]
            i += 1
            if i < len(lines):
                buf += lines[i].rstrip("\n").lstrip()
            else:
                break
        result.append((start, buf))
        i += 1
    return result


def extract(config: dict) -> list[Keybinding]:
    path = Path(config["path"]).expanduser()
    if not path.exists():
        print(f"[tmux] warning: config file not found: {path}", file=sys.stderr)
        return []

    raw_lines = path.read_text().splitlines(keepends=True)
    merged = _join_continuation_lines(raw_lines)

    bindings: list[Keybinding] = []
    prev_comment: str | None = None

    for idx, line in merged:
        stripped = line.strip()

        # Track preceding comment (immediately before a bind line).
        if stripped.startswith("#"):
            prev_comment = stripped.lstrip("#").strip()
            continue

        # Skip blank lines but reset comment tracking.
        if not stripped:
            prev_comment = None
            continue

        m = _BIND_RE.match(stripped)
        if not m:
            prev_comment = None
            continue

        no_prefix, _repeat, table, key, command = m.groups()
        command = command.strip()

        context = _context_from_flags(no_prefix, table)
        action = prev_comment if prev_comment is not None else command

        try:
            normalized = normalize_key_combo(key, style="tmux")
        except ValueError as exc:
            print(f"[tmux] warning: skipping key {key!r}: {exc}", file=sys.stderr)
            prev_comment = None
            continue

        bindings.append(
            Keybinding(
                tool="tmux",
                key=normalized,
                action=action,
                context=context,
                enabled=True,
                source_file=str(path),
                raw_key=key,
            )
        )
        prev_comment = None

    return bindings

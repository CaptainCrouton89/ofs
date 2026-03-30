import re
import sys
from pathlib import Path

from lib.keymap import Keybinding
from lib.modifiers import normalize_key_combo

_NVIM_BASE = Path("~/.config/nvim").expanduser()

_MODE_MAP: dict[str, str] = {
    "n": "normal",
    "v": "visual",
    "i": "insert",
    "c": "command",
    "t": "terminal",
}

# vim.keymap.set("n", "<leader>gg", ..., desc = "LazyGit", ...)
# vim.keymap.set({"n", "v"}, "<C-d>", ..., desc = "Scroll down", ...)
_KEYMAP_SET_RE = re.compile(
    r'vim\.keymap\.set\(\s*'
    r'(?:'
        r'"([^"]+)"'          # single mode string
        r'|'
        r'\{([^}]+)\}'        # table of modes
    r')\s*,\s*'
    r'"([^"]+)"\s*,'          # key
    r'[^)]*?desc\s*=\s*"([^"]*)"',  # desc
    re.DOTALL,
)

# Keys table entry: { "<leader>gg", ..., desc = "LazyGit", mode = "n" }
_KEYS_ENTRY_RE = re.compile(
    r'\{\s*"([^"]+)"'          # first element: key
    r'[^}]*?desc\s*=\s*"([^"]*)"'  # desc field
    r'(?:[^}]*?mode\s*=\s*'
        r'(?:"([^"]+)"|'       # mode as string
        r'\{([^}]+)\})'        # mode as table
    r')?'
    r'[^}]*\}',
    re.DOTALL,
)


def _parse_modes_string(raw: str) -> list[str]:
    """Extract mode letters from a raw string or comma-separated quoted values."""
    modes = re.findall(r'"([^"]+)"', raw)
    if not modes:
        # bare value like: n
        stripped = raw.strip().strip('"').strip("'")
        if stripped:
            modes = [stripped]
    return [m.strip() for m in modes if m.strip()]


def _expand_leader(key: str) -> str:
    return re.sub(r"(?i)<leader>", "<space>", key)


def _normalize(key: str) -> str:
    key = _expand_leader(key)
    try:
        return normalize_key_combo(key, style="nvim")
    except ValueError as exc:
        raise ValueError(f"cannot normalize {key!r}: {exc}") from exc


def _relative_source(path: Path) -> str:
    try:
        return str(path.relative_to(_NVIM_BASE))
    except ValueError:
        return str(path)


def _bindings_from_modes(
    modes: list[str],
    raw_key: str,
    action: str,
    source_file: str,
) -> list[Keybinding]:
    results: list[Keybinding] = []
    try:
        normalized = _normalize(raw_key)
    except ValueError as exc:
        print(f"[neovim] warning: {exc}", file=sys.stderr)
        return []

    for mode in modes:
        context = _MODE_MAP.get(mode, mode)
        results.append(
            Keybinding(
                tool="neovim",
                key=normalized,
                action=action,
                context=context,
                enabled=True,
                source_file=source_file,
                raw_key=raw_key,
            )
        )
    return results


def _extract_from_file(path: Path) -> list[Keybinding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    source_file = _relative_source(path)
    bindings: list[Keybinding] = []

    # Pattern 1: vim.keymap.set
    for m in _KEYMAP_SET_RE.finditer(text):
        single_mode, multi_modes_raw, key, desc = m.groups()
        if single_mode:
            modes = [single_mode]
        else:
            modes = _parse_modes_string(multi_modes_raw or "")
        if not modes:
            modes = ["n"]
        bindings.extend(_bindings_from_modes(modes, key, desc, source_file))

    # Pattern 2: Lazy plugin keys tables
    for m in _KEYS_ENTRY_RE.finditer(text):
        key, desc, mode_str, mode_table_raw = m.groups()
        if mode_table_raw:
            modes = _parse_modes_string(mode_table_raw)
        elif mode_str:
            modes = [mode_str]
        else:
            modes = ["n"]
        if not modes:
            modes = ["n"]
        bindings.extend(_bindings_from_modes(modes, key, desc, source_file))

    return bindings


def extract(config: dict) -> list[Keybinding]:
    glob_patterns: list[str] = config["paths"]
    bindings: list[Keybinding] = []

    for pattern in glob_patterns:
        pattern_path = Path(pattern).expanduser()
        base = pattern_path.parent
        glob_part = pattern_path.name

        # If the pattern contains glob characters, resolve from parent.
        if any(c in str(pattern_path) for c in ("*", "?", "[")):
            # Find the deepest non-glob prefix to use as base.
            parts = pattern_path.parts
            base_parts = []
            glob_parts = []
            in_glob = False
            for part in parts:
                if not in_glob and not any(c in part for c in ("*", "?", "[")):
                    base_parts.append(part)
                else:
                    in_glob = True
                    glob_parts.append(part)
            base_dir = Path(*base_parts) if base_parts else Path(".")
            glob_expr = "/".join(glob_parts)
            matched = list(base_dir.glob(glob_expr))
        else:
            matched = [pattern_path] if pattern_path.exists() else []

        if not matched:
            print(
                f"[neovim] warning: no files matched pattern: {pattern}",
                file=sys.stderr,
            )
            continue

        for file_path in matched:
            if not file_path.is_file():
                continue
            try:
                bindings.extend(_extract_from_file(file_path))
            except OSError as exc:
                print(
                    f"[neovim] warning: could not read {file_path}: {exc}",
                    file=sys.stderr,
                )

    return bindings

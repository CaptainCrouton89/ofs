import csv
import io
import json
from collections import defaultdict

from lib.keymap import Keybinding


def format_tsv(bindings: list[Keybinding]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, dialect=csv.excel_tab)
    writer.writerow(["tool", "key", "action", "context", "source"])
    for b in bindings:
        writer.writerow([b.tool, b.key, b.action, b.context, b.source_file])
    return buf.getvalue()


def format_json(bindings: list[Keybinding]) -> str:
    return json.dumps([b.to_dict() for b in bindings], indent=2)


def format_markdown(bindings: list[Keybinding]) -> str:
    groups: dict[str, list[Keybinding]] = defaultdict(list)
    for b in bindings:
        groups[b.tool].append(b)

    sections = []
    for tool, tool_bindings in groups.items():
        lines = [f"## {tool.title()}"]
        lines.append("")
        lines.append("| Key | Action | Context | Source |")
        lines.append("| --- | ------ | ------- | ------ |")
        for b in tool_bindings:
            lines.append(f"| {b.key} | {b.action} | {b.context} | {b.source_file} |")
        sections.append("\n".join(lines))

    return "\n\n".join(sections)


def format_output(bindings: list[Keybinding], fmt: str) -> str:
    if fmt == "tsv":
        return format_tsv(bindings)
    elif fmt == "json":
        return format_json(bindings)
    elif fmt == "md":
        return format_markdown(bindings)
    else:
        raise ValueError(f"Unknown format: {fmt!r}. Expected 'tsv', 'json', or 'md'.")

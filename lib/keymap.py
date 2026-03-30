from collections import OrderedDict
from dataclasses import dataclass


@dataclass
class Keybinding:
    tool: str
    key: str
    action: str
    context: str
    enabled: bool
    source_file: str
    raw_key: str

    def to_dict(self) -> OrderedDict:
        return OrderedDict([
            ("tool", self.tool),
            ("key", self.key),
            ("action", self.action),
            ("context", self.context),
            ("enabled", self.enabled),
            ("source_file", self.source_file),
            ("raw_key", self.raw_key),
        ])

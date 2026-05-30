"""Configuration: ~/.config/peerpet/config.toml (optional).

Zero-config by default — every field has a sane default. TOML is read with
stdlib `tomllib` (3.11+) or the `tomli` backport (declared as a dependency for
<3.11). If neither is available, defaults are used.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # py311+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover
    try:
        import tomli as _toml  # type: ignore
    except ModuleNotFoundError:
        _toml = None  # type: ignore


def config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return Path(base) / "peerpet" / "config.toml"


@dataclass
class Config:
    pet_name: str = "Pixel"
    pet_rows: int = 1
    tick_interval: float = 0.5  # seconds between animation frames
    shell: str | None = None  # default: $SHELL
    use_honcho: bool = False  # "cool feature later"; needs honcho extra + keys

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        path = path or config_path()
        if _toml is None or not path.exists():
            return cls()
        with open(path, "rb") as f:
            data = _toml.load(f)
        fields = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in fields})

    @property
    def resolved_shell(self) -> str:
        return self.shell or os.environ.get("SHELL", "/bin/bash")

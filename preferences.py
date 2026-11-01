"""Store the selected appearance in the user's application settings directory."""

import json
import os
from pathlib import Path
import sys
import tempfile


def preference_path():
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        configured = os.environ.get("XDG_CONFIG_HOME", "")
        base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".config"
    return base / "AlgoStudio" / "preferences.json"


def load_theme(choices, path=None):
    try:
        path = Path(path) if path is not None else preference_path()
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
        mode = data.get("theme") if isinstance(data, dict) else None
        return mode if isinstance(mode, str) and mode in choices else "System"
    except (OSError, ValueError, RuntimeError):
        return "System"


def save_theme(mode, choices, path=None):
    if not isinstance(mode, str) or mode not in choices:
        return False
    temporary = None
    try:
        path = Path(path) if path is not None else preference_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".theme-", suffix=".tmp", delete=False) as destination:
            temporary = Path(destination.name)
            json.dump({"theme": mode}, destination)
            destination.write("\n")
        os.replace(temporary, path)
        return True
    except (OSError, ValueError, RuntimeError):
        return False
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

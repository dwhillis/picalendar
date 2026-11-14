"""
Chore wheel rotation state management.
Persists the rotation offset in a JSON data file so it survives restarts.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_FILE = Path(__file__).parent / "chore_wheel_data.json"
_DEFAULT = {"rotation": 0, "names": ["?", "?", "?"]}


def _read() -> dict:
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text())
        except Exception as e:
            logger.warning(f"Failed to read {DATA_FILE}: {e}")
    return dict(_DEFAULT)


def _write(data: dict):
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n")


def get_names() -> list[str]:
    return _read().get("names", _DEFAULT["names"])


def get_rotation() -> int:
    return _read().get("rotation", 0)


def set_rotation(value: int):
    data = _read()
    data["rotation"] = value
    _write(data)


def get_assigned_names() -> dict[str, str]:
    """Return a mapping of category to the currently assigned name."""
    names = get_names()
    rotation = get_rotation()
    categories = ["Movie", "Food", "Games"]
    return {cat: names[(i + rotation) % len(names)] for i, cat in enumerate(categories)}


def rotate_forward():
    set_rotation(get_rotation() + 1)


def rotate_back():
    set_rotation(get_rotation() - 1)

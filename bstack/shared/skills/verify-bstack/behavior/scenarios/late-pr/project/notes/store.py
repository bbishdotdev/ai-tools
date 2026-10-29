import json
from pathlib import Path

DEFAULT = Path("notes.json")


def load(path=DEFAULT):
    return json.loads(Path(path).read_text()) if Path(path).exists() else []


def save(notes, path=DEFAULT):
    Path(path).write_text(json.dumps(notes, indent=2) + "\n")

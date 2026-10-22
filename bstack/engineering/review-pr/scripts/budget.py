from datetime import datetime, timedelta, timezone
import fcntl

from contracts import ReviewError
from host import read_json, write_json


def reserve(root, target, limit, calls=6):
    now = datetime.now(timezone.utc)
    path = root / "usage.json"
    lock_path = root / ".usage.lock"
    if path.is_symlink() or lock_path.is_symlink():
        raise ReviewError("Review usage files must not be symbolic links")
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        history = read_json(path) if path.exists() else []
        if not isinstance(history, list):
            raise ReviewError("Review usage history is invalid")
        recent = []
        for item in history:
            try:
                when = datetime.fromisoformat(item["at"])
                count = item["calls"]
            except (KeyError, TypeError, ValueError) as error:
                raise ReviewError("Review usage history is invalid") from error
            if when.tzinfo is None or type(count) is not int or count < 1:
                raise ReviewError("Review usage history is invalid")
            if when > now - timedelta(hours=24):
                recent.append(item)
        if sum(item["calls"] for item in recent) + calls > limit:
            raise ReviewError(f"Review model-call budget reached ({limit} reserved calls per 24 hours). Wait for the window to clear or change the private review config")
        recent.append({"at": now.isoformat(), "target": target, "calls": calls})
        write_json(path, recent)
        return {"reserved": calls, "used_24h": sum(item["calls"] for item in recent), "limit_24h": limit}

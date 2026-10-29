from .schema import MAX_LENGTH


class Store:
    def __init__(self):
        self._rows = {}
        self._cache = {}

    def save(self, record):
        row = {key: value[:MAX_LENGTH] if isinstance(value, str) else value for key, value in record.items()}
        self._rows[row["member_id"]] = row
        self._cache.pop(row["member_id"], None)

    def load(self, member_id):
        if member_id not in self._cache:
            self._cache[member_id] = dict(self._rows[member_id])
        return dict(self._cache[member_id])

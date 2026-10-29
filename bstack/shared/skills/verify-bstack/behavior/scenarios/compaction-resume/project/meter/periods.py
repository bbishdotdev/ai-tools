from datetime import datetime, timezone


def month_bounds(year, month):
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    stop = datetime(year + month // 12, month % 12 + 1, 1, tzinfo=timezone.utc)
    return start, stop

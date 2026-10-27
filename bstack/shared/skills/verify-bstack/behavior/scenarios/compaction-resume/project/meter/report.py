from collections import Counter
from datetime import datetime

from .periods import month_bounds


def parse(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def in_period(moment, start, stop):
    return start <= moment <= stop


def monthly_totals(events, year, month):
    start, stop = month_bounds(year, month)
    totals = Counter()
    for event in events:
        if in_period(parse(event["at"]), start, stop):
            totals[event["customer"]] += event["units"]
    return dict(totals)

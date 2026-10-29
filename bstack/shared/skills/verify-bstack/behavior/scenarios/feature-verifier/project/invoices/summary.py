import csv
from decimal import Decimal


def load(path):
    with open(path, newline="") as handle:
        return [{"id": row["id"], "amount": Decimal(row["amount"])} for row in csv.DictReader(handle)]


def summarize(invoices):
    return {"count": len(invoices), "total": sum((item["amount"] for item in invoices), Decimal("0"))}


def render(summary):
    return f"Invoices: {summary['count']}\nTotal: {summary['total']:.2f}"

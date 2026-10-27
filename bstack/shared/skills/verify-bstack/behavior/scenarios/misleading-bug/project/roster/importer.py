import csv
import io


def rows(text):
    for row in csv.DictReader(io.StringIO(text)):
        yield {"member_id": row["id"], "displayName": row["name"], "email": row["email"], "team": row["team"]}

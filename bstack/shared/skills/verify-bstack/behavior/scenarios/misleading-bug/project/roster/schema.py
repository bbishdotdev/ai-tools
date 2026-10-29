FIELDS = ("member_id", "display_name", "email", "team")
MAX_LENGTH = 64


def normalize(record):
    return {field: record.get(field) for field in FIELDS}

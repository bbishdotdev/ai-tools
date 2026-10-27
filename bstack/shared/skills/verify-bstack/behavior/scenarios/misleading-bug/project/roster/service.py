from . import forms, importer
from .schema import normalize


def add_member(store, member_id, display_name, email, team):
    store.save(normalize({"member_id": member_id, "display_name": display_name, "email": email, "team": team}))


def rename_member(store, member_id, new_name):
    current = store.load(member_id)
    store.save(normalize(forms.rename_payload(current, new_name)))


def import_csv(store, text):
    for row in importer.rows(text):
        store.save(normalize(row))

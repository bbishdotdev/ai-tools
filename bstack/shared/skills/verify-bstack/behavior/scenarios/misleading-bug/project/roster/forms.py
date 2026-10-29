def rename_payload(current, new_name):
    return {**current, "displayName": new_name.strip()}

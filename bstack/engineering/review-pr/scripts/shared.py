import json
import re

from contracts import COVERAGE, FINDING, ReviewError, canonical, digest, text_schema, unique, validate, verdict

PUBLISHED_FINDING = {**FINDING, "properties": {**FINDING["properties"], "title": text_schema(200),
                     "explanation": text_schema(2000), "action": text_schema(1000)}}

PREFIXES = {1: "<!-- bstack-review-v1:", 2: "<!-- bstack-review-v2:"}
MAX_RECEIPT = 40000
VOLATILE = {"created_at", "updated_at", "submitted_at", "reactions", "node_id", "mergeable", "mergeable_state"}


def config_digest(config):
    return digest({"roles": config["roles"], "zip_trees": config["zip_trees"], "worker": config.get("worker"),
                   "runtime_verification": config.get("runtime_verification")})


def normalized(value):
    if isinstance(value, dict):
        return {key: normalized(item) for key, item in value.items() if key not in VOLATILE}
    if isinstance(value, list):
        return sorted((normalized(item) for item in value), key=canonical)
    return value


def source_record(kind, item):
    return {"kind": kind, "id": item["id"], "author": item["author"], "body_digest": digest(item.get("body") or "")}


def context_digest(state, checks, ignored=()):
    copied = {**state, "discussion": {}}
    identities = {(item["kind"], item["id"], item["author"], item["body_digest"]) for item in ignored}
    for kind, entries in state["discussion"].items():
        copied["discussion"][kind] = [item for item in entries if (kind, item["id"], item["author"], digest(item.get("body") or "")) not in identities]
    return digest(normalized({"state": copied, "checks": checks}))


def public_receipt(result, visible_body):
    pr = result["snapshot"]["pr"]
    value = {"version": 2, "run_id": result["run_id"], "target": result["snapshot"]["target"],
             "head": pr["head"]["sha"], "base": pr["base"]["sha"], "config_digest": result["config_digest"],
             "policy_digest": result["policy_digest"], "context_digest": result["context_digest"], "input_digest": result["input_digest"],
             "coverage": result["coverage"], "verdict": result["verdict"], "findings": result["findings"],
             "human_review_required": result.get("human_review_required", []),
             "resolved_ids": [item["id"] for item in result.get("resolved_findings", [])],
             "body_digest": digest(visible_body.rstrip()), "echoes": result.get("publication_echoes", [])}
    body = canonical(value).replace("<", "\\u003c").replace(">", "\\u003e")
    if len(body.encode()) > MAX_RECEIPT:
        return ""
    return PREFIXES[2] + body + " -->"


def decoded_receipt(item, target):
    body = item.get("body") or ""
    if not isinstance(body, str) or not body.rstrip().endswith(" -->"):
        return None
    prefix = next((value for value in PREFIXES.values() if body.count(value) == 1), None)
    if prefix is None:
        return None
    visible, encoded = body.rsplit(prefix, 1)
    if len(encoded.encode()) > MAX_RECEIPT + 4:
        return None
    try:
        value = json.loads(encoded.rstrip()[:-4])
        required = {"version", "run_id", "target", "head", "base", "config_digest", "policy_digest", "context_digest", "input_digest", "coverage", "verdict", "findings", "resolved_ids", "body_digest", "echoes"}
        if not isinstance(value, dict) or type(value.get("version")) is not int or value["version"] not in PREFIXES or prefix != PREFIXES[value["version"]] or value.get("target") != target:
            return None
        if set(value) != required | ({"human_review_required"} if value["version"] == 2 else set()):
            return None
        if value["body_digest"] != digest(visible.rstrip()) or item.get("commit_id") != value["head"]:
            return None
        if not re.fullmatch(r"[a-f0-9]{32}", value["run_id"]):
            return None
        for key in ("head", "base"):
            if not re.fullmatch(r"[a-f0-9]{40,64}", value[key]):
                return None
        for key in ("config_digest", "policy_digest", "context_digest", "input_digest", "body_digest"):
            if not re.fullmatch(r"[a-f0-9]{64}", value[key]):
                return None
        validate(value["coverage"], COVERAGE)
        human = value.get("human_review_required", [])
        if not isinstance(human, list) or len(human) > 100 or any(
                not isinstance(rule, dict) or set(rule) != {"path", "reason", "changed"} or
                not isinstance(rule["path"], str) or not isinstance(rule["reason"], str) or
                not isinstance(rule["changed"], list) or not rule["changed"] or
                any(not isinstance(path, str) or path.startswith("/") or ".." in path.split("/") for path in rule["changed"])
                for rule in human):
            return None
        if not isinstance(value["findings"], list) or len(value["findings"]) > 30:
            return None
        unique(value["findings"])
        for finding in value["findings"]:
            validate(finding, PUBLISHED_FINDING)
            for evidence in finding["evidence"]:
                path = evidence["path"]
                if path != "@pr" and (path.startswith("/") or ".." in path.split("/") or ".bstack" in path.split("/") or "\\" in path):
                    return None
        expected = verdict(value["findings"])
        if (not value["coverage"]["complete"] or human) and expected == "APPROVE":
            expected = "COMMENT"
        if value["verdict"] != expected:
            return None
        state = item.get("state", "").upper()
        allowed = {"APPROVE": {"APPROVED", "APPROVE", "COMMENTED", "COMMENT"}, "REQUEST_CHANGES": {"CHANGES_REQUESTED", "REQUEST_CHANGES", "COMMENTED", "COMMENT"}, "COMMENT": {"COMMENTED", "COMMENT"}}
        if state not in allowed[expected]:
            return None
        if not isinstance(value["resolved_ids"], list) or len(value["resolved_ids"]) > 100 or not all(isinstance(name, str) and 0 < len(name) <= 100 for name in value["resolved_ids"]):
            return None
        if not isinstance(value["echoes"], list) or len(value["echoes"]) > 100:
            return None
        for echo in value["echoes"]:
            if (set(echo) != {"kind", "id", "author", "body_digest"} or echo["kind"] not in {"comments", "inline", "reviews"}
                    or type(echo["id"]) is not int or echo["id"] < 1 or echo["author"] != item.get("author")
                    or not isinstance(echo["body_digest"], str) or not re.fullmatch(r"[a-f0-9]{64}", echo["body_digest"])):
                return None
        return value
    except (ValueError, TypeError, KeyError, AttributeError, ReviewError):
        return None


def model_state(state):
    copied = json.loads(canonical(state))
    for item in copied["discussion"]["reviews"]:
        if decoded_receipt({**item, "state": "COMMENTED"}, copied["target"]):
            item["body"] = item["body"].split(next(prefix for prefix in PREFIXES.values() if prefix in item["body"]), 1)[0].rstrip()
    return copied


def receipts(state, github):
    candidates = [(item, decoded_receipt(item, state["target"])) for item in state["discussion"]["reviews"]]
    candidates = [(item, value) for item, value in candidates if value and value["coverage"]["complete"]]
    if not candidates:
        return []
    try:
        actor = github.api("user", global_path=True)["login"]
    except (ReviewError, KeyError, TypeError):
        return []
    if not isinstance(actor, str):
        return []
    records = []
    for item, value in candidates:
        author = item.get("author")
        if not isinstance(author, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", author):
            continue
        if author.casefold() == actor.casefold():
            records.append({"receipt": value, "source": {**source_record("reviews", item), "url": item.get("html_url"), "node_id": item.get("node_id"), "body": item.get("body")}})
    return records


def compatible_receipt(record, state, checks, config_id, policy_id):
    value = record["receipt"]
    return (value["head"] == state["pr"]["head"]["sha"] and value["base"] == state["pr"]["base"]["sha"]
            and value["config_digest"] == config_id and value["policy_digest"] == policy_id
            and value["context_digest"] == context_digest(state, checks, [record["source"], *value["echoes"]]))


def matching_context(result, state, checks, extra_ignored=()):
    return result["context_digest"] == context_digest(state, checks, extra_ignored)

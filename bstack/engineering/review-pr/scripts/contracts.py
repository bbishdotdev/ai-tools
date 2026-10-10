import hashlib
import json
import re


class ReviewError(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def object_schema(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def text_schema(maximum=4000):
    return {"type": "string", "minLength": 1, "maxLength": maximum}


def array_schema(items, maximum=100):
    return {"type": "array", "items": items, "maxItems": maximum}


COVERAGE = object_schema({"complete": {"type": "boolean"}, "limits": array_schema(text_schema())})
EVIDENCE = object_schema({"path": text_schema(), "line": {"type": "integer", "minimum": 1}, "side": {"type": "string", "enum": ["head", "base", "target"]}, "reason": text_schema()})
FINDING = object_schema({
    "id": text_schema(100), "category": {"type": "string", "enum": ["blocker", "human-decision", "moderate", "low"]},
    "title": text_schema(200), "explanation": text_schema(2000),
    "evidence": {**array_schema(EVIDENCE, 12), "minItems": 1}, "action": text_schema(1000),
})
PRIOR = object_schema({"id": text_schema(100), "status": {"type": "string", "enum": ["open", "resolved", "reopened"]}, "evidence": {**array_schema(text_schema(), 12), "minItems": 1}})
REVIEW = object_schema({
    "coverage": COVERAGE,
    "neededness": object_schema({"assessment": {"type": "string", "enum": ["needed", "unnecessary", "uncertain"]}, "evidence": {**array_schema(text_schema(), 12), "minItems": 1}}),
    "findings": array_schema(FINDING, 30), "prior": array_schema(PRIOR, 100),
})
DECISION = object_schema({"id": text_schema(100), "disposition": {"type": "string", "enum": ["kept", "dismissed", "resolved", "duplicate"]}, "reason": text_schema(), "duplicate_of": {"type": ["string", "null"]}})
FEEDBACK = object_schema({"kind": {"type": "string", "enum": ["comments", "inline", "reviews"]}, "id": {"type": "integer", "minimum": 1},
    "relation": {"type": "string", "enum": ["agree", "extend", "disagree", "resolved"]}, "finding_ids": array_schema(text_schema(100), 30),
    "body": {"type": "string", "maxLength": 1600}, "evidence": array_schema(EVIDENCE, 12)})
ARTIFACT_ASSESSMENT = object_schema({"id": text_schema(100), "material": {"type": "boolean"}, "reason": text_schema(1000)})
JUDGMENT = object_schema({"coverage": COVERAGE, "decisions": array_schema(DECISION, 200), "findings": array_schema(FINDING, 30),
    "feedback": array_schema(FEEDBACK, 100), "new_findings": array_schema(text_schema(100), 30), "artifact_assessments": array_schema(ARTIFACT_ASSESSMENT, 500)})


def validate(value, schema, path="result"):
    kind = schema["type"]
    kinds = kind if isinstance(kind, list) else [kind]
    matches = {"object": isinstance(value, dict), "array": isinstance(value, list), "string": isinstance(value, str), "integer": type(value) is int, "boolean": type(value) is bool, "null": value is None}
    if not any(matches[item] for item in kinds):
        raise ReviewError(f"{path}: expected {kind}")
    if "enum" in schema and value not in schema["enum"]:
        raise ReviewError(f"{path}: unsupported value")
    if isinstance(value, dict):
        if set(value) != set(schema["required"]):
            raise ReviewError(f"{path}: fields must be {', '.join(schema['required'])}")
        for key, item in value.items():
            validate(item, schema["properties"][key], f"{path}.{key}")
    elif isinstance(value, list):
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 1000):
            raise ReviewError(f"{path}: invalid item count")
        for index, item in enumerate(value):
            validate(item, schema["items"], f"{path}[{index}]")
    elif isinstance(value, str):
        if not schema.get("minLength", 0) <= len(value.strip()) <= schema.get("maxLength", 100000):
            raise ReviewError(f"{path}: invalid text length")
        if "\x00" in value:
            raise ReviewError(f"{path}: contains a null byte")
    elif type(value) is int and value < schema.get("minimum", value):
        raise ReviewError(f"{path}: invalid number")
    return value


def unique(items, key="id"):
    values = [item[key] for item in items]
    if len(set(values)) != len(values):
        raise ReviewError(f"Duplicate {key} values")
    return set(values)


def validate_findings(findings, trees):
    unique(findings)
    for item in findings:
        for evidence in item["evidence"]:
            name, side = evidence["path"], evidence["side"]
            if name == "@pr" and evidence["line"] == 1:
                continue
            prefix = side + "/"
            if name not in trees[side] and name.startswith(prefix) and name[len(prefix):] in trees[side]:
                name = evidence["path"] = name[len(prefix):]
            metadata = trees[side].get(name)
            if not metadata or not metadata.get("lines") or evidence["line"] > metadata["lines"]:
                raise ReviewError(f"Invalid evidence location: {side}:{name}:{evidence['line']}")


def validate_review(report, prior_ids, trees):
    validate(report, REVIEW)
    validate_findings(report["findings"], trees)
    if unique(report["prior"]) != set(prior_ids):
        raise ReviewError("Reviewer must address every previous final finding exactly once")
    if report["neededness"]["assessment"] == "unnecessary" and not report["findings"]:
        raise ReviewError("An unnecessary-change assessment needs an actionable evidenced finding")
    return report


def consolidate(judgment, candidates, trees, discussion=None, artifacts=()):
    validate(judgment, JUDGMENT)
    validate_findings(judgment["findings"], trees)
    expected = unique(candidates)
    if unique(judgment["decisions"]) != expected:
        raise ReviewError("Adjudicator must address every candidate and previous final finding exactly once")
    kept = {item["id"] for item in judgment["decisions"] if item["disposition"] == "kept"}
    if unique(judgment["findings"]) != kept:
        raise ReviewError("Final findings must match kept decisions exactly")
    for item in judgment["decisions"]:
        if item["disposition"] == "duplicate":
            if item["duplicate_of"] not in kept or item["duplicate_of"] == item["id"]:
                raise ReviewError("Duplicate findings must point to a retained finding")
        elif item["duplicate_of"] is not None:
            raise ReviewError("Only duplicate decisions may name duplicate_of")
    targets, matched = set(), set()
    for item in judgment["feedback"]:
        target = (item["kind"], item["id"])
        if target in targets or not any(source["id"] == item["id"] for source in (discussion or {}).get(item["kind"], [])):
            raise ReviewError("Feedback must reference unique existing discussion targets")
        targets.add(target)
        identifiers = item["finding_ids"]
        if len(set(identifiers)) != len(identifiers) or not set(identifiers) <= kept:
            raise ReviewError("Feedback must reference retained findings")
        if item["relation"] in {"agree", "extend"}:
            if matched & set(identifiers):
                raise ReviewError("An existing finding must have one discussion match")
            matched.update(identifiers)
        if item["relation"] != "agree" and (not item["body"].strip() or not item["evidence"]):
            raise ReviewError("A discussion reply needs an explanation and source evidence")
        validate_findings([{"id": "feedback", "evidence": item["evidence"]}], trees)
    new = judgment["new_findings"]
    if len(set(new)) != len(new) or matched & set(new) or matched | set(new) != kept:
        raise ReviewError("Retained findings must partition into new findings and existing discussion matches")
    if unique(judgment["artifact_assessments"]) != {item["id"] for item in artifacts}:
        raise ReviewError("Adjudicator must assess every artifact coverage issue exactly once")
    return judgment


def verdict(findings):
    categories = {item["category"] for item in findings}
    if "blocker" in categories:
        return "REQUEST_CHANGES"
    if "human-decision" in categories:
        return "COMMENT"
    return "APPROVE"


def scrub(value, models, field=None):
    if isinstance(value, dict):
        return {key: scrub(item, models, key) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub(item, models, field) for item in value]
    if isinstance(value, str) and field != "path":
        for model in sorted(models, key=len, reverse=True):
            value = re.sub(r"(?i)(?:I am |as (?:an? )?|reviewed by |reviewer: ?|model: ?)" + re.escape(model) + r"\b", "[anonymous reviewer]", value)
        return value
    return value

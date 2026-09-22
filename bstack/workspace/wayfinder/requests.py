"""Build agent requests from data and explicit snapshots, then save replay receipts."""

import os
from pathlib import Path
import tempfile
import uuid

from .core import MAX_REQUEST_BYTES, MUTATIONS, QUERIES, canonical, fail, identity
from .server import _decode

MAX_RECEIPT_BYTES = 32 * 1024 * 1024
CONTROL_FIELDS = {"expectedRev", "expectedMapRev", "expectedFromRev", "expectedToRev", "claimToken", "fence"}


def encode(value):
    try:
        return canonical(value).encode("utf-8")
    except (ValueError, TypeError, RecursionError, OverflowError):
        fail("validation", "Request contains invalid JSON values")


def read_json(path, limit=MAX_REQUEST_BYTES):
    with Path(path).open("rb") as stream:
        content = stream.read(limit + 1)
    if len(content) > limit:
        fail("validation", "JSON file exceeds its size limit")
    try:
        return _decode(content.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        fail("validation", "File must contain valid JSON")


def load_receipt(path, workspace, completed=True):
    receipt = read_json(path, MAX_RECEIPT_BYTES)
    if (not isinstance(receipt, dict) or type(receipt.get("version")) is not int or receipt["version"] != 1
            or not isinstance(receipt.get("request"), dict)):
        fail("validation", "Expected a version 1 request receipt")
    request = receipt["request"]
    if (not isinstance(request.get("op"), str) or request["op"] not in QUERIES | MUTATIONS
            or not isinstance(request.get("input"), dict)):
        fail("validation", "Receipt contains an invalid request")
    if receipt.get("workspace") != workspace.info:
        fail("validation", "Receipt belongs to a different workspace")
    result = receipt.get("result")
    if completed and (not isinstance(result, dict) or result.get("ok") is not True
                      or not isinstance(result.get("value"), dict)):
        fail("validation", "A basis or claim requires a successful receipt")
    return receipt


def record(receipts, kind, identifier=None):
    candidates = []
    for receipt in receipts:
        value = receipt["result"]["value"]
        keys = (kind, "from", "to") if kind == "ticket" else (kind,)
        items = [value.get(key) for key in keys]
        collection = value.get(kind + "s", [])
        if isinstance(collection, list):
            items.extend(collection)
        for item in items:
            if isinstance(item, dict) and "id" in item and "rev" in item:
                if identifier is None or item["id"] == identifier:
                    candidates.append(item)
    if not candidates or any(item != candidates[0] for item in candidates[1:]):
        fail("validation", f"Supply one unambiguous {kind} snapshot with --basis")
    return candidates[0]


def question_source(bases, question_id):
    question = record(bases, "question", question_id)
    answer = question.get("answer")
    if not isinstance(answer, dict):
        fail("not_ready", "Each question source needs an accepted answer")
    return {"questionId": question_id, "answerId": answer["id"], "revision": answer["revision"]}


def credentials(receipts, kind, item, actor):
    for receipt in receipts:
        request, value = receipt["request"], receipt["result"]["value"]
        if request.get("actor") != {"id": actor, "kind": "agent"}:
            continue
        saved = value.get(kind)
        if not isinstance(saved, dict) or saved.get("id") != item["id"]:
            continue
        lease = saved.get("claim")
        if not isinstance(lease, dict) or lease.get("owner") != actor:
            continue
        token = value.get("claimToken", request.get("input", {}).get("claimToken"))
        fence = value.get("fence", request.get("input", {}).get("fence"))
        if isinstance(token, str) and fence == lease.get("fence"):
            return {"claimToken": token, "fence": fence}
    fail("stale_claim", "Supply this actor's successful claim receipt with --claim or --basis")


def assemble(op, data, actor, bases, claims):
    if op not in QUERIES | MUTATIONS:
        fail("validation", "Unknown operation")
    if not isinstance(data, dict):
        fail("validation", "Operation input must be an object")
    if CONTROL_FIELDS & data.keys():
        fail("validation", "Revisions and claim credentials come from receipts, not input data")
    data = dict(data)
    if op in QUERIES:
        if actor or bases or claims:
            fail("validation", "Queries accept input data only")
        return {"op": op, "input": data}
    identity(actor, "actor")
    if op.endswith(".takeover"):
        fail("validation", "Claim takeover requires an explicit human operation")
    if op.endswith(".create"):
        if bases or claims:
            fail("validation", "Create accepts input data only; supply chosen source IDs in that data")
    elif op.startswith("ticket.relationship."):
        if claims:
            fail("validation", "Relationships use endpoint revisions, not claims")
        for endpoint in ("from", "to"):
            identity(data.get(endpoint), endpoint)
            item = record(bases, "ticket", data[endpoint])
            data["expected" + endpoint.title() + "Rev"] = item["rev"]
    else:
        kind = ("map" if op.startswith(("map.", "relationship.")) else
                "spec" if op.startswith("spec.") else "ticket" if op.startswith("ticket.") else "question")
        key = kind + "Id"
        is_claim = op.startswith("claim.") or ".claim." in op
        acquire = is_claim and op.endswith(".acquire")
        lease_only = is_claim and not acquire
        item = record(bases or (claims if lease_only else []), kind, data.get(key))
        data[key] = item["id"]
        if not lease_only:
            data["expectedMapRev" if op.startswith("relationship.") else "expectedRev"] = item["rev"]
        if kind != "map" and not acquire:
            data.update(credentials(claims or bases, kind, item, actor))
        elif claims:
            fail("validation", "This operation does not accept --claim")
        if op == "spec.approve":
            if "questionSources" in data:
                fail("validation", "Spec source identities come from reviewed question receipts in --basis")
            data["questionSources"] = [question_source(bases, question_id) for question_id in item["questionIds"]]
        elif op == "ticket.sources.acknowledge":
            if "sources" in data:
                fail("validation", "Source identities come from reviewed spec/question receipts in --basis")
            sources = item["sources"]
            data["sources"] = {"spec": None, "questions": [question_source(bases, source["questionId"])
                                                         for source in sources["questions"]]}
            if sources["spec"] is not None:
                spec = record(bases, "spec", sources["spec"]["specId"])
                if not spec.get("usableApproval"):
                    fail("not_ready", "The linked spec needs a usable approved revision")
                data["sources"]["spec"] = {"specId": spec["id"], "revision": spec["acceptedRevision"]}
    return {"op": op, "input": data, "actor": {"id": actor, "kind": "agent"}, "requestId": str(uuid.uuid4())}


def save_new(path, receipt):
    encoded = encode(receipt)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(encoded)
        stream.flush()
        os.fsync(stream.fileno())


def save_result(path, receipt):
    encoded = encode(receipt)
    if len(encoded) > MAX_RECEIPT_BYTES:
        fail("validation", "Result exceeds the receipt size limit; the saved request is still replayable")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".receipt-", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def execute(workspace, op, data, actor=None, basis=(), claim=(), receipt_path=None):
    bases = [load_receipt(path, workspace) for path in basis]
    claims = [load_receipt(path, workspace) for path in claim]
    request = assemble(op, data, actor, bases, claims)
    if len(encode(request)) > MAX_REQUEST_BYTES:
        fail("validation", "Request is too large")
    if op in MUTATIONS and receipt_path is None:
        fail("validation", "Mutations require --receipt with a new private file path")
    receipt = {"version": 1, "workspace": workspace.info, "request": request, "result": None}
    if receipt_path is not None:
        save_new(receipt_path, receipt)
    result = workspace.operate(request)
    if receipt_path is not None:
        receipt["result"] = result
        save_result(Path(receipt_path), receipt)
    return result


def replay(workspace, path):
    receipt = load_receipt(path, workspace, completed=False)
    request = receipt["request"]
    if (request.get("op") not in MUTATIONS or not isinstance(request.get("actor"), dict)
            or request["actor"].get("kind") != "agent"):
        fail("validation", "Only saved agent mutations can be replayed; query again for a fresh snapshot")
    result = workspace.operate(request)
    receipt["result"] = result
    save_result(Path(path), receipt)
    return result

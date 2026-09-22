import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wayfinder.core import Workspace
from wayfinder.requests import execute, replay

CLI = Path(__file__).resolve().parents[1] / "cli.py"
AUTHORITY = {"kind": "human", "decider": "Fixture owner", "confirmation": "Approved this fixture"}


class RequestTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.project = Path(self.temporary.name)
        self.workspace = Workspace.initialize(self.project)
        self.serial = 0

    def tearDown(self):
        self.temporary.cleanup()

    def cli(self, *args):
        result = subprocess.run([sys.executable, str(CLI), "--project", str(self.project), *map(str, args)],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.stderr, "")
        value = json.loads(result.stdout)
        self.assertEqual(result.returncode, 0 if value["ok"] else 1, value)
        return value

    def request(self, op, data=None, basis=(), claim=(), actor="fixture-agent", ok=True):
        self.serial += 1
        receipt = self.project / f"receipt-{self.serial}.json"
        args = ["request", op, "--receipt", receipt]
        if not op.endswith((".read", ".search")):
            args += ["--actor", actor]
        if data is not None:
            payload = self.project / f"input-{self.serial}.json"
            payload.write_text(json.dumps(data))
            args += ["--input-file", payload]
        for path in basis:
            args += ["--basis", path]
        for path in claim:
            args += ["--claim", path]
        result = self.cli(*args)
        self.assertEqual(result["ok"], ok, result)
        return receipt, result.get("value", result.get("error"))

    def question(self):
        _, created = self.request("map.create", {"title": "Checkout", "scope": "Plan only", "destination": "Choose storage"})
        map_id = created["map"]["id"]
        receipt, question = self.request("question.create", {"mapId": map_id, "title": "Where to store?", "method": "grilling"})
        return map_id, receipt, question["question"]

    def test_agent_flow_persists_plan_spec_ticket_without_handwritten_envelopes(self):
        map_id, question, _ = self.question()
        claim, _ = self.request("claim.acquire", basis=[question])
        answer, accepted = self.request("question.resolve", {"answer": {
            "markdown": "Use SQLite", "authority": AUTHORITY, "references": [],
        }}, basis=[claim])
        question_id = accepted["question"]["id"]
        spec, created = self.request("spec.create", {"mapId": map_id, "title": "Persistence", "markdown": "Keep records locally",
                                                    "questionIds": [question_id]})
        spec_claim, _ = self.request("spec.claim.acquire", basis=[spec])
        approved, _ = self.request("spec.approve", {"authority": AUTHORITY}, basis=[spec_claim, answer])
        saved = json.loads(approved.read_text())
        self.assertEqual(saved["request"]["input"]["questionSources"][0]["answerId"], accepted["question"]["answer"]["id"])
        ticket, created_ticket = self.request("ticket.create", {"specId": created["spec"]["id"], "title": "Persist records",
            "body": "Store locally", "acceptanceCriteria": "Records survive restart", "authority": AUTHORITY})
        current, _ = self.request("ticket.claim.acquire", basis=[ticket])
        for state in ("ready", "in-progress", "review"):
            current, _ = self.request("ticket.transition", {"to": state}, basis=[current])
        review, _ = self.request("ticket.claim.acquire", basis=[current], actor="fixture-reviewer")
        done, finished = self.request("ticket.transition", {"to": "done", "completion": {"markdown": "Fixture check passed", "references": []}},
                                      basis=[review], actor="fixture-reviewer")
        self.assertTrue(finished["ticket"]["satisfiesDependency"])
        result = self.cli("request", "board.read")
        self.assertEqual(result["value"]["tickets"][0]["state"], "done")
        self.assertEqual(json.loads(done.read_text())["request"]["actor"]["kind"], "agent")

    def test_replay_after_commit_before_receipt_save_does_not_duplicate_creation(self):
        path = self.project / "uncertain.json"
        data = {"title": "One map", "destination": "Replay", "scope": "Test"}
        with patch("wayfinder.requests.save_result", side_effect=OSError("interrupted after commit")):
            with self.assertRaises(OSError):
                execute(self.workspace, "map.create", data, "fixture-agent", receipt_path=path)
        self.assertIsNone(json.loads(path.read_text())["result"])
        result = self.cli("replay", "--receipt", path)
        self.assertTrue(result["ok"])
        self.assertEqual(self.cli("replay", "--receipt", path), result)
        self.assertEqual(len(self.cli("request", "workspace.read")["value"]["maps"]), 1)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_stale_basis_is_rejected_without_fetching_latest_revision(self):
        _, question, item = self.question()
        claim, _ = self.request("claim.acquire", basis=[question])
        changed, _ = self.request("question.update", {"patch": {"progress": "First work"}}, basis=[claim])
        failed, error = self.request("question.update", {"patch": {"progress": "Stale overwrite"}}, basis=[claim], ok=False)
        self.assertEqual(error["code"], "conflict")
        self.assertEqual(self.cli("replay", "--receipt", failed)["error"]["code"], "conflict")
        refreshed, _ = self.request("question.read", {"questionId": item["id"]})
        current, value = self.request("question.update", {"patch": {"progress": "Reconciled"}}, basis=[refreshed], claim=[changed])
        self.assertEqual(value["question"]["progress"], "Reconciled")
        released, _ = self.request("claim.release", basis=[current])
        _, error = self.request("question.update", {"patch": {"progress": "Wrong"}}, basis=[released], claim=[claim], ok=False)
        self.assertEqual(error["code"], "stale_claim")

    def test_receipts_cannot_cross_workspaces_or_actors(self):
        _, question, _ = self.question()
        claim, _ = self.request("claim.acquire", basis=[question])
        _, error = self.request("question.update", {"patch": {"progress": "Wrong owner"}}, basis=[claim], actor="other-agent", ok=False)
        self.assertEqual(error["code"], "stale_claim")
        other = self.project / "other"
        other.mkdir()
        foreign = Workspace.initialize(other)
        from wayfinder.core import DomainError
        with self.assertRaisesRegex(DomainError, "different workspace"):
            replay(foreign, claim)

    def test_no_write_without_receipt_and_existing_receipt_is_not_overwritten(self):
        path = self.project / "input.json"
        path.write_text(json.dumps({"title": "Map", "destination": "Safe", "scope": "Test"}))
        result = self.cli("request", "map.create", "--actor", "fixture-agent", "--input-file", path)
        self.assertEqual(result["error"]["code"], "validation")
        before = path.read_bytes()
        result = self.cli("request", "map.create", "--actor", "fixture-agent", "--input-file", path, "--receipt", path)
        self.assertFalse(result["ok"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.cli("request", "workspace.read")["value"]["maps"], [])

    def test_control_fields_authority_and_payload_validation(self):
        _, question, _ = self.question()
        claim, _ = self.request("claim.acquire", basis=[question])
        for data in ({"expectedRev": 1}, {"claimToken": "invented"}, {"fence": 1}, []):
            _, error = self.request("question.update", data, basis=[claim], ok=False)
            self.assertEqual(error["code"], "validation")
        _, error = self.request("question.resolve", {"answer": {"markdown": "No approval", "references": []}}, basis=[claim], ok=False)
        self.assertEqual(error["code"], "validation")
        _, error = self.request("claim.takeover", basis=[claim], ok=False)
        self.assertEqual(error["code"], "validation")
        invalid = self.project / "invalid.json"
        for content in ('{"title":"a","title":"b"}', '{"priority":NaN}', '{"priority":1e309}',
                        '{"title":"\\ud800"}', 'x' * 300000):
            invalid.write_text(content)
            self.assertEqual(self.cli("request", "map.create", "--actor", "fixture-agent", "--input-file", invalid,
                                      "--receipt", self.project / "should-not-exist.json")["error"]["code"], "validation")
            self.assertFalse((self.project / "should-not-exist.json").exists())

    def test_relationships_use_reviewed_endpoint_and_map_revisions(self):
        map_id, question, first = self.question()
        _, second = self.request("question.create", {"mapId": map_id, "title": "Second", "method": "research"})
        mapping, _ = self.request("map.read", {"mapId": map_id})
        _, linked = self.request("relationship.add", {"kind": "blocks", "from": first["id"], "to": second["question"]["id"]}, basis=[mapping])
        self.assertEqual(len(linked["relationships"]), 1)
        a, av = self.request("ticket.create", {"title": "First"})
        b, bv = self.request("ticket.create", {"title": "Second"})
        link, _ = self.request("ticket.relationship.add", {"kind": "blocks", "from": av["ticket"]["id"], "to": bv["ticket"]["id"]}, basis=[a, b])
        _, unlinked = self.request("ticket.relationship.remove", {"kind": "blocks", "from": av["ticket"]["id"], "to": bv["ticket"]["id"]}, basis=[link])
        self.assertEqual(unlinked["relationships"], [])

    def test_select_from_saved_lists_without_another_read(self):
        map_id, _, first = self.question()
        maps, _ = self.request("workspace.read")
        self.request("map.update", {"mapId": map_id, "patch": {"progress": "Planning"}}, basis=[maps])
        questions, _ = self.request("question.search", {"mapId": map_id, "ready": True})
        claimed, _ = self.request("claim.acquire", {"questionId": first["id"]}, basis=[questions])
        self.request("claim.release", basis=[claimed])
        self.request("ticket.create", {"title": "First"})
        _, second = self.request("ticket.create", {"title": "Second"})
        board, _ = self.request("board.read")
        _, error = self.request("ticket.claim.acquire", basis=[board], ok=False)
        self.assertEqual(error["code"], "validation")
        _, selected = self.request("ticket.claim.acquire", {"ticketId": second["ticket"]["id"]}, basis=[board])
        self.assertEqual(selected["ticket"]["title"], "Second")

    def test_source_acknowledgement_derives_current_identities_from_reviewed_receipts(self):
        spec, value = self.request("spec.create", {"title": "Spec", "markdown": "First scope"})
        spec_claim, _ = self.request("spec.claim.acquire", basis=[spec])
        approved, _ = self.request("spec.approve", {"authority": AUTHORITY}, basis=[spec_claim])
        ticket, value = self.request("ticket.create", {"title": "Ticket", "body": "Implement", "acceptanceCriteria": "Works",
            "authority": AUTHORITY, "specId": value["spec"]["id"]})
        ticket_id = value["ticket"]["id"]
        current, _ = self.request("ticket.claim.acquire", basis=[ticket])
        for state in ("ready", "in-progress"):
            current, _ = self.request("ticket.transition", {"to": state}, basis=[current])
        revised, _ = self.request("spec.update", {"patch": {"markdown": "Revised scope"}}, basis=[approved])
        approved, _ = self.request("spec.approve", {"authority": AUTHORITY}, basis=[revised])
        ticket, _ = self.request("ticket.read", {"ticketId": ticket_id})
        current, _ = self.request("ticket.claim.acquire", basis=[ticket])
        acknowledgement, result = self.request("ticket.sources.acknowledge", {"note": "Reconciled implementation with revised scope", "authority": AUTHORITY},
                                               basis=[current, approved])
        self.assertFalse(result["ticket"]["needsSourceReview"])
        self.assertEqual(result["ticket"]["state"], "in-progress")
        self.assertEqual(json.loads(acknowledgement.read_text())["request"]["input"]["sources"]["spec"]["revision"], 2)


if __name__ == "__main__":
    unittest.main()

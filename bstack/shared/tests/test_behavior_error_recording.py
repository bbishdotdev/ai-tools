import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


BEHAVIOR = Path(__file__).resolve().parents[1] / "skills/verify-bstack/behavior"
sys.path.insert(0, str(BEHAVIOR))
import run as behavior
import matrix


class BehaviorErrorRecordingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.results = self.folder / "results.json"
        patch = mock.patch.object(behavior, "RESULTS", self.results)
        patch.start()
        self.addCleanup(patch.stop)

    def seed(self, host):
        row = {"passes": 3, "quality_passes": 3, "repeats": 3, "failed_checks": [],
               "reminder_hook_runs": 3, "run": "prior-pass"}
        scenarios = {name: dict(copy.deepcopy(row), column=scenario["column"])
                     for name, scenario in behavior.SCENARIOS.items()}
        data = {"updated": "2000-01-01", "hosts": {host: {
            "label": "Fixture CLI", "surface": "cli", "version": "fixture-version", "model": "fixture-model",
            "bindings": ["skills", "auto", "pr", "hooks"], "scenarios": scenarios}},
            "models": {f"{host}|fixture-model": {"host": host, "model": "fixture-model",
                                                 "scenarios": copy.deepcopy(scenarios)}}}
        self.results.write_text(json.dumps(data))
        return data

    def passing(self, host, scenario, repeat):
        return {"host": host, "surface": host + "-cli", "model": "fixture-model", "scenario": scenario,
                "repeat": repeat, "status": "pass", "integration_pass": True, "quality_pass": True,
                "checks": {"outcome": True}, "reminder_hook_every_turn": True}

    def save(self, results, run_id):
        clients = {result["host"]: {"version": "fixture-version"} for result in results}
        behavior.record(behavior.summarize(results, clients), run_id)
        return json.loads(self.results.read_text())

    def resume(self, out):
        host = mock.Mock(model="fixture-model", compacts=True)
        host.binary.return_value = "fixture-cli"
        argv = ["behavior", "--resume", str(out), "--tools", "codex", "--scenarios", "misleading-bug",
                "--jobs", "1", "--record"]
        with mock.patch.object(behavior, "ROOT", self.folder), \
                mock.patch.dict(behavior.HOSTS, {"codex": host}, clear=True), \
                mock.patch.object(behavior.subprocess, "run", return_value=subprocess.CompletedProcess(
                    ["fixture-cli", "--version"], 0, "fixture-version", "")), \
                mock.patch.object(sys, "argv", argv):
            return behavior.main()

    def test_latest_errors_replace_prior_pass_and_clean_rerun_restores_support(self):
        original = self.seed("codex-cli")
        self.assertEqual(matrix.status(original["hosts"]["codex-cli"], "auto"), "supported")
        failed = self.save([dict(self.passing("codex", "misleading-bug", 1), status="error",
                                 reason="launch failed", error_kind="execution")], "latest-error")
        host = failed["hosts"]["codex-cli"]
        row = host["scenarios"]["misleading-bug"]
        self.assertEqual((row["attempts"], row["repeats"], row["passes"], row["quality_passes"]), (1, 0, 0, 0))
        self.assertEqual(row["errors"], [{"repeat": 1, "kind": "execution", "reason": "launch failed"}])
        self.assertEqual(row["failed_checks"], [])
        self.assertEqual(row["run"], "latest-error")
        self.assertNotEqual(failed["updated"], "2000-01-01")
        self.assertEqual(host["scenarios"]["direct-pr"], original["hosts"]["codex-cli"]["scenarios"]["direct-pr"])
        self.assertEqual(matrix.status(host, "auto"), "partial")
        self.assertEqual(matrix.status(host, "hooks"), "partial")
        self.assertIn("ungraded; 1 execution error of 1 attempt", matrix.render_models(failed))
        cleaned = self.save([self.passing("codex", "misleading-bug", 1)], "clean-rerun")
        host = cleaned["hosts"]["codex-cli"]
        row = host["scenarios"]["misleading-bug"]
        self.assertEqual((row["attempts"], row["repeats"], row["passes"], row["quality_passes"]), (1, 1, 1, 1))
        self.assertEqual(row["errors"], [])
        self.assertEqual(row["run"], "clean-rerun")
        self.assertEqual(cleaned["models"]["codex-cli|fixture-model"]["scenarios"]["misleading-bug"], row)
        self.assertEqual(matrix.status(host, "auto"), "supported")
        self.assertEqual(matrix.status(host, "hooks"), "supported")

    def test_quota_attempt_is_ungraded_and_preserves_two_completed_repeats(self):
        self.seed("copilot-cli")
        with mock.patch.object(behavior.HOSTS["copilot"], "model", "fixture-model"), \
                mock.patch.object(behavior, "execute", side_effect=RuntimeError("quota_exceeded")):
            error = behavior.run_case("copilot", "unused", "late-pr", 3, self.folder / "run", 1)
        self.assertEqual((error["surface"], error["model"], error["error_kind"]),
                         ("copilot-cli", "fixture-model", "provider_limit"))
        error.pop("error_kind")
        data = self.save([self.passing("copilot", "late-pr", repeat) for repeat in (1, 2)] + [error], "mixed-quota")
        host = data["hosts"]["copilot-cli"]
        row = host["scenarios"]["late-pr"]
        self.assertEqual((row["attempts"], row["repeats"], row["passes"], row["quality_passes"]), (3, 2, 2, 2))
        self.assertEqual(row["errors"], [{"repeat": 3, "kind": "provider_limit", "reason": "quota_exceeded"}])
        self.assertEqual(row["failed_checks"], [])
        self.assertEqual(matrix.status(host, "pr"), "partial")
        self.assertEqual(matrix.status(host, "hooks"), "partial")
        self.assertIn("2 · 2 of 2; 1 provider limit of 3 attempts", matrix.render_models(data))

    def test_assessment_error_finishes_report_and_replaces_prior_support(self):
        self.seed("codex-cli")
        out = self.folder / "assessment-run"

        def malformed_observation(host, binary, name, repeat, folder, timeout):
            (folder / "observed.json").write_text("{")

        with mock.patch.object(behavior, "execute", side_effect=malformed_observation):
            self.assertEqual(self.resume(out), 1)
        report = json.loads((out / "report.json").read_text())
        result = report["results"][0]
        self.assertEqual((result["host"], result["scenario"], result["status"], result["error_kind"]),
                         ("codex", "misleading-bug", "error", "execution"))
        self.assertIn("Expecting property name", result["reason"])
        recorded = json.loads(self.results.read_text())
        self.assertEqual(matrix.status(recorded["hosts"]["codex-cli"], "auto"), "partial")
        row = recorded["hosts"]["codex-cli"]["scenarios"]["misleading-bug"]
        self.assertEqual((row["attempts"], row["repeats"], len(row["errors"])), (1, 0, 1))

    def test_resume_keeps_archived_error_out_of_current_report_and_record(self):
        self.seed("codex-cli")
        out = self.folder / "resume-run"
        folder = out / "codex/misleading-bug-1"
        folder.mkdir(parents=True)
        old = dict(self.passing("codex", "misleading-bug", 1), status="error", reason="old failure")
        (folder / "result.json").write_text(json.dumps(old))
        passed = self.passing("codex", "misleading-bug", 1)

        def assess(folder):
            (folder / "result.json").write_text(json.dumps(passed))
            return passed

        with mock.patch.object(behavior, "execute"), mock.patch.object(behavior, "assess", side_effect=assess):
            self.assertEqual(self.resume(out), 0)
        archives = list((out / "codex").glob("misleading-bug-1.interrupted-*/result.json"))
        self.assertEqual(len(archives), 1)
        self.assertEqual(json.loads(archives[0].read_text()), old)
        report = json.loads((out / "report.json").read_text())
        self.assertEqual(report["results"], [passed])
        recorded = json.loads(self.results.read_text())
        row = recorded["hosts"]["codex-cli"]["scenarios"]["misleading-bug"]
        self.assertEqual((row["attempts"], row["repeats"], row["errors"]), (1, 1, []))
        self.assertEqual(matrix.status(recorded["hosts"]["codex-cli"], "auto"), "supported")


if __name__ == "__main__":
    unittest.main()

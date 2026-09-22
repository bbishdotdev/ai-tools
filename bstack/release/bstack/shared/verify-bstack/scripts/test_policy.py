#!/usr/bin/env python3
"""Check evidence parsing against benign and misleading captured-probe shapes."""
import unittest

from policy import CASES, assess, contamination_reasons, permitted_trace, read_only_shell, trace_for


class PolicyEvidenceTests(unittest.TestCase):
    def test_read_command_wrappers(self):
        commands = ["cat bstack/shared/skills/bstack-router/SKILL.md",
                    "/bin/bash -lc 'sed -n 1,240p AGENTS.md && cat bstack/shared/skills/bstack-router/SKILL.md'",
                    "rg --files bstack | head -20"]
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(read_only_shell(command))

    def test_mutations_and_unknown_shell_execution_are_not_read_evidence(self):
        commands = ["cat AGENTS.md > copy.md", "cat $(touch marker)", "cat `touch marker`",
                    "sed -n 1p -i AGENTS.md", "sed -n 1p -e 'w marker' AGENTS.md",
                    "rg --pre=touch AGENTS.md", "cat AGENTS.md; touch marker", "python3 script.py"]
        commands.extend(["/tmp/cat AGENTS.md", "./cat AGENTS.md", "/tmp/bash -lc 'cat AGENTS.md'"])
        for command in commands:
            with self.subTest(command=command):
                self.assertFalse(read_only_shell(command))

    def test_unknown_provider_tool_is_retained_and_rejected(self):
        trace = trace_for([{"type": "item.completed", "item": {"id": "t1", "type": "mcp_tool_call", "tool": "post_message"}}])
        self.assertEqual(len(trace), 1)
        self.assertEqual(trace[0]["kind"], "mcp_tool_call")
        self.assertFalse(permitted_trace(trace))

    def test_cursor_read_metadata_is_not_an_extra_tool(self):
        trace = trace_for([{"type": "tool_call", "subtype": "completed", "call_id": "c1",
                            "tool_call": {"readToolCall": {"args": {"path": "AGENTS.md"}},
                                          "hookAdditionalContexts": [], "toolCallId": "c1", "startedAtMs": 1}}])
        self.assertEqual(trace[0]["kind"], ["readToolCall"])
        self.assertTrue(permitted_trace(trace))

    def test_claimed_read_does_not_replace_trace(self):
        response = {"playbook": None, "model_policy": "inherit-parent", "execute_fixture": False,
                    "next_actions": ["Rewrite the sentence"], "reason": "I read bstack-router/SKILL.md."}
        checks = assess(CASES["ordinary-prose"], 0, response, [], [], {}, {})
        self.assertFalse(checks["active_router_read_observed"])
        self.assertTrue(checks["policy_playbook"])

    def test_missing_and_string_booleans_fail_audit_assessment(self):
        response = {"model_policy": "inherit-parent", "execute_fixture": False,
                    "next_actions": ["Request transcript evidence"], "reason": "Only a claim is available.",
                    "execution_claim_proven": "false", "verification_claim_proven": False}
        checks = assess(CASES["honest-audit"], 0, response, ["cat bstack/shared/skills/bstack-router/SKILL.md"], [], {}, {})
        self.assertFalse(checks["policy_execution_claim_proven"])
        self.assertTrue(checks["policy_verification_claim_proven"])
        self.assertFalse(checks["policy_independent_review_proven"])

    def test_verifier_symlink_and_evidence_reads_contaminate(self):
        for path in ("bstack/shared/skills/verify-bstack/features/router-policy.md",
                     ".agents/skills/verify-bstack/SKILL.md", ".claude/skills/verify-bstack/scripts/policy.py",
                     ".cursor/skills/verify-bstack/features/README.md", ".bstack/verification/run/report.json"):
            with self.subTest(path=path):
                trace = trace_for([{"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": path}}]}}])
                self.assertIn("verification_or_evidence_reference", contamination_reasons([], trace))

    def test_search_arguments_cannot_bypass_read_gate(self):
        for args in ({"pattern": "model_policy", "path": "."},
                     {"pattern": "model_policy", "path": "bstack"},
                     {"pattern": "model_policy", "glob": "**/*.md"},
                     {"pattern": "model_policy", "path": ".agents/skills/verify-bstack"}):
            with self.subTest(args=args):
                trace = trace_for([{"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "id": "s1", "name": "Grep", "input": args}]}}])
                self.assertTrue(contamination_reasons([], trace))
        clean = [{"kind": "Grep", "arguments": [{"tool": "Grep", "input": {
            "pattern": "model_policy", "path": "bstack/shared/skills/bstack-router"}}]}]
        self.assertEqual(contamination_reasons([], clean), [])

    def test_shell_search_scope_and_ordinary_engineering_reads(self):
        broad = [{"kind": "command_execution", "command": "rg -n 'model_policy' bstack"}]
        scoped = [{"kind": "command_execution", "command": "rg -n 'model_policy' bstack/shared/skills/bstack-router"}]
        self.assertIn("unscoped_shell_content_read", contamination_reasons([], broad))
        self.assertEqual(contamination_reasons([], scoped), [])
        reads = ["cat bstack/shared/skills/bstack-router/SKILL.md", "cat bstack/upstream/pstack/skills/poteto-mode/SKILL.md"]
        checks = assess(CASES["ordinary-prose"], 0, {}, reads, [], {}, {})
        self.assertFalse(checks["no_imported_engineering_access"])

    def test_cursor_shell_uses_same_read_and_scope_checks(self):
        command = "ls bstack/upstream/pstack && rg -n 'inherit-parent' bstack/shared/skills/bstack-router/SKILL.md | head -40"
        trace = trace_for([{"type": "tool_call", "subtype": "completed", "call_id": "s1", "tool_call": {
            "shellToolCall": {"args": {"command": command, "workingDirectory": ""}}}}])
        self.assertEqual(trace[0]["arguments"][0]["input"]["command"], command)
        self.assertTrue(permitted_trace(trace))
        self.assertEqual(contamination_reasons([], trace), [])
        trace[0]["arguments"][0]["input"]["command"] = "rg 'model_policy' bstack"
        self.assertIn("unscoped_shell_content_read", contamination_reasons([], trace))
        trace[0]["arguments"][0]["input"]["command"] = "touch marker"
        self.assertFalse(permitted_trace(trace))

    def test_only_cursor_local_schema_discovery_is_permitted(self):
        trace = trace_for([{"type": "tool_call", "subtype": "completed", "call_id": "m1", "tool_call": {
            "getMcpToolsToolCall": {"args": {"server": "cursor", "pattern": "TodoWrite"}}}}])
        self.assertTrue(permitted_trace(trace))
        trace[0]["arguments"][0]["input"]["server"] = "external-provider"
        self.assertFalse(permitted_trace(trace))
        unknown = trace_for([{"type": "tool_call", "subtype": "completed", "call_id": "m2", "tool_call": {
            "mcpToolCall": {"args": {"server": "cursor", "tool": "TodoWrite"}}}}])
        self.assertFalse(permitted_trace(unknown))

    def test_content_glob_traversal_cannot_hide_verifier_source(self):
        trace = [{"kind": "command_execution", "command": "cat bstack/shared/skills/bstack-router/*/../../*/scripts/policy.py"}]
        self.assertIn("unscoped_shell_content_read", contamination_reasons([], trace))


if __name__ == "__main__":
    unittest.main()

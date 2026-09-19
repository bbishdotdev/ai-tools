# Manual entry and opt-in auto mode

Decision recorded 18 September 2026 and implemented in the consumer release's project controller. See [installation](../INSTALL.md). This development repository's earlier POC still has its previously authorized automatic routing enabled.

New installations should default to manual invocation. Automatic routing should require an explicit opt-in and persist as a local preference for that repository. Keep unslop's existing always-applied behavior independent of the engineering router switch.

Manual and automatic entry should load the same bstack policy. Only activation changes; supporting PStack skills stay on demand. This does not require enabling implicit invocation for the entire imported library.

Consumer commands:

| Intent | Name | Behavior |
| --- | --- | --- |
| Enter the engineering mode manually | `poteto-mode` | Load bstack's adaptation of PStack's Poteto Mode for the current work. |
| Enable auto mode | `bstack-auto on` | Enable the reminder hooks and automatic standing-instruction bindings. |
| Disable auto mode | `bstack-auto off` | Stop future automatic reminders and routing bindings; preserve manual invocation. |
| Inspect configuration | `bstack-auto status` | Report persisted mode, active host bindings, and any reload requirement. |

Use explicit on/off operations rather than a blind toggle so retries are idempotent. Native invocation syntax and plugin namespace can differ by host; those spellings are adapter concerns. A small shared local command should own the state change, with the skill exposing it through each host's supported invocation mechanism.

bstack names the complete collection. Keep Poteto Mode as the engineering workflow's user-facing name and retain attribution to Lauren Tan's PStack. Describe the adapted entry as bstack's adaptation of PStack's Poteto Mode. The bstack auto switch controls collection-wide automatic routing as additional workflows are selected later.

Off covers the automatic path. The controller removes owned router hooks and replaces standing instructions with manual-only guidance while keeping unslop. It stores mode and exact ownership records in gitignored `.bstack/config.json`. Other project instructions point to `.bstack/instructions.md`, keeping one generated instruction source. Updates preflight conflicts and preserve unrelated configuration.

Turning off future injection cannot remove text already present in an active conversation. State that limitation, stop applying bstack automatically to later work, and expose any host reload/new-session requirement. Verify new sessions separately from transitions in an existing session.

The entry should have a portable lowercase identifier without spaces. Current Claude documentation says personal/project skill commands derive from the directory; plugin skill commands can use the frontmatter name with a plugin prefix. The imported `name: Poteto Mode` is therefore a plausible plugin-path issue, not a confirmed explanation for desktop behavior. See [Claude command naming](https://code.claude.com/docs/en/skills#how-a-skill-gets-its-command-name) and [desktop skill support](https://code.claude.com/docs/en/desktop#skills). Preserve the pinned upstream source and normalize bstack's own entry or adapter.

Verification should cover fresh manual default, explicit manual invocation, opt-in across resumed turns, on/on and off/off idempotence, persisted status, opt-out with no fresh reminders, and preservation of unrelated configuration. Run the CLI paths first. Desktop diagnosis remains a separate live test.

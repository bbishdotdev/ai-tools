# Probe set: <product>

One table for every surface. Prompts are typed exactly; scripts never reword them. Give each probe a stable ID so results and fixtures stay comparable across runs. Retire an ID instead of reusing it.

| ID | What the driver does | Exact prompt or action | Expected (graded by code) | Result cells |
| --- | --- | --- | --- | --- |
| P1 | Prompt: agent edit | `<prompt that makes exactly one file>` | <record the grader checks> | <matrix cells> |
| P2 | Prompt: read, edit, and an exact shell command | `<prompt naming the exact command, e.g. echo shell-made > shell-probe.txt>` | <…> | <…> |
| P3 | Prompt: subagent | `<prompt asking for a subagent, with "if you can't, say so and change nothing">` | <…> | <…> |
| P4 | Slash commands and skills | Type `/`, screenshot the menu, run one info-only command, and one read-only skill if listed | research: raw payloads only | fixtures |
| P5 | Interrupted turn | `<prompt producing long streamed output>`, then interrupt once text streams | the turn is stored as interrupted | <…> |
| P6 | Compaction | the surface's compaction command, then `<follow-up prompt>` | <state that must survive> | <…> |
| P7 | Human edit | by hand in a no-AI editor: `<exact line>` | <…> | <…> |
| P8 | Pre-existing session | open the app before `setup`, keep it running, then send P1 from it | <how the product should flag a session it couldn't observe> | <…> |
| P9 | Parent-folder session | open the app on the workspace's parent, prompt an edit inside the workspace | <…> | <…> |

Drop probes the product doesn't care about; keep the IDs of the rest.

**Approval rule:** approve the app's own writes inside the workspace and the exact commands named above. Decline anything else and note it.

**Can't-do rule:** if a surface can't perform a probe (no subagents, no `/` menu, nothing streams), write why in `notes.md` and continue. That is a result.

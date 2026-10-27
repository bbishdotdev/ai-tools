# A visual that earns its space

Each visual should answer one reviewer question: what changed, or how does this part work? Place it beside the explanation it supports. Use as many as distinct questions need, but do not illustrate the same idea twice. Choose the format from the change: show actual UI or output with a real screenshot, compare observed states side by side, or explain hidden behavior with generated art, an annotated data view, an authored diagram, a sequence, or an ERD. Do not make every PR a process flow. When generating an explanation, try Codex CLI first if this project permits Codex to see its code. A CLI being installed does not grant that permission; from another host, check the user's or project's existing provider choice. If Codex is not allowed, start with the current agent's image tool. Only a truly small change, at most two files and 30 changed lines, may omit a visual entirely.

Write a short brief in the consumer's gitignored `.bstack/pr/visual-brief.md`. Include the actual base and changed paths, the old and new behavior, the few relationships the reader needs, and any terms or states that must be exact. Say what the visual must **not** imply. Keep the brief grounded in code; a generated image is explanation, never evidence that a test passed. Give Codex this concrete job in the brief:

```text
Inspect the final diff against <base>. Use your image-generation tool to make one
polished, easy-to-grasp illustration for this point in the PR explanation.
The reader should understand: <one central idea>.
Show: <only the supported steps and relationships>.
Keep these terms exact: <short list>.
Do not imply: <unsupported states, results, code examples, or measurements>.
Choose a visual form that fits the idea; do not default to flowcharts, arrows,
human characters, or a stock metaphor. Use a clear reading order, generous
space, and a few large labels. Avoid tiny text, dense boxes, and fake UI.
Use image generation without writing to the project. Inspect the result and
report its absolute generated-image path. Do not edit project source. If image
generation is unavailable, say why.
```

Ask a headless Codex CLI session to inspect the diff and use its image-generation tool. First run `bstack.py doctor --live --workflow to-pr --project "$PROJECT"` to check that the selected Codex launcher can answer a prompt. This text probe cannot prove image generation is available. Run the actual visual attempt from the consumer project, with a private output path inside `.bstack/pr/`:

```sh
python3 "$PROJECT/.bstack/package/shared/model_cli.py" --project "$PROJECT" run --cli codex -- \
  exec --ephemeral --cd "$PROJECT" --sandbox read-only \
  --output-last-message "$PROJECT/.bstack/pr/visual-result.txt" - \
  < "$PROJECT/.bstack/pr/visual-brief.md"
```

Tell Codex to use image generation, not a hand-coded diagram, for this attempt. Give it room to choose a concrete scene, spatial comparison, architecture view, or other form that makes this particular change easier to grasp without inventing behavior. Avoid example code or data that could be mistaken for the actual diff. Ask it to inspect the rendered output and correct a factual or readability problem. The image tool saves under Codex's generated-images directory; the read-only session reports that path instead of writing into the checkout. If image generation is unavailable, it must say so.

Read the result, **open the actual image**, and compare every label and relationship with the final diff. Reject a pretty but inaccurate or hard-to-read image. One targeted revision is reasonable; do not turn a PR into an illustration project. Copy an accepted image to `.bstack/pr/<name>.png` yourself. If Codex CLI is not allowed, missing, blocked, or produces no usable image, try the current agent's image-generation tool with the same brief and inspection standard. Use an authored SVG or Mermaid diagram when precision is clearer than generated art. For a visible product result, capture the real app or output in its tested state; do not generate a fake screenshot. A text flow or table can explain state elsewhere in the PR but cannot stand in for a visual. Keep a PR over the small-change limit draft if no useful visual can be made.

Use the [publishing media manifest](publishing.md) for attached files, with useful alt text and a self-contained Mermaid fallback for each. Label generated artwork as an illustration. If uploading fails, keep the diagram fallback in the published PR. Never link to a local file path as if reviewers can open it. Read the published body and confirm each image sits beside its explanation; some upload tools append unreferenced files at the end.

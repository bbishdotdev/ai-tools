# A visual that earns its space

The visual should answer one reviewer question: what changed, or how does the new path work? Decide that from the final diff and accepted decisions before choosing a format. Prefer a real UI screenshot when the UI itself is the point. For a process or architectural change that benefits from illustration, try Codex CLI first when this project permits Codex to see its code. A CLI being installed does not grant that permission; from another host, check the user's or project's existing provider choice. If Codex is not allowed, start with the current agent's image tool. Do not add an image merely to fill the section.

Write a short brief in the consumer's gitignored `.bstack/pr/visual-brief.md`. Include the actual base and changed paths, the old and new behavior, the few relationships the reader needs, and any terms or states that must be exact. Say what the visual must **not** imply. Keep the brief grounded in code; a generated image is explanation, never evidence that a test passed. Give Codex this concrete job in the brief:

```text
Inspect the final diff against <base>. Use your image-generation tool to make one
polished, easy-to-grasp illustration for the PR's "For visual nerds" section.
The reader should understand: <one central idea>.
Show: <only the supported steps and relationships>.
Keep these terms exact: <short list>.
Do not imply: <unsupported states, results, code examples, or measurements>.
Use a clear reading order, generous space, a few large labels, and a relatable
process or metaphor where it helps. Avoid tiny text, dense boxes, and fake UI.
Use image generation without writing to the project. Inspect the result and
report its absolute generated-image path. Do not edit project source. If image
generation is unavailable, say why.
```

Ask a headless Codex CLI session to inspect the diff and use its image-generation tool. Run it from the consumer project, with a private output path inside `.bstack/pr/`:

```sh
codex exec --ephemeral --cd "$PROJECT" --sandbox read-only \
  --output-last-message "$PROJECT/.bstack/pr/visual-result.txt" - \
  < "$PROJECT/.bstack/pr/visual-brief.md"
```

Tell Codex to use image generation, not a hand-coded diagram, for this attempt. Give it creative room to choose a simple scene, flow, or metaphor that makes the process relatable without inventing behavior. Avoid example code or data that could be mistaken for the actual diff. Ask it to inspect the rendered output and correct a factual or readability problem. The image tool saves under Codex's generated-images directory; the read-only session reports that path instead of writing into the checkout. If image generation is unavailable, it must say so.

Read the result, **open the actual image**, and compare every label and arrow with the final diff. Reject a pretty but inaccurate or hard-to-read image. One targeted revision is reasonable; do not turn a PR into an illustration project. Copy an accepted image to `.bstack/pr/<name>.png` yourself. If Codex CLI is not allowed, missing, blocked, or produces no usable image, try the current agent's image-generation tool with the same brief and inspection standard. If that is unavailable or still weak, use a real screenshot, authored SVG, Mermaid, a compact table, or a short text flow. Choose the clearest result, even when it is not generated.

Use the [publishing media manifest](publishing.md) for an attached file, with useful alt text and a self-contained plain fallback. Label generated artwork as an illustration. If uploading fails, keep the fallback in the published PR. Never link to a local file path as if reviewers can open it.

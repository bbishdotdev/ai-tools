# A short bstack walkthrough

Teach these ideas in the person's language and at their pace. This is a map for the agent, not a script to recite.

1. Bstack puts planning, engineering, PR work, and optional shared memory in one installed package. It builds on pinned work from PStack and Matt Pocock, with bstack-owned connections and local tooling. The package's `README.md` explains the current feature set and limits.
2. Installation places a small baseline in project instructions and discoverable skill entries that point into one reviewed package. It does not load all skills into every prompt. `unslop` shapes prose. Named skills load when selected.
3. The person can start anywhere: ask about code with `how` or `why`, work through an idea with `grill-me` or `wayfinder`, compare variants with `prototype`, implement a clear task, or use a PR skill. A map, spec, and ticket are useful artifacts, not gates every task must pass.
4. Manual engineering routing is the default, though a question about bstack can still select this guide. `poteto-mode` routes an explicitly invoked engineering task. `bstack-auto on` opts ordinary engineering requests into routing; it does not grant authority to make product decisions or turn on shared memory. The installed package's setup docs cover host-specific hook and session behavior.
5. Wayfinder maps, specs, and tickets can live in the local workspace. `handoff` carries accepted decisions into a fresh context when a phase changes. Personal memory is a separate, optional setup. Each of these survives a single chat differently; explain the distinction if the person asks.

Then give one concrete route relevant to their likely work, using [common routes](routes.md). If they want a tour with no task in mind, use two small examples:

- "Fix the login error" can go straight into an engineering workflow. With auto mode on, an ordinary request can route there. With auto off, the person can invoke `poteto-mode`. A Wayfinder map or ticket is optional.
- "We're considering a new meal-planning feature" can start with `grill-me`. If choices span sessions, use `wayfinder`; if a screen needs comparison, use `prototype`. Accepted scope can become a spec or tickets before `implement`. A `handoff` can move the accepted result into a fresh context.

Stop there and let them choose the next topic. Avoid implying that an optional external integration or model role is already configured.

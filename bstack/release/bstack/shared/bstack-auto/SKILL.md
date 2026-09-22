---
name: bstack-auto
description: Explicitly enable, disable, or inspect bstack automatic routing for this project.
disable-model-invocation: true
metadata:
  package: bstack
---

# Automatic routing

Require an explicit `on`, `off`, or `status` argument. If the argument is missing or invalid, show the choices below and stop without running the controller:

- `bstack-auto on` enables automatic routing.
- `bstack-auto off` disables automatic routing.
- `bstack-auto status` checks the saved mode without changing it.

Use the host's skill prefix, such as `$bstack-auto` in Codex or `/bstack-auto` in slash-command hosts. Do not infer a mode or toggle the current setting.

With a valid argument, resolve the [controller](../../scripts/bstack.py) to its absolute path and run it for the requested project:

```sh
python3 <absolute-package-path>/scripts/bstack.py auto status --project <project-root>
```

Replace `status` with the requested mode. Report the configured mode and the controller's `notice`. Only request a fresh session when `fresh_session_required` is true. A read-only status check or an unchanged mode does not require a new session.

`native_hook_trust: not_checked` means unknown, not untrusted. `auto: true` confirms configuration, not hook execution or router delivery. Do not claim those were verified by `auto status`. Follow the controller's Codex terminal CLI instructions when hook review applies; do not tell users to run `/hooks` in the desktop chat.

Turning auto off preserves direct skill invocation and unslop. It cannot remove instructions already loaded in a conversation.

---
name: bstack-auto
description: Explicitly enable, disable, or inspect bstack automatic routing for this project.
disable-model-invocation: true
metadata:
  package: bstack
---

# Automatic routing

Resolve the [controller](../../scripts/bstack.py) to its absolute path. Run it with the user's explicit `on`, `off`, or `status` argument. With no argument, use `status`. Do not infer permission to enable automatic routing.

```sh
python3 <absolute-package-path>/scripts/bstack.py auto status --project <project-root>
```

Replace `status` with the requested mode. Report the resulting mode and any session reload or native hook trust requirement. Turning auto off preserves direct skill invocation and unslop. It cannot remove instructions already loaded in a conversation.

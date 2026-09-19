---
name: setup-bstack
description: Configure or check bstack's local project bindings and selected agent tools.
disable-model-invocation: true
metadata:
  package: bstack
---

# Set up bstack

Resolve the installed package from the [controller](../../scripts/bstack.py). Run it with the requested project and hosts:

```sh
python3 <absolute-package-path>/scripts/bstack.py setup --project <project-root> --hosts codex claude cursor grok
```

Setup creates direct public skill entries and project instructions. It preserves an existing auto preference and defaults to manual routing for a new installation. Do not enable auto mode without the user's request. Run `doctor --project <project-root>` to check the resulting package and bindings.

This replaces PStack's host-specific model setup. Do not write global model rules or select providers as part of setup. The default delegation policy remains `inherit-parent`. See [the package guide](../../README.md) for updates and removal.

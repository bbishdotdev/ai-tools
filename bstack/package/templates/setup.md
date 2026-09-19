# Local bstack setup

This is bstack's replacement for PStack's host-specific `setup-pstack` workflow. Do not write global Cursor model rules or choose provider models as part of setup. The bstack default model policy is `inherit-parent`.

Resolve the installed capsule from the [controller](../../scripts/bstack.py). Run it with the requested consumer project:

```sh
python3 <installed-poteto-mode>/scripts/bstack.py setup --project <project-root> --hosts codex claude cursor grok
```

Setup installs the local writing binding and control entries. It preserves existing auto mode and defaults to manual mode on first setup. Only an explicit user request enables `auto on`. The supported controls and uninstall procedure are in the [package guide](../../README.md).

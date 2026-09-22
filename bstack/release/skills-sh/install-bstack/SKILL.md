---
name: install-bstack
description: Install or update the bundled bstack collection and its public skills in a local project.
disable-model-invocation: true
metadata:
  package: bstack
---

# Install bstack

This skill transports the reviewed bstack release. Its [archive](assets/bstack.zip) contains the package, dependencies, customizations, source manifest, and license notices. Do not fetch upstream skills or modify this distributor-owned archive.

Resolve [scripts/install.py](scripts/install.py) to its absolute path, then run it for the requested project and hosts:

```sh
python3 <installed-install-bstack>/scripts/install.py --project <project-root> --hosts codex claude cursor grok
```

The installer validates and copies the package to `.bstack/package/`, creates direct skill entries under `.agents/skills/`, and connects the selected hosts. All engineering entrypoints remain manual initially; automatic routing requires an explicit opt-in. Existing configuration and ownership conflicts must be respected.

After installation, run `python3 <project-root>/.bstack/package/scripts/bstack.py doctor --project <project-root>`. Report its results and any reload or native hook trust requirements. The installed package is independent of this transport skill and the development checkout. Keep this skill intact so its distributor can update or remove it normally.

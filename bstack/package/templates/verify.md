# Verify an installed bstack package

This is bstack's maintainer verification entry. It does not activate engineering mode or authorize implementation work.

Run the installed [controller](../../../../scripts/bstack.py) with `doctor --project <project-root>` to check package integrity and project bindings.

For a fresh installation probe, resolve [scripts/installation.py](scripts/installation.py) to its absolute installed path and run it from the chosen project directory. It creates isolated consumer projects, installs this bundled capsule through the offline controller, and records evidence under that directory's `.bstack/verification/`. The default probe requires no skills.sh or upstream download.

```sh
python3 <installed-poteto-mode>/content/shared/skills/verify-bstack/scripts/installation.py
```

Use `--methods offline symlink copy` to also test skills.sh's symlink and copy installation paths when that installer is available. These paths install the same reviewed bundled files, not upstream latest. Use `--help` for the available options. Add `--live` only when the user requests provider-backed CLI verification and authorizes its model usage. The live suite checks manual entry, opt-in, resumed turns, opt-out, and installed router reads on detected clients. File integrity, hook emission, observed model reads, and correct answers are separate claims. Preserve unavailable or trust-blocked checks as limitations.

The other packaged verifier modules support this installation probe. Their standalone source-checkout commands are not a consumer interface. Pin/layer adoption checks belong in the maintained bstack source repository.

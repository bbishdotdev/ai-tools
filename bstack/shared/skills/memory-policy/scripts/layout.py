"""Resolve the shared memory runtime and state without tying them to a project."""
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    home: Path
    portable: bool = False

    @classmethod
    def load(cls, home, portable=False):
        from memory_files import SyncError, read_file
        layout = cls(home, True)
        raw = read_file(layout.manifest)
        if raw is not None:
            try:
                data = json.loads(raw)
            except (ValueError, UnicodeError) as error:
                raise SyncError('Malformed portable memory installation manifest') from error
            if not isinstance(data, dict) or data.get('schema') != 1 or data.get('name') != 'bstack-memory':
                raise SyncError('Unsupported portable memory installation manifest')
            portable = True
        return cls(home, portable)

    @property
    def root(self):
        return self.home / '.local/share/bstack/memory'

    @property
    def runtime(self):
        return self.root / 'runtime' if self.portable else self.home / 'Work/.agents/skills/memory-policy'

    @property
    def state(self):
        return self.root / 'state' if self.portable else self.home / 'Work/.agents/memory-sync'

    @property
    def manifest(self):
        return self.root / 'install.json'

    @property
    def config(self):
        return self.state / 'config.json'

    @property
    def cursor(self):
        return self.state / 'cursor'

    @property
    def claude(self):
        return self.state / 'claude'

    @property
    def lock(self):
        return self.state / 'lock'

    @property
    def backups(self):
        return self.state / 'backups'

    @property
    def setup_hint(self):
        return 'preview portable.py setup, then apply its reviewed --apply-plan digest' if self.portable else 'run install.py --activate-sync'


def component_source():
    return Path(__file__).resolve().parent.parent


def policy_source(source=None):
    source = source or component_source()
    portable = source / 'policy.md'
    return portable if portable.exists() else source.parents[1] / 'rules/memory-policy.md'

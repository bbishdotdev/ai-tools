import contextlib
import os
import sqlite3
import uuid

KANBAN_DDL = (
    'CREATE TABLE specs (id TEXT PRIMARY KEY, map_id TEXT REFERENCES maps(id), data TEXT NOT NULL)',
    'CREATE TABLE spec_revisions (spec_id TEXT NOT NULL REFERENCES specs(id), revision INTEGER NOT NULL, data TEXT NOT NULL, PRIMARY KEY(spec_id,revision))',
    'CREATE TABLE tickets (id TEXT PRIMARY KEY, map_id TEXT REFERENCES maps(id), spec_id TEXT REFERENCES specs(id), data TEXT NOT NULL)',
    'CREATE TABLE ticket_relationships (kind TEXT NOT NULL, source TEXT NOT NULL REFERENCES tickets(id), target TEXT NOT NULL REFERENCES tickets(id), PRIMARY KEY(kind,source,target), CHECK(source != target))',
    'CREATE INDEX specs_map ON specs(map_id)',
    'CREATE INDEX tickets_map ON tickets(map_id)',
    'CREATE INDEX tickets_spec ON tickets(spec_id)',
    'CREATE INDEX ticket_relationships_target ON ticket_relationships(target,kind)',
)


def backup_v1(db, path):
    backup = path.with_name('wayfinder.schema-v1.sqlite3')
    temporary = backup.with_name('.' + backup.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with contextlib.closing(sqlite3.connect(temporary)) as destination:
            os.chmod(temporary, 0o600)
            db.backup(destination)
        with temporary.open('rb') as stream:
            os.fsync(stream.fileno())
        os.replace(temporary, backup)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def upgrade(db, path):
    """Caller holds the repository/standalone init lock and verified identity."""
    backup_v1(db, path)
    db.execute('BEGIN IMMEDIATE')
    try:
        if db.execute('PRAGMA user_version').fetchone()[0] != 1:
            raise sqlite3.DatabaseError('Schema changed during migration')
        for statement in KANBAN_DDL:
            db.execute(statement)
        db.execute('PRAGMA user_version=2')
        db.commit()
    except BaseException:
        db.rollback()
        raise

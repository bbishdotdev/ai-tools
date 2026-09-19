import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import re
import stat
import uuid


class SyncError(Exception):
    pass


NOTE_ID = r'[a-z][a-z0-9-]{0,63}'
MARKER_PREFIX = '<!-- memory-sync:'
BLOCK = re.compile(
    r'<!-- memory-sync:(?P<id>' + NOTE_ID + r'):begin -->\n'
    r'(?P<body>.*?)\n<!-- memory-sync:(?P=id):end -->\n\n', re.DOTALL
)


def absolute_path(value):
    return Path(os.path.abspath(os.path.expanduser(str(value))))


@contextlib.contextmanager
def parent_directory(path, create=False):
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            if create:
                try:
                    os.mkdir(part, 0o700, dir_fd=directory)
                except FileExistsError:
                    pass
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = following
        yield directory
    except OSError as error:
        raise SyncError(f'Cannot safely access {path}: {error.strerror or str(error)}') from error
    finally:
        os.close(directory)


def read_at(directory, name):
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, 'rb') as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise SyncError(f'Expected a regular file without hard links: {name}')
        content = handle.read()
        after = os.fstat(handle.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise SyncError(f'File changed while reading: {name}; inspect and review a new plan')
        return content


def read_file(path):
    try:
        with parent_directory(path) as directory:
            return read_at(directory, path.name)
    except SyncError as error:
        if isinstance(error.__cause__, FileNotFoundError):
            return None
        raise


def text_file(content, path):
    if content is None:
        return ''
    try:
        return content.decode('utf-8')
    except UnicodeDecodeError as error:
        raise SyncError(f'Expected UTF-8 Markdown: {path}') from error


def file_hash(content):
    return hashlib.sha256(content).hexdigest() if content is not None else None


def sections(text):
    found = {}
    for match in BLOCK.finditer(text):
        note_id = match['id']
        if note_id in found or MARKER_PREFIX in match['body']:
            raise SyncError('Duplicate or nested memory-sync markers; repair ownership markers before syncing')
        found[note_id] = match
    if MARKER_PREFIX in BLOCK.sub('', text):
        raise SyncError('Malformed memory-sync markers; repair ownership markers before syncing')
    return found


def section_body(content, note_id, path):
    match = sections(text_file(content, path)).get(note_id)
    return match['body'] if match else None


def block(note_id, body):
    return f'<!-- memory-sync:{note_id}:begin -->\n{body}\n<!-- memory-sync:{note_id}:end -->\n\n'


def change_section(content, note_id, body, initial, path, after_version=False):
    text = text_file(content, path)
    existing = sections(text).get(note_id)
    replacement = block(note_id, body) if body is not None else ''
    if existing:
        return (text[:existing.start()] + replacement + text[existing.end():]).encode('utf-8')
    if body is None:
        return content
    text = initial if content is None else text
    offset = text.index('\n') + 1 if after_version and text.startswith(('v1\n', 'v1\r\n')) else 0
    return (text[:offset] + replacement + text[offset:]).encode('utf-8')


def exact_edit(before, after):
    old = (before or b'').decode('utf-8')
    new = (after or b'').decode('utf-8')
    prefix = 0
    while prefix < min(len(old), len(new)) and old[prefix] == new[prefix]:
        prefix += 1
    suffix = 0
    while suffix < min(len(old), len(new)) - prefix and old[-suffix - 1] == new[-suffix - 1]:
        suffix += 1
    return {
        'byte_offset': len(old[:prefix].encode('utf-8')),
        'remove': old[prefix:len(old) - suffix],
        'insert': new[prefix:len(new) - suffix],
    }


def atomic_change(path, before, after):
    with parent_directory(path, create=after is not None) as directory:
        if read_at(directory, path.name) != before:
            raise SyncError(f'Drift at {path}; inspect and review a new plan')
        if after is None:
            os.unlink(path.name, dir_fd=directory)
            os.fsync(directory)
            return
        temporary = f'.memory-sync-{uuid.uuid4().hex}.tmp'
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
            with os.fdopen(descriptor, 'wb') as handle:
                handle.write(after)
                handle.flush()
                os.fsync(handle.fileno())
            if read_at(directory, path.name) != before:
                raise SyncError(f'Drift at {path}; inspect and review a new plan')
            os.replace(temporary, path.name, src_dir_fd=directory, dst_dir_fd=directory)
            os.fsync(directory)
        finally:
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass


@contextlib.contextmanager
def sync_lock(home):
    path = home / 'Work/.agents/memory-sync/lock'
    with parent_directory(path, create=True) as directory:
        descriptor = os.open(path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=directory)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise SyncError(f'Unsafe synchronization lock: {path}')
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise SyncError('Another memory-sync apply is running; retry after it finishes') from error
            yield
        finally:
            os.close(descriptor)

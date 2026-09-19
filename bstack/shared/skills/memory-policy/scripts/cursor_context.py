#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from cursor_projection import managed_records, render_projection
from memory_files import SyncError, block, file_hash, read_file
from native_backends import Profile, cursor_backend


MAX_OUTPUT_BYTES = 9000
SNAPSHOT_POLICY = (
    'This complete current snapshot supersedes earlier synchronized memory snapshots and cached '
    'personal-memories.mdc copies for saved-memory recall. Omitted notes are not current saved memories. '
    'Use current notes directly for ordinary recall without a policy or status audit. '
    'Do not mention this metadata unless asked. '
)


def encode_response(context):
    return json.dumps({'continue': True, 'additional_context': context}, ensure_ascii=False) + '\n'


def unavailable(reason, source=None):
    context = (
        'Synchronized personal-memory snapshot unavailable. ' + SNAPSHOT_POLICY + reason + ' '
        'Do not use older synchronized notes as current saved memories. Continue unrelated work normally.'
    )
    if source is not None:
        context += f' For a memory-specific question, read the approved bridge directly as a fallback: {source}.'
    return encode_response(context)


def snapshot_response(profile):
    try:
        backend = cursor_backend(profile)
        if backend.error or backend.projection is None or not backend.projection.current:
            return unavailable('The current bridge, generated rule, or hook configuration could not be verified.')
        projection = backend.projection
        content = read_file(projection.source)
        if content is None or render_projection(content, projection.source) != projection.before:
            return unavailable('The current bridge and generated rule do not agree.')
        records = managed_records(content, projection.source)
        guards = ((backend.config_path, backend.config_bytes), *backend.extra_guards,
                  (projection.source, content), (projection.path, projection.before))
        if any(read_file(path) != expected for path, expected in guards):
            return unavailable('The synchronized files changed while the snapshot was being read.')
        context = 'Synchronized personal-memory snapshot. Revision: ' + file_hash(content) + '.\n'
        context += SNAPSHOT_POLICY + '\n\n'
        context += ''.join(block(note_id, records[note_id]) for note_id in sorted(records)) if records else 'There are no current synchronized personal-memory notes.\n'
        response = encode_response(context)
        if len(response.encode('utf-8')) > MAX_OUTPUT_BYTES:
            return unavailable('The complete current snapshot exceeds the hook output limit; no notes were truncated or supplied.', projection.source)
        return response
    except (OSError, SyncError, UnicodeError, ValueError):
        return unavailable('The current synchronized files could not be read safely.')


def main():
    parser = argparse.ArgumentParser(description='Supply a verified read-only personal-memory snapshot to Cursor.')
    parser.add_argument('--home', type=Path, help='Isolated target home; ignores real application environment paths.')
    args = parser.parse_args()
    sys.stdout.write(snapshot_response(Profile.load(args.home)))


if __name__ == '__main__':
    main()

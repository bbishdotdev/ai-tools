import argparse
from datetime import datetime, timezone

from . import store


def visible(notes):
    return sorted((note for note in notes if not note.get("archived")), key=lambda note: note["updated"], reverse=True)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="notes")
    parser.add_argument("--file", default=str(store.DEFAULT))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    add = commands.add_parser("add")
    add.add_argument("title")
    add.add_argument("--tag", action="append", default=[])
    args = parser.parse_args(argv)
    notes = store.load(args.file)
    if args.command == "add":
        notes.append({"title": args.title, "tags": args.tag, "archived": False,
                      "updated": datetime.now(timezone.utc).isoformat()})
        store.save(notes, args.file)
        return
    for note in visible(notes):
        print(f"{note['title']}  [{', '.join(note['tags'])}]")


if __name__ == "__main__":
    main()

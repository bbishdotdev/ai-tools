import argparse

from .summary import load, render, summarize


def main(argv=None):
    parser = argparse.ArgumentParser(prog="invoices")
    commands = parser.add_subparsers(dest="command", required=True)
    summary = commands.add_parser("summary")
    summary.add_argument("path")
    args = parser.parse_args(argv)
    print(render(summarize(load(args.path))))


if __name__ == "__main__":
    main()

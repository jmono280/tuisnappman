import argparse
import os
import sys

from tuisnappman.app import TuiSnappMan
from tuisnappman.runner import Runner


def main() -> None:
    parser = argparse.ArgumentParser(prog="tuisnappman", description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="no ejecuta los comandos que modifican (borrar, crear)",
    )
    args = parser.parse_args()
    if os.geteuid() != 0 and not args.dry_run:
        sys.exit("Necesita root. Ejecuta: sudo .venv/bin/python -m tuisnappman")
    TuiSnappMan(Runner(dry_run=args.dry_run)).run()


if __name__ == "__main__":
    main()

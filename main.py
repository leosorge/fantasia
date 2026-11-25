"""Preparazione del feed, conferma dopo deploy e anteprima locale."""
import argparse
import sys
from pathlib import Path

from drive_io import DriveManager, supported
from expert_choice import choose_and_adapt, run_expert
from pager import load, receipt, rotate, save, write


def prepare(drive, root):
    root = Path(root)
    state = load(root / "state_12.json")
    count = 0
    for item in drive.list_new():
        key = receipt(item)
        if key in state["processed"] or not supported(item):
            continue
        try:
            payload = choose_and_adapt(drive.read(item), item["name"])
        except (UnicodeError, ValueError) as exc:
            print(f'{item["name"]}: {exc} — resta in coda.', file=sys.stderr)
            continue
        entry = run_expert(payload) | {"key": key}
        count += rotate(state, entry, drive.archive)
    save(state, root)
    return count


def acknowledge(drive, root):
    state = load(Path(root) / "state_12.json")
    return sum(drive.acknowledge(item) for item in drive.list_new()
               if receipt(item) in state["processed"])


class DemoDrive:
    """Sorgente locale con gli stessi metodi dell'adattatore Drive."""
    def __init__(self, root):
        self.root = root
        self.files = sorted((root / "new").glob("*.txt"))

    def list_new(self):
        return [{"id": file.name, "version": "1", "name": file.name,
                 "mimeType": "text/plain"} for file in self.files]

    def read(self, item):
        return (self.root / "new" / item["id"]).read_text(encoding="utf-8-sig")

    def archive(self, key, filename, html):
        target = self.root / "old" / filename
        if not target.exists():
            write(target, html)


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check-drive", "prepare", "ack", "demo"])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "demo":
        print(f"{prepare(DemoDrive(args.root), args.root)} card preparate.")
        return
    drive = DriveManager()
    drive.validate()
    if args.command == "check-drive":
        print(f"Cartelle raggiungibili. {len(drive.list_new())} elementi in coda.")
    elif args.command == "prepare":
        print(f"{prepare(drive, args.root)} card preparate.")
    else:
        print(f"{acknowledge(drive, args.root)} sorgenti rimossi dalla coda.")


if __name__ == "__main__":
    cli()

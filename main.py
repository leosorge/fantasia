"""Preparazione del feed, conferma dopo deploy e anteprima locale."""
import argparse
import json
import re
import sys
from pathlib import Path

from drive_io import DriveManager, supported
from expert_choice import choose_and_adapt, parse_source, run_expert, update_legacy_3d
from pager import initialize_feed, load, receipt, rotate_batch, save, save_state, today, write


def repair_legacy_news(state):
    """Recover a structured article previously mistaken for a carousel."""
    for item in state["slots"]:
        if item["format_code"] != "3" or not item["title"].startswith("TITOLO "):
            continue
        node = re.search(r'id="slides">(.*?)</script>', item["html"], re.S)
        if not node:
            continue
        slides = json.loads(node[1])["slides"]
        raw = "\n\n".join(slide["text"] for slide in slides if slide["text"])
        fields, _ = parse_source(raw)
        if "sommario" in fields:
            item.update(run_expert(choose_and_adapt(raw, "notizia", forced_choice="1")))


def prepare(drive, root):
    root = Path(root)
    state = load(root / "state_12.json")
    repair_legacy_news(state)
    initialize_feed(state, root / "index.html", drive.archive)
    for card in state["slots"]:
        if card["format_code"].startswith("5."):
            card["html"] = update_legacy_3d(card["html"])
    entries = []
    seen = set(state["processed"])
    for item in drive.list_new():
        if not supported(item) or receipt(item) in seen:
            continue
        try:
            body = drive.read(item)
            key = receipt(item, body)
            if key in seen:
                continue
            payload = choose_and_adapt(body, item["name"])
        except (UnicodeError, ValueError) as exc:
            print(f'{item["name"]}: {exc} — resta in coda.', file=sys.stderr)
            continue
        entries.append(run_expert(payload) | {"key": key})
        seen.add(key)
    rotate_batch(state, entries, drive.archive)
    save(state, root)
    return len(entries)


def acknowledge(drive, root):
    state = load(Path(root) / "state_12.json")
    count = 0
    for item in drive.list_new():
        if not supported(item):
            continue
        known = receipt(item) in state["processed"]
        if not known:
            try:
                known = receipt(item, drive.read(item)) in state["processed"]
            except (UnicodeError, ValueError):
                continue
        if known:
            count += drive.acknowledge(item)
    return count


def mark_published(root):
    state = load(Path(root) / "state_12.json")
    published_on = today()
    for card in state["slots"]:
        card.setdefault("published_on", published_on)
    save_state(state, root)


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
        if target.exists():
            if target.read_text(encoding="utf-8") == html:
                return
            target = target.with_name(f"{target.stem}_{key[:8]}{target.suffix}")
        write(target, html)


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["check-drive", "prepare", "mark-published", "ack", "demo"])
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    if args.command == "demo":
        print(f"{prepare(DemoDrive(args.root), args.root)} card preparate.")
        return
    if args.command == "mark-published":
        mark_published(args.root)
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

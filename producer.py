"""Accoda brevi segnalazioni YouTube dai metadati raccolti da intersearQ."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from drive_io import DriveManager
from translate_it import ItalianTranslator, TranslationError

HERE = Path(__file__).resolve().parent


def notify(video, translator):
    video_id = video["id"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id):
        return None
    title, description = translator.translate(video["title"], video.get("description", ""))
    one_line = lambda text: " ".join(text.split())
    seconds = video["seconds"]
    metadata = (f'{one_line(video["channel"])} ha pubblicato questo video il {video["published"][:10]}. '
                f'Durata {seconds//60} min {seconds%60} s.')
    copy = f'Titolo: {one_line(title)}\nFonte: https://www.youtube.com/watch?v={video_id}\n\n'
    if description.strip():
        return copy + description.strip() + "\n\n" + metadata
    return copy + metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels")
    parser.add_argument("--max-new", default=3, type=int)
    args = parser.parse_args()
    if args.max_new < 1:
        parser.error("--max-new deve essere almeno 1")
    drive = DriveManager()
    drive.validate()
    with TemporaryDirectory() as temporary:
        result = Path(temporary) / "videos.json"
        command = ["node", str(HERE / "intersearQ.mjs"), "--json", "--output", str(result)]
        if args.channels:
            command += ["--channels", args.channels]
        subprocess.run(command, check=True)
        videos = json.loads(result.read_text(encoding="utf-8"))
    count = 0
    translator = ItalianTranslator()
    for video in videos:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video["id"]) or drive.has_video(video["id"]):
            continue
        try:
            content = notify(video, translator)
        except TranslationError as exc:
            print(f'Video {video["id"]} non accodato: {exc}.')
            continue
        if content and drive.enqueue_video(video["id"], f'youtube_{video["id"]}.txt', content):
            count += 1
            if count == args.max_new:
                break
    print(f"{count} segnalazioni accodate.")


if __name__ == "__main__":
    main()

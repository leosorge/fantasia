"""Accoda brevi segnalazioni YouTube dai metadati raccolti da intersearQ."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from drive_io import DriveManager

HERE = Path(__file__).resolve().parent


def notify(video):
    video_id = video["id"]
    if not re.fullmatch(r"[a-zA-Z0-9_-]{11}", video_id):
        return None
    one_line = lambda text: " ".join(text.split())
    topics = ", ".join(dict.fromkeys(tag["term"] for tag in video["tags"]))
    seconds = video["seconds"]
    return (f'Titolo: {one_line(video["title"])}\n'
            f'Fonte: https://www.youtube.com/watch?v={video_id}\nFormato: 1\n\n'
            f'{one_line(video["channel"])} ha pubblicato questo video il {video["published"][:10]}. '
            f'Durata {seconds//60} min {seconds%60} s. Termini rilevati: {one_line(topics)}.')


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
    for video in videos:
        content = notify(video)
        if content and drive.enqueue_video(video["id"], f'youtube_{video["id"]}.txt', content):
            count += 1
            if count == args.max_new:
                break
    print(f"{count} segnalazioni accodate.")


if __name__ == "__main__":
    main()

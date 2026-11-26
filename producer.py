"""Accoda brevi segnalazioni YouTube dai metadati raccolti da intersearQ."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from drive_io import DriveManager
from expert_choice import clip, cloze, numeric_trail
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
    title = one_line(title)
    channel = one_line(video["channel"])
    date = video["published"][:10]
    description = "\n".join(
        f"— {line}" if re.fullmatch(
            r"TITOLO|FONTE|URL|SOMMARIO|TESTO|CAROUSEL|QUIZ|GIOCO|3D|FRASE[- ]SINTESI|FORMATO|CATEGORIE",
            line.strip(), re.I,
        ) else line
        for line in description.strip().splitlines()
    )
    introduction = f'Il video «{title}» è stato pubblicato su YouTube da {channel}.'
    content_summary = next(
        (line.strip() for line in re.split(r"(?<=[.!?])\s+|\n+", description)
         if len(line.strip()) >= 35 and not re.search(r"https?://", line)),
        "",
    )
    synopsis = clip(content_summary, 280) if content_summary else introduction
    body = "\n\n".join(part for part in (introduction, description, metadata) if part)
    trail = numeric_trail(description)
    game = "\n\n".join(
        "\n".join([f'Frase: {question["t"].strip()}',
                   *(f"{letter}: {value}" for letter, value in question["o"].items()),
                   f'Risposta: {question["answer"]}'])
        for question in trail
    )
    scene = clip(f"{title}. {synopsis}" if content_summary else title, 360)
    quiz = (f"Domanda: In che anno {channel} ha pubblicato il video?\n"
            f"A: {int(date[:4]) - 1}\nB: {date[:4]}\nC: {int(date[:4]) + 1}\n"
            f"Risposta: B\nSpiegazione: La data di pubblicazione è {date}.")
    questions = cloze(description)[:3]
    if questions:
        quiz = "\n\n".join(
            "\n".join([f'Domanda: {item["t"].strip()}',
                       *(f"{letter}: {option}" for letter, option in zip("ABC", item["o"])),
                       f'Risposta: {"ABC"[item["answer"]]}',
                       f'Spiegazione: {item["t"].replace("____", item["o"][item["answer"]], 1).strip()}'])
            for item in questions
        )
    categories = dict.fromkeys(tag["category"] for tag in video.get("tags", []) if tag.get("category"))
    sections = [
        ("TITOLO", title),
        ("FONTE", f"https://www.youtube.com/watch?v={video_id}"),
        ("CATEGORIE", "\n".join(categories)),
        ("SOMMARIO", synopsis),
        ("TESTO", body),
        ("CAROUSEL", f"Il tema del video\n{synopsis}\n\n"
                     f"La pubblicazione\nIl video è uscito sul canale {channel} il {date}.\n\n"
                     f"La durata\nIl video dura {seconds//60} minuti e {seconds%60} secondi."),
        ("QUIZ", quiz),
        ("GIOCO", game),
        ("3D", f"Scena: {scene}\nSoggetto: {title}\nDidascalia: {synopsis}"),
        ("FRASE-SINTESI", synopsis),
    ]
    return "\n\n".join(f"{heading}\n{value}".rstrip() for heading, value in sections) + "\n"


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

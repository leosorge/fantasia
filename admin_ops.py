"""Apply requests confirmed via GitHub Actions."""
import hashlib
import json
import os
import re
from pathlib import Path
from uuid import UUID

from drive_io import DriveManager
from expert_choice import choose_and_adapt, parse_source, run_expert
from pager import archive_card, load, rotate_batch, save
from translate_it import ItalianTranslator


def translate_payload(payload, target):
    translator = ItalianTranslator(target)
    payload["title"], payload["body"] = translator.translate(payload["title"], payload["body"])
    if translator.tokenizer is None:
        return
    for key in ("plain", "summary", "synthesis", "scene_details"):
        payload[key] = translator.translate_text(payload[key])
    payload["blocks"] = [translator.translate_text(block) for block in payload["blocks"]]
    for question in payload["questions"]:
        parts = re.split(r"(_{3,4})", question["t"])
        question["t"] = "".join(part if part.startswith("___") else translator.translate_text(part)
                                for part in parts)
        if "explanation" in question:
            question["explanation"] = translator.translate_text(question["explanation"])
        if isinstance(question["o"], list):
            question["o"] = [translator.translate_text(value) for value in question["o"]]


def apply_request(drive, root, request):
    root = Path(root)
    state = load(root / "state_12.json")
    action = request.get("action")
    card_key = request.get("key", "")
    if not re.fullmatch(r"[0-9a-f]{64}", card_key):
        raise ValueError("Identificativo scheda non valido")
    if action == "remove":
        for card in state["slots"]:
            if card["key"] == card_key:
                archive_card(card, drive.archive)
                state["slots"].remove(card)
                for i, remaining in enumerate(state["slots"], 1):
                    remaining["position"] = i
                break
    elif action == "publish":
        key = hashlib.sha256(f'admin:{UUID(request["id"])}'.encode()).hexdigest()
        if key not in state["processed"]:
            if not any(card["key"] == card_key for card in state["slots"]):
                raise ValueError("La scheda originale non è più nel feed")
            body, code, language = request["text"], request["format"], request["language"]
            if language not in {"it", "en", "zh", "ja"} or code not in "1 2 3 4 5 6".split():
                raise ValueError("Lingua o formato non ammessi")
            if not isinstance(body, str) or len(body.encode()) > 45_000:
                raise ValueError("Sorgente oltre 45 KB")
            fields, _ = parse_source(body)
            if not fields.get("news_v1"):
                raise ValueError("Inserisci un sorgente Fantasia News v1")
            payload = choose_and_adapt(body, "admin", code)
            translate_payload(payload, language)
            card = run_expert(payload)
            card["html"] = card["html"].replace('<html lang="it">', f'<html lang="{language}">', 1)
            drive.archive_text(key, body)
            rotate_batch(state, [card | {"key": key, "source_archived": True,
                                         "output_language": language}], drive.archive)
    else:
        raise ValueError("Azione amministrativa sconosciuta")
    save(state, root)


if __name__ == "__main__":
    drive = DriveManager()
    drive.validate()
    apply_request(drive, Path("."), json.loads(os.environ["FANTASIA_ADMIN_REQUEST"]))

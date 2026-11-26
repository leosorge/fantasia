"""Apply requests confirmed via GitHub Actions."""
import hashlib
import json
import os
import re
from pathlib import Path
from uuid import UUID

from drive_io import DriveManager
from expert_choice import choose_and_adapt, parse_source, run_expert
from pager import archive_card, load, rotate_batch, save, topic_groups, write
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


def update_categories(drive, root, request):
    path = root / "Qlist.txt"
    current = topic_groups(path)
    rows = request.get("groups")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100:
        raise ValueError("Servono da 1 a 100 categorie")
    groups = {}
    for row in rows:
        name, terms = row["name"].strip(), row["terms"]
        if (not name or len(name) > 100 or re.search(r"[\r\n;,]", name)
                or name.casefold() == "canali seguiti" or name.casefold() in {key.casefold() for key in groups}):
            raise ValueError(f"Nome categoria non valido o duplicato: {name}")
        if not isinstance(terms, list) or not 1 <= len(terms) <= 300:
            raise ValueError(f"Inserisci almeno una parola chiave per {name}")
        terms = list(dict.fromkeys(term.strip() for term in terms))
        if any(not term or len(term) > 160 or re.search(r"[\r\n,]", term) for term in terms):
            raise ValueError(f"Parola chiave non valida in {name}")
        groups[name] = terms
    if list(current.items()) != list(groups.items()) and current != request.get("previous"):
        raise ValueError("Le categorie sono cambiate nel frattempo. Ricarica il pannello.")
    lines = []
    for number, (name, terms) in enumerate(groups.items(), 1):
        lines.append(f"{number}. {name}")
        by_length = []
        for term in terms:
            length = len(term.split())
            if not by_length or by_length[-1][0] != length:
                by_length.append((length, []))
            by_length[-1][1].append(term)
        lines.extend(f"{length} {'parola' if length == 1 else 'parole'}: {', '.join(values)}"
                     for length, values in by_length)
        lines.append("")
    drive.sync_category_specification(list(groups))
    write(path, "\n".join(lines))


def apply_request(drive, root, request):
    root = Path(root)
    state = load(root / "state_12.json")
    action = request.get("action")
    if action == "categories":
        update_categories(drive, root, request)
        save(state, root)
        return
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
            if code == "3" and payload.get("carousel_manifest"):
                manifest_language = payload["carousel_manifest"].get("language", "it")
                if language != manifest_language:
                    raise ValueError("Per cambiare lingua, usa un manifest approvato nella lingua selezionata")
            else:
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

"""Rigenera una demo indipendente dalle credenziali Drive."""
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

from main import DemoDrive, prepare
from pager import load, render_page, write

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / "outputs"
CAROUSEL = """Un qubit fisico è un dispositivo che conserva e manipola informazione quantistica.

Un qubit logico distribuisce quella informazione su più qubit fisici.

Un codice di correzione permette di rilevare determinati errori senza misurare direttamente il valore logico."""
GAME = ("La navetta percorre 120 km. "
        "La batteria è al 75%. "
        "La stazione dispone di 8 antenne. "
        "Il satellite controlla la traiettoria usando un sistema di navigazione. "
        "La stazione riceve la telemetria e aggiorna i parametri della missione.")
PHOTONICS = "https://medium.com/@leosorge/q-ant-revolution-is-the-future-of-ai-photonic-native-a8c531b5d155"
COMPILATION = "https://medium.com/@leosorge/european-ai-compilation-is-seeking-native-isas-hint-404-a11e6035f9a3"
PHOTONICS_COPY = ("La NPU2 di Q.ANT affianca le CPU del server come acceleratore per l’AI.\n\n"
                  "Il chip usa niobato di litio per svolgere alcune operazioni direttamente nel dominio ottico.\n\n"
                  "L’adozione dipende anche dal software. Q.PAL mira a rendere l’acceleratore accessibile da strumenti come PyTorch.\n\n"
                  "La sfida è portare l’elaborazione ottica nel rack e renderla utilizzabile con gli strumenti dei data center.")
COMPILATION_COPY = ("Dal modello al chip\nIl compilatore traduce il modello AI nelle istruzioni che il processore può eseguire.\n\n"
                    "Lo stack aperto\nMLIR e LLVM permettono di usare una base comune per più architetture.\n\n"
                    "La posta in gioco\nPer gli acceleratori europei, il supporto software conta quanto la progettazione del chip.")
SAMPLES = [
    ("1", "Chip in laboratorio", CAROUSEL), ("2", "Quiz di navigazione", GAME),
    ("1", "Lo stack aperto per i chip AI", COMPILATION_COPY),
    ("6.3", "Beatles · Son of Flowers", "All I know about light I learnt from Vincos"),
    ("3", "Dal modello AI al processore", COMPILATION_COPY),
    ("5.2", "Reticolo", "Un qubit logico distribuisce l’informazione su più qubit fisici.\n\nLa griglia mostra la disposizione delle celle."),
    ("5.1", "Processore", "La parte centrale del chip elabora i segnali. I contatti lungo i bordi collegano il processore al circuito."),
    ("6.2", "Prism", "All I know about light I learnt from Vincos"),
    ("1", "Q.ANT porta la fotonica nel rack", PHOTONICS_COPY),
    ("2", "Quiz sulla telemetria", GAME),
    ("5.3", "Satellite in orbita", GAME),
    ("6.1", "La luce corre!", "Un impulso di luce attraversa il chip. Il segnale arriva dall’altra parte!"),
    ("4", "Qwat World · Missione in orbita", GAME),
    ("3", "Q.ANT: l’AI passa dalla luce", PHOTONICS_COPY),
]


def main():
    with TemporaryDirectory() as directory:
        demo = Path(directory)
        for i, (code, title, body) in enumerate(SAMPLES):
            source = PHOTONICS if body == PHOTONICS_COPY else COMPILATION if body == COMPILATION_COPY else ""
            if code == "1" and not source:
                title, body, source = "Acceleratori AI e compilazione", COMPILATION_COPY, COMPILATION
            metadata = f"Fonte: {source}\n" if source else ""
            if code == "3" and source == COMPILATION:
                metadata += "Carousel: A sezioni\n"
            write(demo / "new" / f"{i:02}.txt", f"Titolo: {title}\nFormato: {code}\n{metadata}\n{body}\n")
        assert prepare(DemoDrive(demo), demo) == 14
        state = load(demo / "state_12.json")
        assert [card["format_code"] for card in state["slots"][:3]] == ["3", "4", "6.1"]
        assert len(list((demo / "old").glob("*.html"))) == 2
        write(OUT / "FANTASIA_Demo.html", render_page(state["slots"], "FANTASIA — Demo"))
        with ZipFile(OUT / "FANTASIA.zip", "w", compression=ZIP_DEFLATED) as archive:
            for path in sorted(ROOT.rglob("*")):
                relative = path.relative_to(ROOT)
                if (not path.is_file() or set(relative.parts) & {"demo", "__pycache__", ".git", ".venv"}
                        or path.name in {".env", "credentials.json", "authorized_user.json"}):
                    continue
                archive.write(path, relative.as_posix())
            for path in sorted(demo.rglob("*")):
                if path.is_file():
                    archive.write(path, "demo/" + path.relative_to(demo).as_posix())
        with ZipFile(OUT / "FANTASIA.zip") as archive:
            assert archive.testzip() is None
            assert "demo/docs/index.html" in archive.namelist()
            assert ".github/workflows/fantasia.yml" in archive.namelist()


if __name__ == "__main__":
    main()

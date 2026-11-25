import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from expert_choice import choose_and_adapt, numeric_trail, run_expert
from main import acknowledge, prepare
from pager import load, render_page

TEXT = ("Il processore quantistico utilizza qubit fisici per eseguire operazioni controllate. "
        "La correzione protegge la memoria logica durante il calcolo. "
        "Un compilatore traduce il programma in istruzioni supportate.")
CODES = ["1", "2", "3", "4", "5.3", "6.1"]


class Queue:
    def __init__(self):
        self.items = [{"id": str(i), "version": "1", "name": f"{i}.txt",
                       "mimeType": "text/plain"} for i in range(14)]
        self.outputs = {}
        self.fail = False

    def list_new(self):
        return list(self.items)

    def read(self, item):
        i = int(item["id"])
        code = CODES[i % 6]
        body = TEXT + (" La navetta percorre 120 km. La batteria è al 75%. La stazione dispone di 8 antenne." if code == "4" else "")
        return f'Titolo: Scheda {i}\nFormato: {code}\n\n{body}'

    def archive(self, key, filename, html):
        if self.fail:
            raise OSError("archivio non raggiungibile")
        self.outputs.setdefault(key, (filename, html))

    def acknowledge(self, item):
        self.items.remove(item)
        return True


class PipelineTests(unittest.TestCase):
    def test_preserve_demo_on_first_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed = [{"key": str(i), "position": i, "title": f"Demo {i}",
                     "format_label": "News", "format_code": "1", "html": f"<p>Demo {i}</p>"}
                    for i in range(1, 13)]
            (root / "index.html").write_text(render_page(seed, "FANTASIA — Demo"), encoding="utf-8")
            queue = Queue()
            queue.items = queue.items[:1]
            queue.read = lambda item: "TITOLO\nTitolo reale\n\nSOMMARIO\nSintesi breve.\n\nTESTO\nCorpo.\n\nQUIZ\nDomanda?"
            self.assertEqual(prepare(queue, root), 1)
            cards = load(root / "state_12.json")["slots"]
            self.assertEqual([c["title"] for c in cards], ["Titolo reale", *[f"Demo {i}" for i in range(1, 12)]])
            self.assertEqual(cards[0]["format_code"], "1")
            self.assertIn("Sintesi breve.", cards[0]["html"])
            self.assertNotIn("Domanda?", cards[0]["html"])
            self.assertEqual([c["position"] for c in cards], list(range(1, 13)))
            self.assertEqual([html for _, html in queue.outputs.values()], ["<p>Demo 12</p>"])
            self.assertEqual(prepare(queue, root), 0)
            self.assertEqual(len(queue.outputs), 1)

    def test_dispatch(self):
        for code in CODES:
            body = TEXT if code != "4" else "La navetta percorre 120 km. La batteria è al 75%. La stazione dispone di 8 antenne."
            result = run_expert(choose_and_adapt(body, "source", code))
            self.assertEqual(result["format_code"], code)
            self.assertIn("<!doctype html>", result["html"])
        for n in (1, 2, 3):
            with patch("expert_choice.randint", return_value=n) as draw:
                self.assertEqual(choose_and_adapt("Il satellite è in orbita.", "x")["format_code"], f"5.{n}")
                self.assertEqual(choose_and_adapt("«La luce è informazione»", "x")["format_code"], f"6.{n}")
                self.assertEqual(draw.call_count, 2)
                draw.assert_called_with(1, 3)
            for module in (5, 6):
                code = f"{module}.{n}"
                self.assertEqual(run_expert(choose_and_adapt(TEXT, "x", code))["format_code"], code)
        long = "Prima riga.\n\n" + "Testo lungo. " * 50 + "Ultima riga."
        card = run_expert(choose_and_adapt(long, "x", "5.2"))["html"]
        self.assertIn(long, card)
        self.assertNotIn('id="caption"', card)
        self.assertNotIn('<img src=x>', run_expert(choose_and_adapt("<img src=x>", "x"))["html"])
        trail = numeric_trail("La navetta percorre 120 km. La batteria è al 75%. La stazione dispone di 8 antenne.")
        self.assertEqual([list(q["o"]) for q in trail], [list("AB"), list("BC"), list("ABC")])
        self.assertEqual([q["o"][q["answer"]] for q in trail], ["120", "75%", "8"])
        self.assertTrue(all(option.endswith("%") for option in trail[1]["o"].values()))

    def test_rotation_and_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = Queue()
            queue.fail = True
            with self.assertRaises(OSError):
                prepare(queue, root)
            self.assertFalse((root / "state_12.json").exists())
            self.assertEqual(len(queue.items), 14)
            queue.fail = False
            self.assertEqual(prepare(queue, root), 14)
            state = load(root / "state_12.json")
            self.assertEqual([card["title"] for card in state["slots"]],
                             [f"Scheda {i}" for i in range(13, 1, -1)])
            self.assertEqual([card["position"] for card in state["slots"]], list(range(1, 13)))
            self.assertEqual(len(queue.outputs), 2)
            docs = root / "docs"
            html = (docs / "index.html").read_text(encoding="utf-8")
            self.assertEqual(html.count("<iframe "), 12)
            self.assertNotIn("<nav", html)
            self.assertFalse(list(docs.glob("page_*.html")))
            self.assertEqual(prepare(queue, root), 0)
            self.assertEqual(len(queue.outputs), 2)
            self.assertEqual(acknowledge(queue, root), 14)
            self.assertEqual(acknowledge(queue, root), 0)


if __name__ == "__main__":
    unittest.main()

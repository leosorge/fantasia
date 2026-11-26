"""Stato persistente e feed a rotazione di dodici schede."""
import base64
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

LIMIT = 12


def receipt(item, body=None):
    version = item.get("version", "") if body is None else hashlib.sha256(body.encode()).hexdigest()
    return hashlib.sha256(f'{item["id"]}:{version}'.encode()).hexdigest()


def today():
    try:
        zone = ZoneInfo("Europe/Rome")
    except ZoneInfoNotFoundError:
        zone = None
    return datetime.now(zone).date().isoformat()


def load(path):
    path = Path(path)
    if not path.exists():
        return {"slots": [], "processed": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(state, dict) or set(state) - {"slots", "processed", "seeded"}
            or not {"slots", "processed"} <= set(state) or len(state["slots"]) > LIMIT):
        raise ValueError("Stato pager incompatibile.")
    return state


class DemoFrames(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cards = []
        self.read_label = False
        self.label = ""

    def handle_starttag(self, tag, attrs):
        if tag == "h2":
            self.read_label = True
            self.label = ""
        if tag != "iframe":
            return
        fields = dict(attrs)
        if not fields.get("srcdoc") or not fields.get("title"):
            return
        label = re.sub(r"^\d+\.\s*", "", self.label.strip())
        if not label:
            return
        key = hashlib.sha256(f'demo:{len(self.cards)}:{fields["title"]}'.encode()).hexdigest()
        self.cards.append({"key": key, "title": fields["title"], "html": fields["srcdoc"],
                           "format_label": label, "format_code": "5.0" if fields.get("data-fit") == "3d" else "demo"})

    def handle_endtag(self, tag):
        if tag == "h2":
            self.read_label = False

    def handle_data(self, data):
        if self.read_label:
            self.label += data


def archive_card(card, archive):
    words = re.findall(r"[^\W_]+(?:[.’'\-][^\W_]+)*", card["title"], flags=re.UNICODE)[:3]
    stem = "_".join(words)[:90] or "Scheda"
    published_on = date.fromisoformat(card.get("published_on") or today())
    archive(card["key"], f"{stem}_{published_on:%d%m%y}.html", card["html"])


def initialize_feed(state, demo_path, archive):
    if state.get("seeded") or not demo_path.is_file():
        return
    source = demo_path.read_text(encoding="utf-8-sig")
    if "FANTASIA — Demo</title>" not in source:
        return
    parser = DemoFrames()
    parser.feed(source)
    if len(parser.cards) != LIMIT:
        raise ValueError("La pagina demo di partenza non contiene 12 schede.")
    combined = state["slots"] + parser.cards
    for card in reversed(combined[LIMIT:]):
        archive_card(card, archive)
    state["slots"] = [dict(card, position=i) for i, card in enumerate(combined[:LIMIT], 1)]
    state["seeded"] = True


def rotate_batch(state, entries, archive):
    if not entries:
        return
    combined = list(reversed(entries)) + state["slots"]
    for card in reversed(combined[LIMIT:]):
        archive_card(card, archive)
    state["slots"] = [dict(card, position=i) for i, card in enumerate(combined[:LIMIT], 1)]
    state["processed"].update(dict.fromkeys((entry["key"] for entry in entries), True))


def searchable(value):
    folded = unicodedata.normalize("NFKD", value.casefold())
    return " ".join(re.findall(r"\w+", "".join(c for c in folded if not unicodedata.combining(c))))


def topic_groups(path=None):
    path = path or Path(__file__).resolve().with_name("Qlist.txt")
    groups = {}
    name = None
    if path.is_file():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if match := re.match(r"^\d+\.\s+(.+)$", line):
                name = match[1]
                groups[name] = []
            elif name and re.match(r"^\d+\s+parol[ae]\s*:", line, re.I):
                groups[name].extend(word.strip() for word in line.split(":", 1)[1].split(",") if word.strip())
    return groups


def card_categories(item, groups):
    if categories := item.get("categories"):
        return categories
    title = f' {searchable(item["title"])} '
    return [name for name, terms in groups.items() if any(f" {searchable(term)} " in title for term in terms)]


FILTER_SCRIPT = r"""<script>
const query = document.querySelector("#feed-search");
const category = document.querySelector("#feed-category");
const status = document.querySelector("#search-status");
const cards = [...document.querySelectorAll(".feed-card")];
const normalize = text => text.normalize("NFKD").toLowerCase().replace(/\p{M}/gu,"");
function filter() {
  const terms = normalize(query.value).trim().split(/\s+/).filter(Boolean);
  let count = 0;
  for (const card of cards) {
    const matches = (!category.value || JSON.parse(card.dataset.categories).includes(category.value))
      && terms.every(term => normalize(card.dataset.search).includes(term));
    card.hidden = !matches;
    if (matches) count++;
  }
  status.textContent = count ? count + " di " + cards.length + " schede" : "Nessuna scheda corrispondente";
}
query.addEventListener("input", filter);
category.addEventListener("change", filter);
</script>"""


STYLE = """
*{box-sizing:border-box}body{margin:0;padding:12px;color:#eff7fb;background:#101820;font:16px system-ui}
header,main{max-width:1464px;margin:auto}header{margin-bottom:12px}
h1,h2{margin:0}h1{font-size:22px}h2{font-size:14px;margin-bottom:6px}
.masthead{display:block;width:100%;height:auto;border-radius:10px;margin-top:8px;background:#f8f8f8}
main{display:grid;grid-template-columns:repeat(3,minmax(0,480px));gap:18px 12px}
iframe{display:block;width:100%;aspect-ratio:4/5;border:0;border-radius:10px;background:#162a3a}
.feed-filters{display:flex;flex-wrap:wrap;align-items:center;gap:8px 14px;margin:12px 0}
.feed-filters input,.feed-filters select{font:inherit;color:inherit;background:#162a3a;border:1px solid #597787;border-radius:6px;padding:6px;max-width:100%}
.card-label{position:relative}.category-tip{display:none;position:absolute;z-index:2;top:100%;left:0;padding:8px 10px;background:#192e41;color:#fff;border:1px solid #688496;border-radius:6px;font-size:13px;margin:1px 0;pointer-events:none}
.feed-card:hover .category-tip,.feed-card:focus-within .category-tip{display:block}
@media(max-width:1050px){main{grid-template-columns:repeat(2,minmax(0,480px))}}
@media(max-width:660px){main{grid-template-columns:minmax(0,480px)}}
"""


def render_page(slots, heading="FANTASIA", groups=None):
    cards = []
    groups = topic_groups() if groups is None else groups
    available = dict.fromkeys([*groups, "Canali seguiti"])
    for item in slots:
        is_animation = item.get("format_code", "").startswith("5.")
        label = f'{item["position"]}. {"3D" if is_animation else item["format_label"]}'
        categories = card_categories(item, groups) or ["Senza categoria"]
        available.update(dict.fromkeys(categories))
        tooltip = ", ".join(categories)
        search_text = " ".join((item["title"], item["format_label"], tooltip))
        cards.append(f'<section class="feed-card" tabindex="0" aria-describedby="category-{item["position"]}" '
                     f'data-categories="{escape(json.dumps(categories, ensure_ascii=False), quote=True)}" '
                     f'data-search="{escape(search_text, quote=True)}">'
                     f'<div class="card-label"><h2>{escape(label)}</h2>'
                     f'<p class="category-tip" id="category-{item["position"]}">{escape(tooltip)}</p></div>'
                     f'<iframe title="{escape(item["title"])}" '
                     'sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox" '
                     f'srcdoc="{escape(item["html"], quote=True)}"></iframe></section>')
    options = "".join(f'<option value="{escape(name, quote=True)}">{escape(name)}</option>' for name in available)
    filters = ('<div class="feed-filters"><label>Cerca <input id="feed-search" type="search" '
               'placeholder="Titolo o categoria"></label><label>Categoria <select id="feed-category">'
               f'<option value="">Tutte</option>{options}</select></label>'
               f'<span id="search-status" role="status">{len(cards)} schede</span></div>')
    body = "".join(cards) or "<p>Nessun contenuto nel feed.</p>"
    banner = Path(__file__).resolve().parent / "assets" / "qwat-masthead.jpg"
    masthead = ""
    if banner.is_file():
        data = base64.b64encode(banner.read_bytes()).decode("ascii")
        masthead = (f'<img class="masthead" src="data:image/jpeg;base64,{data}" '
                    'alt="L’esploratore del Qwat, vignetta cromata nel laboratorio Q-13">')
    return (f'<!doctype html><html lang="it"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(heading)}</title><style>{STYLE}</style></head>'
            f'<body><header><h1>{escape(heading)}</h1>{masthead}{filters}</header><main>{body}</main>{FILTER_SCRIPT}</body></html>')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + ".tmp")
    pending.write_text(content, encoding="utf-8")
    pending.replace(path)


def save(state, root):
    root = Path(root)
    docs = root / "docs"
    path = root / "Qlist.txt"
    groups = topic_groups(path if path.is_file() else None)
    write(docs / "index.html", render_page(state["slots"], groups=groups))
    write(docs / "admin" / "categories.json", json.dumps(groups, ensure_ascii=False))
    cards = [{key: card[key] for key in ("key", "position", "title", "format_code", "format_label")}
             | {"source_archived": card.get("source_archived", False)} for card in state["slots"]]
    write(docs / "admin" / "feed.json", json.dumps(cards, ensure_ascii=False))
    for number in range(1, 5):
        (docs / f"page_{number}.html").unlink(missing_ok=True)
    save_state(state, root)


def save_state(state, root):
    write(Path(root) / "state_12.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")

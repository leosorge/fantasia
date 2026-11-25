"""Stato persistente e quattro pagine, tre card per pagina."""
import base64
import hashlib
import json
from html import escape
from pathlib import Path

LIMIT = 12


def receipt(item):
    return hashlib.sha256(f'{item["id"]}:{item.get("version", "")}'.encode()).hexdigest()


def load(path):
    path = Path(path)
    if not path.exists():
        return {"slots": [], "processed": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or set(state) != {"slots", "processed"} or len(state["slots"]) > LIMIT:
        raise ValueError("Stato pager incompatibile.")
    return state


def rotate(state, entry, archive):
    if entry["key"] in state["processed"]:
        return False
    slots = state["slots"]
    if len(slots) == LIMIT:
        last = slots[-1]
        archive(last["key"], f'pos12_{last["key"][:16]}.html', last["html"])
    state["slots"] = [dict(item, position=i) for i, item in enumerate([entry, *slots[:LIMIT-1]], 1)]
    state["processed"][entry["key"]] = True
    return True


STYLE = """
*{box-sizing:border-box}body{margin:0;padding:12px;color:#eff7fb;background:#101820;font:16px system-ui}
header,main{max-width:1464px;margin:auto}header{margin-bottom:12px}
h1,h2{margin:0}h1{font-size:22px}h2{font-size:14px;margin-bottom:6px}
.masthead{display:block;width:100%;height:auto;border-radius:10px;margin-top:8px;background:#f8f8f8}
main{display:grid;grid-template-columns:repeat(3,minmax(0,480px));gap:18px 12px}
iframe{display:block;width:100%;aspect-ratio:4/5;border:0;border-radius:10px;background:#162a3a}
@media(max-width:1050px){main{grid-template-columns:repeat(2,minmax(0,480px))}}
@media(max-width:660px){main{grid-template-columns:minmax(0,480px)}}
"""


def render_page(slots, heading="FANTASIA"):
    cards = []
    for item in slots:
        is_animation = item.get("format_code", "").startswith("5.")
        label = f'{item["position"]}. {"3D" if is_animation else item["format_label"]}'
        fit = ' data-fit="3d"' if is_animation else ""
        cards.append(f'<section><h2>{escape(label)}</h2>'
                     f'<iframe title="{escape(item["title"])}"{fit} '
                     'sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox" '
                     f'srcdoc="{escape(item["html"], quote=True)}"></iframe></section>')
    body = "".join(cards) or "<p>Nessun contenuto nel feed.</p>"
    banner = Path(__file__).resolve().parent / "assets" / "qwat-masthead.jpg"
    masthead = ""
    if banner.is_file():
        data = base64.b64encode(banner.read_bytes()).decode("ascii")
        masthead = (f'<img class="masthead" src="data:image/jpeg;base64,{data}" '
                    'alt="L’esploratore del Qwat, vignetta cromata nel laboratorio Q-13">')
    fit_script = """<script>
    window.addEventListener("message",event=>{
      const data=event.data;
      if(data?.type!=="fantasia-3d-height" || !Number.isInteger(data.height) || data.height<1 || data.height>2000000)return;
      const frame=Array.from(document.querySelectorAll('iframe[data-fit="3d"]')).find(item=>item.contentWindow===event.source);
      if(frame)frame.style.height=Math.max(Math.ceil(frame.clientWidth*1.25),data.height)+"px";
    });
    </script>"""
    return (f'<!doctype html><html lang="it"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(heading)}</title><style>{STYLE}</style></head>'
            f'<body>{fit_script}<header><h1>{escape(heading)}</h1>{masthead}</header><main>{body}</main></body></html>')


def write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + ".tmp")
    pending.write_text(content, encoding="utf-8")
    pending.replace(path)


def save(state, root):
    root = Path(root)
    docs = root / "docs"
    write(docs / "index.html", render_page(state["slots"]))
    for number in range(1, 5):
        (docs / f"page_{number}.html").unlink(missing_ok=True)
    write(root / "state_12.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")

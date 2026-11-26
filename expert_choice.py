"""Selezione del formato e adattamento editoriale a 480 × 600."""
import base64
import json
import re
from hashlib import sha256
from html import escape, unescape
from pathlib import Path
from random import randint
from urllib.parse import urlsplit

LABELS = {"1": "News", "2": "Quiz", "3": "Carousel", "4": "Game-PIP",
          "5.1": "3D", "5.2": "3D", "5.3": "3D",
          "6.1": "American Comics", "6.2": "Prism", "6.3": "Beatles · Son of Flowers"}
SCENES = {"5.1": "chip", "5.2": "lattice", "5.3": "satellite"}
QUOTES = {"6.1": "comics", "6.2": "prism", "6.3": "beatles"}
HERE = Path(__file__).resolve().parent
CSS = """
:root{color-scheme:dark;font:16px system-ui;color:#eff8fc;background:#142336}
*{box-sizing:border-box}[hidden]{display:none!important}body,h1,p,blockquote{margin:0}body{min-height:100vh}
main{width:100%;max-width:480px;aspect-ratio:4/5;padding:7%;display:flex;flex-direction:column;gap:12px;overflow:hidden;background:linear-gradient(145deg,#1f4751,#152237)}
h1{font-size:26.67px;line-height:1.12;overflow-wrap:anywhere}p,blockquote{white-space:pre-wrap;overflow-wrap:anywhere}
.body{flex:1;min-height:0;display:grid;align-content:safe center;overflow:auto;font-size:17.33px;line-height:1.45}
footer{font-size:14.67px}a{color:#a4ffe2}button{font:inherit;color:inherit;background:#1d3145;border:1px solid #7995ad;border-radius:8px;padding:8px;cursor:pointer;text-align:left}button:disabled{opacity:.7}
.quiz-options{display:grid;gap:7px}.controls{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.controls span{margin-right:auto}
.good{background:#245943}.bad{background:#663535}.question{margin:0 0 10px}.feedback{min-height:1.4em}.game-track{display:block;width:100%;height:70px;margin:0 0 10px}
.comics{color:#1d1610;background:radial-gradient(#1115 18%,transparent 22%) 0 0/8px 8px,conic-gradient(from 10deg,#eb5440,#e6a730,#428da8,#eb5440);border:5px solid #221815}
.comics h1{background:#f9e6a4;padding:10px;border:3px solid #221815;font:700 25px Impact,system-ui}
.comics blockquote{max-height:100%;overflow:auto;background:#fff1bb;border:4px solid #221815;padding:18px;font:700 25px/1.14 Impact,"Arial Black",sans-serif;box-shadow:7px 7px #201710;transform:rotate(-2deg);margin:10px}.comics a{color:#1d1610;background:#fff0aa;padding:3px}
.comic-panels{display:flex;height:22%;flex-shrink:0;gap:8px}.comic-panels span{flex:1;transform:skew(-7deg);border:4px solid #221815;background:radial-gradient(#17141377 17%,transparent 22%) 0 0/6px 6px,conic-gradient(from -20deg at 30% 70%,#ffd95e 0 40%,#d74834 0 60%,#ffd95e 0)}.comic-panels span:nth-child(2){background-color:#4495ad;filter:hue-rotate(155deg)}.comic-panels span:nth-child(3){filter:hue-rotate(-25deg)}
@media(max-width:380px){h1{font-size:21px}.body{font-size:15px}.comics blockquote{font-size:18px}}
.arcade{background:#141c40;padding:6%;gap:10px}.arcade h1{color:#d8fff9}.arcade canvas{width:100%;display:block;touch-action:manipulation;background:#111835}.arcade .stage{position:relative}.arcade .gate{position:absolute;inset:0;background:#121a3aea;padding:4%;overflow:auto}.arcade .gate h2{margin:0 0 6px;font-size:clamp(17px,5vw,24px)}.arcade .gate p{margin-bottom:6px}.arcade .gate button{display:block;margin:3px 0;padding:4px 10px}.arcade #jump{align-self:flex-end;background:#69ddc4;color:#142331;font-weight:800;padding:8px 18px;touch-action:manipulation}
.qwat{padding:3%;gap:7px;background:#182c24;color:#fff5cf}.qwat h1{font-size:clamp(19px,6vw,29px)}.qwat .stage{position:relative}.qwat canvas{display:block;width:100%;image-rendering:pixelated}.qwat #hud{font-size:clamp(12px,3vw,16px)}
.qwat #gate{position:absolute;inset:5% 7%;display:grid;align-content:center;gap:10px;background:#172a23eb;padding:12px;text-align:center}.qwat #gate h2{margin:0}.qwat button{background:#244a39;color:#fff3c8;border-color:#9bb968;text-align:center;padding:6px 10px;touch-action:manipulation}.qwat .controls{justify-content:center;gap:5px}.qwat .controls button{flex:1}.qwat #hint{font-size:clamp(11px,3vw,14px)}
.comics.illustrated{border:0;position:relative;background-size:cover;background-position:center;padding:5%;justify-content:center}
.illustrated blockquote{padding:0 5%;border:0;margin:0;box-shadow:none;background:none;transform:rotate(-4deg);text-align:center;font-size:clamp(21px,6.5vw,37px);line-height:.99;color:#a52e24;-webkit-text-stroke:.7px #161313;filter:drop-shadow(2px 2px #ffe18b)}
.illustrated .body{flex:initial;max-height:36%;margin-inline:11%;padding:5%;overflow:auto;scrollbar-width:none}
.illustrated footer{position:absolute;bottom:4%;right:5%}
"""


def clip(value, limit):
    if len(value) <= limit:
        return value
    prefix = value[:limit - 1]
    boundary = prefix.rfind(" ")
    return (prefix[:boundary] if boundary > limit / 2 else prefix) + "…"


def safe_url(value):
    try:
        return value if urlsplit(value).scheme in {"https", "http"} and urlsplit(value).hostname else ""
    except ValueError:
        return ""


def parse_source(text):
    text = text.strip()
    if re.match(r"TITOLO[ \t]*\r?\n", text, re.I):
        parts = re.split(r"(?mi)^(TITOLO|SOMMARIO|TESTO|QUIZ|FRASE[- ]SINTESI|FONTE|URL|FORMATO)[ \t]*\r?$", text)
        sections = {parts[i].lower(): parts[i + 1].strip() for i in range(1, len(parts), 2)}
        body = sections.get("testo") or sections.get("sommario")
        if body and sections.get("titolo"):
            fields = {"titolo": sections["titolo"], "sommario": sections.get("sommario", ""), "formato": sections.get("formato", ""),
                      "sintesi": sections.get("frase-sintesi") or sections.get("frase sintesi", "")}
            if source := sections.get("fonte") or sections.get("url"):
                fields["fonte"] = source
            return fields, body
    fields, lines = {}, []
    for line in text.strip().splitlines():
        match = re.match(r"^(titolo|title|fonte|url|formato|carousel)\s*:\s*(.*)$", line, re.I)
        if match and not lines:
            fields[match[1].lower()] = match[2].strip()
        else:
            lines.append(line)
    body = "\n".join(lines).strip()
    if not body:
        raise ValueError("testo vuoto")
    return fields, body


def cloze(text):
    """Distrattori estratti dal testo, senza introdurre affermazioni esterne."""
    words = list(dict.fromkeys(re.findall(r"[^\W\d_]{6,}", text.casefold())))
    questions = []
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text):
        if not 35 <= len(sentence) <= 210:
            continue
        match = next((m for m in re.finditer(r"[^\W\d_]{6,}", sentence)
                      if len([w for w in words if w not in sentence.casefold()]) >= 2), None)
        if not match:
            continue
        answer = match[0]
        distractors = [w for w in words if w not in sentence.casefold()][:2]
        options = sorted([answer, *distractors], key=str.casefold)
        questions.append({"t": sentence[:match.start()] + "____" + sentence[match.end():],
                          "o": options, "answer": options.index(answer)})
        if len(questions) == 4:
            break
    return questions


def numeric_trail(text):
    """Tre fatti numerici, con cartelli AB, BC e ABC."""
    facts = []
    for clause in re.split(r"(?<=[.!?])\s+|[;\n]+", text):
        matches = list(re.finditer(r"(?<![\w.,])\d+(?:[.,]\d+)?(?:\s*%)?(?![\w.,]\d)", clause))
        if len(matches) != 1 or not 12 <= len(clause) <= 100:
            continue
        match = matches[0]
        value = re.sub(r"\s+", "", match[0])
        percent = value.endswith("%")
        digits = value.rstrip("%")
        base = float(digits.replace(",", "."))
        if base > 1_000_000 or (percent and base > 100):
            continue
        decimals = len(re.split("[.,]", digits)[1]) if re.search("[.,]", digits) else 0
        quantum = 10 ** -decimals
        step = max(quantum, round(base * .13, decimals))
        candidates = [base + step, base - step, base + 2*step, base - 2*step]
        available = list(dict.fromkeys(round(n, decimals) for n in candidates
                        if n >= 0 and (not percent or n <= 100) and round(n, decimals) != base))
        letters = ("AB", "BC", "ABC")[len(facts)]
        if len(available) < len(letters)-1:
            continue
        answer = ("B", "C", "A")[len(facts)]
        values = iter(available)
        options = {}
        for letter in letters:
            if letter == answer:
                options[letter] = value
            else:
                shown = format(next(values), f".{decimals}f")
                options[letter] = (shown.replace(".", ",") if "," in digits else shown) + ("%" if percent else "")
        facts.append({"t": clause[:match.start()] + "___" + clause[match.end():],
                      "o": options, "answer": answer})
        if len(facts) == 3:
            break
    return facts


def choose_and_adapt(raw_text, source_name, forced_choice=None):
    fields, body = parse_source(raw_text)
    plain = " ".join(body.split())
    title = fields.get("titolo") or fields.get("title") or re.split(r"(?<=[.!?])\s+", plain)[0]
    title = clip(title, 72)
    declared_source = fields.get("fonte", fields.get("url", ""))
    source = safe_url(declared_source)
    if declared_source and not source:
        raise ValueError("Fonte: inserisci un URL HTTP o HTTPS completo")
    if not source:
        links = re.findall(r'https?://[^\s<>"\]]+', body)
        source = next((url for link in links if (url := safe_url(link.rstrip(".,;:!)")))), "")
    code = str(forced_choice or fields.get("formato", "")).strip()
    editorial = body
    if re.fullmatch(r"https?://www\.youtube\.com/watch\?v=[\w-]{11}", source):
        editorial = re.sub(
            r"(?:^|\n\n)[^\n]+ ha pubblicato questo video il \d{4}-\d{2}-\d{2}\. Durata \d+ min \d+ s\.$",
            "", body,
        ).strip()
    questions = cloze(editorial)
    trail = numeric_trail(editorial)
    blocks = [part.strip() for part in re.split(r"\n[ \t]*\n", body) if part.strip()]
    synthesis = fields.get("sintesi") or next(
        (sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+|\n+", "\n".join((fields.get("sommario", ""), editorial)))
         if 40 <= len(sentence.strip()) <= 220 and not re.search(r"https?://", sentence)
         and sentence.rstrip().endswith((".", "!"))),
        "",
    )
    if not code and not editorial:
        code = "1"
    if not code:
        hint = f"{title} {' '.join(editorial.split())[:250]}".casefold()
        if re.search(r"satellit|\borbit[ae]\b|downlink", hint):
            code = "5"
        elif re.search(r"\b(citazione|fumetto|quote)\b", hint) or editorial.startswith(("«", "“", '"')):
            code = "6"
        elif len(trail) == 3 and re.search(r"\b(gioco|sfida|missione|game)\b", hint):
            code = "4"
        elif questions and re.search(r"\b(quiz|esercizio|test)\b", hint):
            code = "2"
        else:
            eligible = ["1"]
            if questions:
                eligible.append("2")
            if len(blocks) >= 3:
                eligible.append("3")
            if len(trail) == 3:
                eligible.append("4")
            if editorial and re.search(r"\b(?:chip|processori?|qubits?|fotonic\w*|quantistic\w*|quantum)\b", hint):
                eligible.append("5")
            if synthesis:
                eligible.append("6")
            digest = sha256(f"{title}\n{source}\n{editorial}".encode("utf-8")).digest()
            code = eligible[int.from_bytes(digest, "big") % len(eligible)]
    if code in {"5", "6"}:
        code = f"{code}.{randint(1, 3)}"
    if code not in LABELS:
        raise ValueError("Formato ammesso: 1–6 oppure una variante esplicita da 5.1 a 5.3 o da 6.1 a 6.3")
    if code == "2" and not questions:
        raise ValueError("quiz: servono frasi abbastanza lunghe e termini distinti")
    if code == "4" and len(trail) != 3:
        raise ValueError("Game-PIP: servono tre frasi brevi con un numero o una percentuale ciascuna")
    theme = fields.get("carousel", "narrativo").casefold()
    themes = {"narrativo":"narrative", "a sezioni":"sectional", "verbatim":"verbatim"}
    if code == "3" and theme not in themes:
        raise ValueError("Carousel: usa Narrativo, A sezioni o Verbatim")
    return {"format_code": code, "format_label": LABELS[code], "title": title,
            "source_name": source_name, "source": source, "plain": plain,
            "summary": fields.get("sommario", ""), "synthesis": synthesis,
            "blocks": blocks, "body": body, "questions": trail if code == "4" else questions,
            "theme": themes.get(theme, "narrative")}


def js_data(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def document(title, content, script="", extra_css=""):
    return (f'<!doctype html><html lang="it"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(title)}</title><style>{CSS}{extra_css}</style></head>'
            f'<body>{content}{script}</body></html>')


def source_link(payload):
    return (f'<footer><a href="{escape(payload["source"])}" target="_blank" rel="noopener">'
            'Materiale originale</a></footer>') if payload["source"] else ""


def embedded_jpeg(filename):
    return base64.b64encode((HERE / "assets" / filename).read_bytes()).decode("ascii")


def summarize_3d(body):
    words = list(re.finditer(r"\S+", body))
    if len(words) <= 300:
        return body
    excerpt = body[:words[299].end()]
    endings = list(re.finditer(r"[.!?](?=\s|$)", excerpt[words[239].end():]))
    if endings:
        return excerpt[:words[239].end() + endings[-1].end()]
    return excerpt + "…"


def render_3d(settings, body, source):
    template = (HERE / "assets" / "satellite.html").read_text(encoding="utf-8")
    slots = {"SETTINGS": settings, "TEXT": escape(summarize_3d(body)), "SOURCE": source}
    return re.sub(r"__FANTASIA_53_(SETTINGS|TEXT|SOURCE)__", lambda match: slots[match[1]], template)


def update_legacy_3d(card):
    if "fantasia-3d-height" not in card:
        return card
    description = re.search(r'<div class="description"><p>(.*?)</p>(.*?)</div>', card, re.S)
    settings = re.search(r'<script id="settings" type="application/json">(.*?)</script>', card, re.S)
    if description and settings:
        return render_3d(settings[1], unescape(description[1]), description[2])
    return card


def run_expert(payload):
    code = payload["format_code"]
    title = escape(payload["title"])
    source = source_link(payload)
    if code in SCENES:
        settings = js_data({"scene": SCENES[code], "color": "#24b8ad", "speed": 1})
        card = render_3d(settings, payload["body"], source)
    elif code in {"2", "4"}:
        game = code == "4"
        script = (HERE / "assets" / ("qwat.js" if game else "interaction.js")).read_text(encoding="utf-8")
        data = js_data({"questions": payload["questions"]})
        body = ('<p id="hud" aria-live="polite"></p><div class="stage"><canvas id="course" tabindex="0" width="450" height="430" '
                'aria-label="Percorso Qwat World su tre piani"></canvas><div id="gate" hidden></div></div>'
                '<div id="commands" class="controls"></div><p id="hint"></p>') if game else '<div class="body" id="play"></div>'
        card = document(payload["title"], f'<main class="{"qwat" if game else "quiz"}"><h1>{title}</h1>{body}{source}</main>',
                        f'<script id="data" type="application/json">{data}</script><script>{script}</script>')
    elif code == "3":
        theme = payload["theme"]
        slides = [{"title":payload["title"], "text":""}]
        for block in payload["blocks"]:
            title_line, separator, rest = block.partition("\n")
            sectional = theme == "sectional" and bool(separator)
            copy = rest if sectional else block
            slides.append({"title": title_line if sectional else "",
                           "text": copy if theme == "verbatim" else re.sub(r"(?<=[.!?]) +", "\n", copy)})
        use_photo = (HERE / "assets" / "carousel-quantum.jpg").exists() and bool(
            re.search(r"quantistic|\bqubit\b|fotonic|ottic", payload["plain"], re.I))
        profile = json.loads((HERE / "assets" / "stile-neroverde-carousel-brand.json").read_text(encoding="utf-8-sig"))
        palette = profile["palette"]
        css = (HERE / "assets" / "carousel-builder-v2.14.3.css").read_text(encoding="utf-8")
        license_text = (HERE / "assets" / "carousel-builder-LICENSE.txt").read_text(encoding="utf-8")
        css = "/*\n" + license_text + "\n*/\n" + css
        css += """
        .carousel-card{position:relative;padding:0;gap:0;display:block;background:#090a0c}
        .carousel-card .slide-preview{position:relative;top:auto;min-height:0;width:100%;height:100%;border-radius:0}
        .carousel-card .preview-copy{max-height:68%;overflow:auto}
        .carousel-card .preview-title{font-weight:800}
        .carousel-card footer{position:absolute;z-index:3;bottom:42px;left:9%;font-size:12px}
        .carousel-card footer a{color:white;background:#1a2429;padding:3px 5px;border-radius:4px}
        .carousel-nav{position:absolute;z-index:4;bottom:0;inset-inline:0;display:flex;justify-content:space-between;gap:5px;padding:4px;background:#090a0c}
        .carousel-nav button,.carousel-nav select{background:#242526;color:#fff;border:1px solid #637272;border-radius:5px;padding:4px 6px;font:13px Arial,sans-serif}
        """
        variables = (f'--preview-accent:{palette["accent"]};--preview-dark-bg:{palette["background_dark"]};'
                     f'--preview-light-bg:{palette["background_light"]};--preview-dark-text:{palette["text_on_dark"]};'
                     f'--preview-light-text:{palette["text_on_light"]};--preview-display:Arial,sans-serif;'
                     '--preview-body:Arial,sans-serif;--preview-scale:1;--sentence-gap:.6em')
        image = (f'<img id="art" class="preview-cover-media" alt="" src="data:image/jpeg;base64,{embedded_jpeg("carousel-quantum.jpg")}">'
                 if use_photo else '<span id="art" hidden></span>')
        planets = "".join(f'<span class="preview-sphere preview-sphere-{role}"></span>'
                          for role in ("primary", "core", "ring", "moon", "satellite"))
        script = (f'<script type="application/json" id="slides">{js_data({"slides": slides, "photo": use_photo, "palette": palette, "verbatim": theme == "verbatim"})}</script>'
                  f'<script>{(HERE / "assets" / "carousel-feed.js").read_text(encoding="utf-8")}</script>')
        card = document(payload["title"],
                        f'<main class="carousel-card" id="carousel"><section id="deck" data-theme="{theme}" style="{escape(variables)}">'
                        f'<div class="preview-constellation" id="constellation" aria-hidden="true">{planets}</div>'
                        f'<div class="preview-frame-field" id="frameField" aria-hidden="true"></div>{image}'
                        '<span class="preview-page" id="page"></span><div class="preview-copy">'
                        '<h2 id="slideTitle" class="preview-title"></h2><p id="slide" class="preview-summary"></p></div>'
                        f'</section>{source}<div class="carousel-nav"><button id="back">Indietro</button>'
                        '<select id="visualStyle" aria-label="Stile visivo Carousel Builder">'
                        '<option value="editorial-frame">A · Editoriale</option>'
                        '<option value="editorial-halftone">B · Geometrico</option>'
                        '<option value="corporate-modular">C · Frame</option>'
                        '</select><button id="next">Avanti</button></div></main>', script, css)
    else:
        style = QUOTES.get(code)
        comics = style == "comics"
        tag = "blockquote" if style else "p"
        quote = re.search(r'«([^»]+)»|“([^”]+)”|"([^"\n]+)"', payload["plain"]) if style else None
        fragment = (next(group for group in quote.groups() if group is not None) if quote
                    else (payload.get("synthesis") if style else payload.get("summary")) or payload["plain"])
        text = escape(fragment if quote else clip(fragment, 260 if style else 450))
        illustration = HERE / "assets" / "american-comics.jpg"
        if comics and illustration.exists():
            image = embedded_jpeg("american-comics.jpg")
            card = document(payload["title"], '<main class="comics illustrated">'
                            f'<div class="body"><blockquote>{text}</blockquote></div>{source}</main>',
                            extra_css=f'.illustrated{{background-image:url(data:image/jpeg;base64,{image})}}')
        elif style and not comics:
            quote_css = (HERE / "assets" / "quote-styles.css").read_text(encoding="utf-8")
            card = document(payload["title"], f'<main class="quote {style}"><div class="body">'
                            f'<blockquote>{text}</blockquote></div>{source}</main>', extra_css=quote_css)
        else:
            panels = '<div class="comic-panels" aria-hidden="true"><span></span><span></span><span></span></div>' if comics else ""
            card = document(payload["title"], f'<main class="{"comics" if comics else "news"}"><h1>{title}</h1>{panels}'
                            f'<div class="body"><{tag}>{text}</{tag}></div>{source}</main>')
    return {key: payload[key] for key in ("format_code", "format_label", "title")} | {"html": card}

"""Saca las tablitas de Google Sheets y las deja estáticas en ../tablitas/.

1. (con --drive) por cada hoja de cálculo de drive_main.json descarga:
     - el export HTML de Google (aspecto idéntico: colores, anchos, imágenes en celda)
     - el .xlsx (para descargar / reabrir en cualquier programa de hojas)
   y apunta la lista en tablitas/tablitas.json. Solo funciona mientras sigan públicas en Google.
2. convierte los .rtf de tablitas/textedit/ (tablitas de TextEdit) a .html (textutil, macOS).
3. rehace tablitas/index.html con todo, más lo que haya en tablitas/nuevas/ (salido del generador).

    python3 tools/drive_crawl.py 1EjRzAfi49bkjyhzu5wryt0KFr1uhzSNl tools/drive_main.json  # refrescar inventario
    python3 tools/tablitas.py --drive   # volver a bajar de Google
    python3 tools/tablitas.py           # solo rehacer índice + rtf (sin internet)
"""
import html, io, json, urllib.parse, re, shutil, subprocess, sys, unicodedata, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tablitas"

GROUPS = [  # (clave, título, descripción)
    ("nuevas", "tablitas nuevas", "hechas con el generador, después del TFG."),
    ("originales", "tablitas (textedit)", "las primeras, de septiembre a diciembre de 2020: tablas en TextEdit con celdas que hablan entre sí."),
    ("google", "tablitas google", "el culmen de la metodología: agotar una canción y guardar todo su jugo (febrero–abril 2021)."),
    ("extended", "extended tablitas", "el apéndice que salió de tablitas y acabó creciendo hasta VERTICAL."),
    ("pendientes", "aún no terminadas", "tablitas empezadas que se quedaron a medias."),
    ("porhacer", "anotadas por hacer", "canciones apuntadas para analizar algún día. «ese continuará»."),
    ("otras", "registros", "hojas de seguimiento del propio TFG."),
]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def classify(path):
    if path.startswith("/aun no terminadas/"):
        return "pendientes", path.rsplit("/", 1)[-1].strip()
    if path.startswith("/extended_tablitas/"):
        return "extended", path.rsplit("/", 1)[-1].strip()
    name = path[1:].strip()
    if name.startswith("/"):
        return "porhacer", name.lstrip("/ ").strip()
    if name.startswith("tablitas google "):
        return "google", name[len("tablitas google "):].replace("vocaloid ", "", 1)
    return "otras", name


def fetch(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · tablitas</title>
{styles}
<link rel="stylesheet" href="../tablita.css">
</head><body class="sheet">
<header class="tb-head"><a href="../">← tablitas</a> <h1>{title}</h1>
<nav>{tabs}<a href="{slug}.xlsx" download>descargar .xlsx</a></nav></header>
{body}
</body></html>
"""


def build_sheet(sid, title, slug):
    d = OUT / slug
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    base = f"https://docs.google.com/spreadsheets/d/{sid}/export?format="
    (d / f"{slug}.xlsx").write_bytes(fetch(base + "xlsx"))
    z = zipfile.ZipFile(io.BytesIO(fetch(base + "zip")))
    sheets = sorted(n for n in z.namelist() if n.endswith(".html"))
    for n in z.namelist():
        if n.startswith("resources/") and not n.endswith(".css"):
            (d / n).parent.mkdir(parents=True, exist_ok=True)
            (d / n).write_bytes(z.read(n))
    # una página por hoja; la primera es index.html
    files = ["index.html"] + [f"{slugify(Path(n).stem)}.html" for n in sheets[1:]]
    tabs = "".join(f'<a href="{f}">{html.escape(Path(n).stem)}</a> ' for n, f in zip(sheets, files)) if len(sheets) > 1 else ""
    for n, f in zip(sheets, files):
        raw = z.read(n).decode("utf-8")
        styles = "".join(re.findall(r"<style.*?</style>", raw, re.S))
        body = raw[raw.find('<div class="ritz'):]
        (d / f).write_text(PAGE.format(title=html.escape(title), slug=slug, styles=styles, tabs=tabs, body=body))
    return len(sheets)


# rtf de tablitas/textedit/ -> grupo (por defecto "originales")
TEXTEDIT_GROUP = {"-error_extended": "extended", "meltdown_extended": "extended", "teo_extended": "extended",
                  "grimes - delete forever": "google", "grimes - my name is dark": "google"}


def drive():
    items = json.loads((ROOT / "tools" / "drive_main.json").read_text())
    entries = []
    for path, url in items:
        m = re.search(r"/spreadsheets/d/([\w-]+)", url)
        if not m:
            continue
        group, title = classify(path)
        slug = slugify(title)
        n = build_sheet(m.group(1), title, slug)
        entries.append({"id": m.group(1), "group": group, "title": title, "href": slug + "/"})
        print(f"ok  {group:10} {slug}  ({n} hoja{'s' if n > 1 else ''})")
    (OUT / "tablitas.json").write_text(json.dumps(entries, ensure_ascii=False, indent=1))


def url(name):  # nombres con espacios/acentos -> url segura (NFC, como lo guarda git)
    return urllib.parse.quote(unicodedata.normalize("NFC", name))


def textedit():
    entries = []
    for rtf in sorted((OUT / "textedit").glob("*.rtf")):
        out = rtf.with_suffix(".html")
        subprocess.run(["textutil", "-convert", "html", "-output", str(out), str(rtf)], check=True)
        title = unicodedata.normalize("NFC", rtf.stem).lstrip("-").replace("_extended", "")
        page = out.read_text().replace("<title></title>", f"<title>{html.escape(title)} · tablitas</title>")
        page = page.replace("<body>", f'<body>\n<p style="font:13px Helvetica;margin:0 0 1em"><a href="../">← tablitas</a> · <a href="{url(rtf.name)}" download>descargar .rtf</a></p>', 1)
        out.write_text(page)
        entries.append({"group": TEXTEDIT_GROUP.get(rtf.stem, "originales"), "title": title + (" (texto)" if rtf.stem.startswith("grimes") else ""), "href": "textedit/" + url(out.name)})
    return entries


def main():
    if "--drive" in sys.argv or not (OUT / "tablitas.json").exists():
        drive()
    entries = json.loads((OUT / "tablitas.json").read_text()) + textedit()
    entries += [{"group": "nuevas", "title": unicodedata.normalize("NFC", f.name[: -len(".html")].removesuffix(".tablita")), "href": "nuevas/" + url(f.name)}
                for f in sorted((OUT / "nuevas").glob("*.html"))]

    sections = []
    for key, name, desc in GROUPS:
        rows = sorted((e for e in entries if e["group"] == key), key=lambda e: e["title"].lower())
        if rows:
            lis = "\n".join(f'<li><a href="{html.escape(e["href"])}">{html.escape(e["title"])}</a></li>' for e in rows)
            sections.append(f"<section><h2>{name} <small>{len(rows)}</small></h2><p>{desc}</p><ul>\n{lis}\n</ul></section>")
    (OUT / "index.html").write_text((OUT / "_index.tpl.html").read_text().replace("{{sections}}", "\n".join(sections)))


if __name__ == "__main__":
    main()

"""Comprime los sobres (copia del Drive en el Escritorio) a ../sobres/ y hace sobres/index.html.

  vídeo  -> .mp4 h264, lado largo ≤ 960px, crf 30 (se ve en cualquier navegador, iPhone incluido)
  imagen -> .webp, ancho ≤ 1200px (sips + cwebp)
  audio  -> .m4a (el .ogg no suena en Safari)
  texto  -> .html (textutil, macOS) + el .rtf original

    python3 tools/sobres.py   # no rehace lo que ya existe; borra un archivo de sobres/ para regenerarlo
"""
import html, re, subprocess, tempfile, unicodedata, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sobres"
SRC = [Path.home() / "Desktop" / f"cómo hacer algo pequeñito, consistente y honesto{s}" / "sobre" for s in ("", " 2")]
VIDEO, IMAGE, AUDIO = {".mp4", ".mov"}, {".png", ".jpg", ".jpeg", ".heic"}, {".ogg", ".m4a"}


def nfc(s):
    return unicodedata.normalize("NFC", s)


def run(*cmd):
    subprocess.run(cmd, check=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)


CLAIMED = set()  # dos originales con el mismo nombre y distinta extensión (sobre meowrhino.jpg/.png)


def convert(src):
    ext = src.suffix.lower()
    stem = nfc(src.stem).strip()
    if stem.lower() in CLAIMED:
        stem += " 2"
    CLAIMED.add(stem.lower())
    if ext in VIDEO:
        dst = OUT / f"{stem}.mp4"
        if not dst.exists():
            run("ffmpeg", "-y", "-v", "error", "-i", str(src),
                "-vf", "scale='if(gt(iw,ih),min(960,iw),-2)':'if(gt(iw,ih),-2,min(960,ih))'",
                "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "80k", "-movflags", "+faststart", str(dst))
        return "video", [dst]
    if ext in IMAGE:
        dst = OUT / f"{stem}.webp"
        if not dst.exists():
            with tempfile.TemporaryDirectory() as tmp:  # sips (macOS) lee también heic; cwebp no
                png = Path(tmp) / "x.png"
                run("sips", "-s", "format", "png", str(src), "--out", str(png))
                w = int(subprocess.run(["sips", "-g", "pixelWidth", str(png)], capture_output=True, text=True).stdout.split()[-1])
                run("cwebp", "-quiet", "-q", "80", *(["-resize", "1200", "0"] if w > 1200 else []), str(png), "-o", str(dst))
        return "image", [dst]
    if ext in AUDIO:
        dst = OUT / f"{stem}.m4a"
        if not dst.exists():
            run("ffmpeg", "-y", "-v", "error", "-i", str(src), "-vn", "-c:a", "aac", "-b:a", "96k", str(dst))
        return "audio", [dst]
    if ext == ".rtf":
        rtf, dst = OUT / f"{stem}.rtf", OUT / f"{stem}.html"
        rtf.write_bytes(src.read_bytes())
        run("textutil", "-convert", "html", "-output", str(dst), str(rtf))
        dst.write_text(dst.read_text().replace("<title></title>", f"<title>{html.escape(stem)} · sobres</title>"))
        return "text", [dst, rtf]
    return None, []


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def url(p):
    return urllib.parse.quote(nfc(p.name))


def card(kind, title, files):
    f, t, h = url(files[0]), html.escape(title), "#" + slugify(title)
    media = {
        "video": f'<video src="{f}" controls preload="metadata" playsinline></video>',
        "image": f'<a href="{h}"><img src="{f}" alt="{t}" loading="lazy"></a>',
        "audio": f'<audio src="{f}" controls preload="none"></audio>',
        "text": f'<a class="txt" href="{h}">leer →</a> <a class="txt" href="{url(files[-1])}" download>.rtf</a>',
    }[kind]
    # data-*: lo que usa el visor (sobres/#id)
    return (f'<figure class="{kind}" id="{slugify(title)}" data-kind="{kind}" data-src="{f}" data-title="{t}">'
            f'{media}<figcaption><a href="{h}">{t}</a></figcaption></figure>')


def main():
    OUT.mkdir(exist_ok=True)
    cards = []
    for src in sorted((p for d in SRC for p in d.iterdir()), key=lambda p: nfc(p.stem).lower()):
        if src.name.startswith(".") or src.name.startswith("Icon"):
            continue
        kind, files = convert(src)
        if kind:
            cards.append(card(kind, nfc(files[0].stem).replace("_", " "), files))
            print("ok ", kind, src.name)
        else:
            print("??", src.name)
    page = (OUT / "_index.tpl.html").read_text()
    (OUT / "index.html").write_text(page.replace("{{n}}", str(len(cards))).replace("{{cards}}", "\n".join(cards)))


if __name__ == "__main__":
    main()

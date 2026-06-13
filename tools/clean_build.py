#!/usr/bin/env python3
"""
Clean rewrite: rebuild each Cargo page as minimal, editable static HTML/CSS,
WITHOUT the Cargo JS engine (no embedded JSON, no templates, no _jsapps/_api).

Reuses Cargo's own CSS (foundation + the site stylesheet) for fidelity, plus each
page's local_css, and lays out galleries with a small clean CSS/JS of our own.

Output goes to ./clean/  (kept separate from ./site until validated).
"""
import json, os, re, hashlib, shutil
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT  = os.path.join(ROOT, 'clean')
BUNDLE = json.load(open(os.path.join(ROOT, 'cargo_bundle.json')))
ASSET_MAP = json.load(open(os.path.join(ROOT, 'asset_map.json')))   # real_url -> local rel path

# ---------- asset URL -> local maps ----------
FREIGHT_BY_URL = {u: v for u, v in ASSET_MAP.items() if 'freight.cargo.site' in u}
FREIGHT_BY_HASH = {}
for u, v in FREIGHT_BY_URL.items():
    m = re.search(r'/i/([a-f0-9]{16,})/', u)
    if m:
        # prefer original / largest
        FREIGHT_BY_HASH.setdefault(m.group(1), v)
FILES_BY_URL = {u: v for u, v in ASSET_MAP.items() if 'files.cargocollective.com' in u}

def localize_freight(url):
    if not url: return url
    if url in FREIGHT_BY_URL: return FREIGHT_BY_URL[url]
    m = re.search(r'/i/([a-f0-9]{16,})/', url)
    if m and m.group(1) in FREIGHT_BY_HASH: return FREIGHT_BY_HASH[m.group(1)]
    return url

def localize_files(url):
    if url in FILES_BY_URL: return FILES_BY_URL[url]
    # match by filename
    name = urlparse(url).path.rsplit('/', 1)[-1]
    p = os.path.join(OUT, 'assets/files', name)
    return 'assets/files/' + name if name and os.path.exists(p) else url

# ---------- scaffolding parsing ----------
def scaffold(purl):
    m = re.search(r'<script type="text/json" data-set="ScaffoldingData"\s*>(.*?)</script>', BUNDLE[purl], re.S)
    return json.loads(m.group(1))

def find_node(node, purl):
    if isinstance(node, list):
        for x in node:
            r = find_node(x, purl)
            if r: return r
    elif isinstance(node, dict):
        if node.get('project_url') == purl: return node
        for v in node.values():
            if isinstance(v, (list, dict)):
                r = find_node(v, purl)
                if r: return r
    return None

PAGES = [p for p in BUNDLE if p != '__root__']
LINK_TARGETS = set(PAGES)

# build {purl: node} using each page's own scaffold (most complete for itself)
NODES = {}
SETS = {}
for purl in PAGES:
    n = find_node(scaffold(purl), purl)
    if not n: continue
    if n.get('is_set'):
        SETS[purl] = [c.get('project_url') for c in (n.get('pages') or [])]
        # also stash child nodes that carry content
        for c in (n.get('pages') or []):
            if c.get('project_url') and not c.get('is_set'):
                NODES.setdefault(c['project_url'], c)
    else:
        NODES[purl] = n

# ---------- content cleaning ----------
def clean_content(html):
    # images: data-src -> src (local), lazy, drop data-mid
    def img_sub(m):
        tag = m.group(0)
        ds = re.search(r'data-src="([^"]+)"', tag)
        src = localize_freight(ds.group(1)) if ds else ''
        w = re.search(r'\bwidth="([^"]+)"', tag)
        h = re.search(r'\bheight="([^"]+)"', tag)
        attrs = ['src="%s"' % src, 'loading="lazy"', 'decoding="async"', 'alt=""']
        if w: attrs.append('width="%s"' % w.group(1))
        if h: attrs.append('height="%s"' % h.group(1))
        return '<img ' + ' '.join(attrs) + '>'
    html = re.sub(r'<img\b[^>]*>', img_sub, html)

    # galleries: parse mode, add classes, drop noisy data-gallery
    def gal_sub(m):
        data = m.group(1)
        mode = 'justify'
        try:
            mode = json.loads(unquote(data)).get('path') or 'justify'
        except Exception:
            pass
        return '<div class="image-gallery initialized gallery-%s">' % mode
    html = re.sub(r'<div class="image-gallery" data-gallery="([^"]+)">', gal_sub, html)

    # videos: localize source, no preload
    html = re.sub(r'<video\b', '<video preload="none"', html)
    def src_sub(m):
        u = m.group(1)
        if 'files.cargocollective.com' in u: u = localize_files(u)
        elif 'freight.cargo.site' in u: u = localize_freight(u)
        return 'src="%s"' % u
    html = re.sub(r'src="(https://(?:files\.cargocollective\.com|freight\.cargo\.site)/[^"]+)"', src_sub, html)
    # audio/source tags localized the same way (covered by regex above)

    # internal links -> .html ; drop rel="history"
    html = html.replace('rel="history"', '')
    def link_sub(m):
        href = m.group(1)
        # absolute meowrhino -> purl
        mm = re.match(r'https?://meowrhino\.cargo\.site/(.+)$', href)
        if mm: href = mm.group(1)
        base = href.split('?')[0].split('#')[0].strip('/')
        if base in LINK_TARGETS:
            return 'href="%s.html"' % base
        return m.group(0)
    html = re.sub(r'href="([^"]+)"', link_sub, html)

    # background-image url(freight...) -> local
    html = re.sub(r'url\((https://freight\.cargo\.site/[^)]+)\)',
                  lambda m: 'url(%s)' % localize_freight(m.group(1)), html)
    return html

def local_style_id(local_css):
    m = re.search(r'\[local-style="(\d+)"\]', local_css or '')
    return m.group(1) if m else ''

def render_block(node):
    """One page's content wrapped like Cargo expects (so foundation/base CSS applies).
       The svg_overlay (hand-drawn markers) goes INSIDE bodycopy after page_content,
       exactly like Cargo's template, so foundation's `bodycopy svg.marker-overlay`
       absolute-positioning rule applies and the drawings line up with the text."""
    content = clean_content(node.get('content') or '')
    po = node.get('page_options') or {}
    lsid = local_style_id(po.get('local_css'))
    svg = (po.get('svg_overlay') or '').strip()
    attr = (' local-style="%s"' % lsid) if lsid else ''
    overlay = ('\n          %s' % svg) if svg else ''
    return ('    <div class="page"%s>\n'
            '      <bodycopy class="bodycopy content content_padding">\n'
            '        <div class="page_content clearfix">\n%s\n        </div>%s\n'
            '      </bodycopy>\n'
            '    </div>\n') % (attr, content, overlay)

def page_local_css(nodes):
    css = []
    for n in nodes:
        c = (n.get('page_options') or {}).get('local_css')
        if c: css.append('/* %s */\n%s' % (n.get('project_url'), c.strip()))
    return '\n\n'.join(css)

def esc_attr(s):
    return (s or '').replace('"', '&quot;').replace('<', '').replace('\n', ' ')[:300]

PAGE_TMPL = """<!doctype html>
<html lang="{lang}" data-predefined-style="true" data-css-presets="true" data-typography-preset>
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="stylesheet" href="assets/css/foundation.css">
  <link rel="stylesheet" href="assets/css/base.css">
  <link rel="stylesheet" href="assets/css/galleries.css">
{localcss}</head>
<body>
  <main class="main_container">
{blocks}  </main>
</body>
</html>
"""

def lang_of(purl):
    if purl.endswith('_eng') or purl == 'homepage_eng': return 'en'
    if purl.endswith('_cat'): return 'ca'
    return 'es'

def build_page(purl):
    if purl in SETS:
        child_purls = SETS[purl]
        nodes = [NODES[c] for c in child_purls if c in NODES]
        title = purl
        desc = ''
    else:
        n = NODES.get(purl)
        if not n: return None
        nodes = [n]
        title = n.get('title_no_html') or n.get('title') or purl
        desc = n.get('excerpt') or ''
    blocks = ''.join(render_block(n) for n in nodes)
    lc = page_local_css(nodes)
    localcss = ('  <style>\n%s\n  </style>\n' % lc) if lc.strip() else ''
    return PAGE_TMPL.format(
        lang=lang_of(purl),
        title=esc_attr((title or purl)) + ' — meowrhino',
        desc=esc_attr(desc),
        localcss=localcss,
        blocks=blocks,
    )

# ---------- CSS assembly ----------
def localize_css_text(css):
    # localize url(...) references to cargo hosts
    def u(m):
        url = m.group(1).strip('\'"')
        if url.startswith('//'): url = 'https:' + url
        if 'freight.cargo.site' in url: url = localize_freight(url)
        elif url in ASSET_MAP: url = ASSET_MAP[url]
        else:
            # static/type by path match in asset map
            for real, local in ASSET_MAP.items():
                if real.split('?')[0].endswith(urlparse(url).path) and urlparse(url).path:
                    url = local; break
        return 'url(%s)' % url
    return re.sub(r'url\(([^)]+)\)', u, css)

def main():
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'assets/css'), exist_ok=True)
    # copy media assets from site/ (already downloaded there)
    for sub in ('freight', 'files', 'type'):
        src = os.path.join(ROOT, 'site/assets', sub)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(OUT, 'assets', sub))

    # foundation.css from the identical inline <style> block
    h = BUNDLE['UX-UI_esp']; head = h[:h.find('</head>')]
    foundation = max(re.findall(r'<style[^>]*>(.*?)</style>', head, re.S), key=len)
    open(os.path.join(OUT, 'assets/css/foundation.css'), 'w').write(localize_css_text(foundation))

    # base.css from the member stylesheet
    member = open(os.path.join(ROOT, 'site/assets/css/member_stylesheet.css')).read()
    open(os.path.join(OUT, 'assets/css/base.css'), 'w').write(localize_css_text(member))

    # galleries.css: clean layouts for our static galleries + marquee
    open(os.path.join(OUT, 'assets/css/galleries.css'), 'w').write(GALLERIES_CSS)

    # pages
    n = 0
    for purl in PAGES:
        html = build_page(purl)
        if not html: continue
        open(os.path.join(OUT, purl + '.html'), 'w', encoding='utf-8').write(html)
        n += 1
    # index = welcome
    open(os.path.join(OUT, 'index.html'), 'w', encoding='utf-8').write(build_page('welcome'))
    open(os.path.join(OUT, '.nojekyll'), 'w').close()
    print('wrote %d pages + index.html to clean/' % n)

GALLERIES_CSS = """/* ============================================================
   galleries.css — static layout for the recovered site
   Replaces the parts the Cargo JS engine used to compute at runtime:
   block layout for <bodycopy>, the numeric grid, gallery image layout,
   and the marquee. (Without the engine these need explicit CSS.)
   ============================================================ */

/* <bodycopy> is a custom element (defaults to display:inline), so its
   content_padding wouldn't indent block children. Make it a block. */
bodycopy{ display:block; }

/* ---- Grid ----
   Content authored grid widths as [grid-col="N"] (N of 12) and spacing as
   [grid-gutter]/[grid-pad] on a pixel scale the engine recomputed. Foundation
   maps those attrs onto a rem scale (e.g. [grid-gutter="10"]{margin:-5rem}),
   which overflows without the engine. So: neutralize foundation's gutter and
   define our own simple, predictable grid. */
[grid-row]{ margin:0 !important; width:auto !important; }
[grid-gutter]{ margin:0 !important; }
[grid-col]{ box-sizing:border-box; padding:0 8px !important; }
[grid-col="1"]{width:8.3333%}  [grid-col="2"]{width:16.6667%}
[grid-col="3"]{width:25%}      [grid-col="4"]{width:33.3333%}
[grid-col="5"]{width:41.6667%} [grid-col="6"]{width:50%}
[grid-col="7"]{width:58.3333%} [grid-col="8"]{width:66.6667%}
[grid-col="9"]{width:75%}      [grid-col="10"]{width:83.3333%}
[grid-col="11"]{width:91.6667%}[grid-col="12"]{width:100%}
@media (max-width:700px){ [grid-col]{width:100% !important} }

/* ---- Galleries ----
   Foundation hides direct-child media (it expects the engine to wrap each in a
   .gallery_card). We show them and lay out by mode. */
.image-gallery.initialized > img,
.image-gallery.initialized > video{ display:block; max-width:100%; }
.image-gallery img{ max-height:85vh; }

/* Slideshow -> horizontal scroll-snap carousel (swipe/scroll, no JS) */
.gallery-slideshow{ display:flex; overflow-x:auto; scroll-snap-type:x mandatory; gap:2px; -webkit-overflow-scrolling:touch; }
.gallery-slideshow > img{ scroll-snap-align:center; flex:0 0 100%; width:100%; height:auto; object-fit:contain; }

/* Justify -> single image at a sensible size; multiple -> equal-height rows */
.gallery-justify{ display:flex; flex-wrap:wrap; gap:2px; }
.gallery-justify > img{ width:auto; max-width:100%; height:auto; }
.gallery-justify:has(> img + img) > img{ height:300px; width:auto; flex:1 1 auto; object-fit:cover; max-width:none; }

/* Freeform / fallback -> simple responsive flow */
.gallery-freeform{ display:flex; flex-wrap:wrap; gap:8px; align-items:flex-start; }
.gallery-freeform > img{ max-width:48%; height:auto; }

/* ---- Marquee ----
   The engine animated marquees by cloning content into .marquee_contents.
   Statically we just show the text (a scrolling section title looks broken). */
.marquee{ overflow:visible !important; white-space:normal !important; }

video{ max-width:100%; height:auto; }
"""

if __name__ == '__main__':
    main()

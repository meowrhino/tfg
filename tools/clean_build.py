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
def clean_img(tag):
    """data-src -> local src, lazy, keep dimensions, drop engine attrs.
       If the tag has no data-src it's already been cleaned (or has a real src),
       so leave it untouched — otherwise a second pass would blank it."""
    ds = re.search(r'data-src="([^"]+)"', tag)
    if not ds:
        return tag
    src = localize_freight(ds.group(1))
    w = re.search(r'\bwidth="([^"]+)"', tag)
    h = re.search(r'\bheight="([^"]+)"', tag)
    attrs = ['src="%s"' % src, 'loading="lazy"', 'decoding="async"', 'alt=""']
    if w: attrs.append('width="%s"' % w.group(1))
    if h: attrs.append('height="%s"' % h.group(1))
    return '<img ' + ' '.join(attrs) + '>'

def process_galleries(html):
    """Rebuild each Cargo gallery from its real config so the layout matches:
       freeform -> per-image % widths (meta_data); justify -> equal-height rows;
       slideshow -> a carousel (enhanced by gallery.js)."""
    def repl(m):
        cfg_raw, inner = m.group(1), m.group(2)
        try: cfg = json.loads(unquote(cfg_raw))
        except Exception: cfg = {}
        mode = cfg.get('path') or 'justify'
        data = cfg.get('data', {}) or {}
        try: pad = float(data.get('image_padding', 2))
        except Exception: pad = 2.0
        cleaned = [clean_img(im) for im in re.findall(r'<img\b[^>]*>', inner)]
        n = len(cleaned)
        gap = 'style="--gap:%gpx"' % (pad * 3)
        if mode == 'freeform':
            meta = data.get('meta_data', {}) or {}
            cards = []
            for i, im in enumerate(cleaned):
                w = (meta.get(str(i)) or {}).get('width') or (100.0 / max(1, n))
                cards.append('<figure class="gcard" style="width:%s%%">%s</figure>' % (w, im))
            return '<div class="gallery gallery-freeform" %s>%s</div>' % (gap, ''.join(cards))
        if mode == 'slideshow':
            auto = 1 if data.get('autoplay') else 0
            spd = data.get('autoplaySpeed', 2.5)
            cards = ''.join('<figure class="gcard">%s</figure>' % im for im in cleaned)
            return ('<div class="gallery gallery-slideshow" data-autoplay="%s" data-speed="%s" %s>%s</div>'
                    % (auto, spd, gap, cards))
        # justify (default): equal-height rows that fill the width
        return '<div class="gallery gallery-justify" %s>%s</div>' % (gap, ''.join(cleaned))
    return re.sub(r'<div class="image-gallery" data-gallery="([^"]+)">(.*?)</div>',
                  repl, html, flags=re.S)

def clean_content(html):
    html = process_galleries(html)
    # any remaining (non-gallery) imgs
    html = re.sub(r'<img\b[^>]*>', lambda m: clean_img(m.group(0)), html)

    # videos: localize source, don't preload
    html = re.sub(r'<video\b', '<video preload="none"', html)
    html = re.sub(r'src="(https://(?:files\.cargocollective\.com|freight\.cargo\.site)/[^"]+)"',
                  lambda m: 'src="%s"' % (localize_files(m.group(1)) if 'cargocollective' in m.group(1)
                                          else localize_freight(m.group(1))), html)

    # download links to Cargo's CDN -> local copies where we have them (independence)
    html = re.sub(r'href="(https://(?:files\.cargocollective\.com|freight\.cargo\.site)/[^"]+)"',
                  lambda m: 'href="%s"' % (localize_files(m.group(1)) if 'cargocollective' in m.group(1)
                                           else localize_freight(m.group(1))), html)

    # internal links -> .html ; drop rel="history"
    html = html.replace('rel="history"', '')
    def link_sub(m):
        href = m.group(1)
        mm = re.match(r'https?://meowrhino\.cargo\.site/(.+)$', href)
        if mm: href = mm.group(1)
        base = href.split('?')[0].split('#')[0].strip('/')
        return 'href="%s.html"' % base if base in LINK_TARGETS else m.group(0)
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
  <script src="assets/gallery.js" defer></script>
</body>
</html>
"""

def lang_of(purl):
    if purl.endswith('_eng') or purl == 'homepage_eng': return 'en'
    if purl.endswith('_cat'): return 'ca'
    return 'es'

# welcome is a freeform page: the hand-drawn SVG markers sit at fixed coords; we
# pin each language word on top of its drawing so they always line up (no engine).
# coords are relative to .page top-left (measured from the rendered drawings).
WELCOME_LINKS = [
    ('home_1_esp', 'hola',    255, 248),  # red curve
    ('home_1_cat', 'bon dia', 778, 466),  # blue line
    ('home_1_eng', 'hello',   360, 624),  # yellow V
]

def build_welcome():
    n = NODES['welcome']
    po = n.get('page_options') or {}
    svg = (po.get('svg_overlay') or '').strip()
    lc = po.get('local_css') or ''
    lsid = local_style_id(lc)
    links = '\n'.join(
        '          <a href="%s.html" class="welcome-link" style="left:%dpx;top:%dpx">%s</a>'
        % (h, x, y, t) for h, t, x, y in WELCOME_LINKS)
    extra = ('.welcome-page{position:relative;min-height:760px}'
             '.welcome-link{position:absolute;font-size:1.4rem}'
             '@media(max-width:700px){.welcome-link{position:static;display:block;font-size:1.6rem;margin:.4em 0}'
             ' .welcome-page svg.marker-overlay{display:none}}')
    localcss = '  <style>\n%s\n%s\n  </style>\n' % (lc, extra)
    blocks = ('    <div class="page welcome-page"%s>\n'
              '      <bodycopy class="bodycopy content content_padding">\n'
              '        <div class="page_content"></div>\n'
              '        %s\n'
              '%s\n'
              '      </bodycopy>\n'
              '    </div>\n') % ((' local-style="%s"' % lsid) if lsid else '', svg, links)
    return PAGE_TMPL.format(lang='es', title='welcome — meowrhino', desc='hola · hello · bon dia',
                            localcss=localcss, blocks=blocks)

def build_page(purl):
    if purl == 'welcome':
        return build_welcome()
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
    """Localize url(...) refs to cargo hosts. NOTE: these CSS files live in
       assets/css/, so a local path 'assets/x' must be written '../x' to resolve."""
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
        if url.startswith('assets/'):      # rebase: CSS is in assets/css/
            url = '../' + url[len('assets/'):]
        return 'url(%s)' % url
    return re.sub(r'url\(([^)]+)\)', u, css)

def fix_webp_refs():
    """The freight images were optimized to .webp; point HTML refs at them."""
    import glob
    freight = os.path.join(OUT, 'assets/freight')
    webps = {os.path.basename(f)[:-5] for f in glob.glob(freight + '/*.webp')}  # name w/o .webp
    def r(m):
        base = m.group(1)
        return 'assets/freight/%s.webp' % base if base in webps else m.group(0)
    for fp in glob.glob(OUT + '/*.html'):
        s = open(fp, encoding='utf-8').read()
        n = re.sub(r'assets/freight/([^"\')\s]+)\.(?:png|jpe?g)', r, s, flags=re.IGNORECASE)
        if n != s: open(fp, 'w', encoding='utf-8').write(n)

def main():
    os.makedirs(os.path.join(OUT, 'assets/css'), exist_ok=True)
    # copy media assets from site/ ONLY if missing — preserves any optimization
    # (WebP conversion, video compression) already applied to clean/.
    for sub in ('freight', 'files', 'type', 'static'):
        src = os.path.join(ROOT, 'site/assets', sub)
        dst = os.path.join(OUT, 'assets', sub)
        if os.path.isdir(src) and not os.path.isdir(dst):
            shutil.copytree(src, dst)
            if sub == 'static':  # clean build doesn't use Cargo's engine JS; keep only fonts/images
                for rt, _, files in os.walk(dst):
                    for f in files:
                        if f.endswith('.js'): os.remove(os.path.join(rt, f))

    # foundation.css from the identical inline <style> block
    h = BUNDLE['UX-UI_esp']; head = h[:h.find('</head>')]
    foundation = max(re.findall(r'<style[^>]*>(.*?)</style>', head, re.S), key=len)
    open(os.path.join(OUT, 'assets/css/foundation.css'), 'w').write(localize_css_text(foundation))

    # base.css from the member stylesheet. The stylesheet USES "Young Serif" but
    # Cargo loaded its @font-face via a separate /type/css link we don't have, so
    # define it here (path is relative to this CSS file in assets/css/).
    member = open(os.path.join(ROOT, 'site/assets/css/member_stylesheet.css')).read()
    fontface = ('@font-face{font-family:"Young Serif";'
                'src:url(../type/YoungSerif-Regular.woff) format("woff");'
                'font-style:normal;font-weight:400;font-display:swap}\n')
    open(os.path.join(OUT, 'assets/css/base.css'), 'w').write(fontface + localize_css_text(member))

    # galleries.css + gallery.js (our clean layout + slideshow controller)
    open(os.path.join(OUT, 'assets/css/galleries.css'), 'w').write(GALLERIES_CSS)
    open(os.path.join(OUT, 'assets/gallery.js'), 'w').write(GALLERY_JS)

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
    fix_webp_refs()
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

/* ---- Typography base ----
   Cargo sets a FIXED root font-size; every size in base.css is in rem and derives
   from it. Matching it makes body=2rem=26.27px, h1=3rem=39.4px, h2=4rem, small=1.6rem
   render exactly like Cargo (the browser default 16px made everything ~22% too big). */
html{ font-size:13.1328px; }

/* Content images fit their container (Cargo applies this; without it the full-res
   originals overflow and the column shows only a cropped corner). */
.page_content img{ max-width:100%; height:auto; }

/* ---- Galleries (rebuilt from each gallery's real Cargo config) ---- */
.gallery{ --gap:6px; margin:.2rem 0; }
.gallery img{ display:block; max-width:100%; }
.gallery .gcard{ margin:0; }

/* Freeform: each card keeps the % width Cargo stored per image; cards flow+wrap. */
.gallery-freeform{ display:flex; flex-wrap:wrap; align-items:flex-start; }
.gallery-freeform .gcard{ box-sizing:border-box; padding:calc(var(--gap)/2); }
.gallery-freeform .gcard img{ width:100%; height:auto; }

/* Justify: equal-height rows that fill the width; a lone image stays modest. */
.gallery-justify{ display:flex; flex-wrap:wrap; gap:var(--gap); align-items:flex-start; }
.gallery-justify img{ height:300px; width:auto; flex:1 1 auto; object-fit:cover; }
.gallery-justify img:only-child{ height:auto; width:auto; max-width:420px; flex:0 0 auto; object-fit:contain; }

/* Slideshow: one image per view, horizontal scroll-snap carousel.
   gallery.js wraps it in .slideshow-wrap and adds arrows + autoplay. */
.slideshow-wrap{ position:relative; }
.gallery-slideshow{ display:flex; overflow-x:auto; scroll-snap-type:x mandatory; scroll-behavior:smooth;
  gap:var(--gap); -webkit-overflow-scrolling:touch; scrollbar-width:none; }
.gallery-slideshow::-webkit-scrollbar{ display:none; }
.gallery-slideshow .gcard{ flex:0 0 100%; scroll-snap-align:center; }
.gallery-slideshow .gcard img{ width:100%; height:auto; max-height:80vh; object-fit:contain; margin:0 auto; }
.gallery-arrow{ position:absolute; top:50%; transform:translateY(-50%); z-index:5; border:0;
  background:rgba(255,255,255,.7); color:#000; font:1.6rem/1 sans-serif; width:1.8em; height:1.8em;
  border-radius:50%; cursor:pointer; opacity:0; transition:opacity .2s; }
.slideshow-wrap:hover .gallery-arrow{ opacity:1; }
.gallery-arrow.prev{ left:.3rem; } .gallery-arrow.next{ right:.3rem; }

/* ---- Marquee: Cargo bounced these section titles back and forth across the
   width (behavior="bounce"). Reproduce the bounce; respect reduced-motion. ---- */
.marquee{ overflow:hidden !important; white-space:nowrap !important; }
.marquee > *{ display:inline-block; margin:0; position:relative; left:0;
  animation:marquee-bounce 9s ease-in-out infinite alternate; }
@keyframes marquee-bounce{ to{ left:100%; transform:translateX(-100%); } }
@media (prefers-reduced-motion:reduce){
  .marquee > *{ animation:none; left:50%; transform:translateX(-50%); } }

video{ max-width:100%; height:auto; }
"""

GALLERY_JS = """/* Slideshow controller: arrows + autoplay (only while in view, paused on hover).
   Swiping/scrolling works natively via CSS scroll-snap; this just enhances it. */
(function(){
  document.querySelectorAll('.gallery-slideshow').forEach(function(g){
    var cards = Array.prototype.filter.call(g.children, function(c){
      return c.classList && c.classList.contains('gcard'); });
    if(cards.length < 2) return;
    var wrap = document.createElement('div'); wrap.className = 'slideshow-wrap';
    g.parentNode.insertBefore(wrap, g); wrap.appendChild(g);
    var i = 0, timer = null, hovered = false, inview = false;
    function go(k){ i = (k + cards.length) % cards.length;
      g.scrollTo({ left: cards[i].offsetLeft - g.offsetLeft, behavior: 'smooth' }); }
    ['prev','next'].forEach(function(d){
      var b = document.createElement('button'); b.type = 'button';
      b.className = 'gallery-arrow ' + d;
      b.setAttribute('aria-label', d === 'prev' ? 'anterior' : 'siguiente');
      b.textContent = d === 'prev' ? '\\u2039' : '\\u203A';
      b.addEventListener('click', function(){ pause(); go(d === 'prev' ? i - 1 : i + 1); });
      wrap.appendChild(b);
    });
    var st; g.addEventListener('scroll', function(){ clearTimeout(st);
      st = setTimeout(function(){ i = Math.round(g.scrollLeft / g.clientWidth) % cards.length; }, 120); });
    function play(){ if(timer || !inview || hovered || g.dataset.autoplay !== '1') return;
      var ms = (parseFloat(g.dataset.speed) || 2.5) * 1000 + 2000;
      timer = setInterval(function(){ go(i + 1); }, ms); }
    function pause(){ if(timer){ clearInterval(timer); timer = null; } }
    wrap.addEventListener('mouseenter', function(){ hovered = true; pause(); });
    wrap.addEventListener('mouseleave', function(){ hovered = false; play(); });
    if('IntersectionObserver' in window){
      new IntersectionObserver(function(es){ es.forEach(function(e){
        inview = e.isIntersecting; if(inview) play(); else pause(); }); }, { threshold: 0.4 }).observe(wrap);
    } else { inview = true; play(); }
  });
})();
"""

if __name__ == '__main__':
    main()

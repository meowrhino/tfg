#!/usr/bin/env python3
"""Phase 1: discover every owned asset URL across all pages, map to a local path, download."""
import json, re, os, hashlib, subprocess
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, 'site')
BUNDLE = json.load(open(os.path.join(ROOT, 'cargo_bundle.json')))

OWNED = ('freight.cargo.site', 'files.cargocollective.com',
         'static.cargo.site', 'type.cargo.site')

# A URL as it may appear in HTML/JSON: optional scheme, // or \/\/, host, path+query.
# Path/query chars include backslash so we capture escaped slashes \/ too.
URL_RE = re.compile(
    r'(?:https?:)?(?:\\?/){2}(freight\.cargo\.site|files\.cargocollective\.com|static\.cargo\.site|type\.cargo\.site)'
    r'(?:\\?/[A-Za-z0-9_~:.\-+%=&?]+)*'
)
# meowrhino stylesheet endpoint (the only meowrhino asset we localize here)
STYLE_RE = re.compile(r'(?:https?:)?(?:\\?/){2}meowrhino\.cargo\.site\\?/stylesheet(?:\?[A-Za-z0-9_&=]+)?')

def clean(s):
    """Turn an as-appears match into a real URL (unescape \\/ )."""
    u = s.replace('\\/', '/')
    if u.startswith('//'):
        u = 'https:' + u
    return u

def local_for(real_url):
    """Map a real URL to (fs_path, rel_href) under site/."""
    p = urlparse(real_url)
    host, path = p.netloc, p.path
    if host == 'freight.cargo.site':
        name = unquote(path.rsplit('/', 1)[-1]) or 'img'
        h = hashlib.md5(path.encode()).hexdigest()[:10]
        fn = f"{h}_{name}"
        return (f"assets/freight/{fn}", f"assets/freight/{fn}")
    if host == 'files.cargocollective.com':
        name = unquote(path.rsplit('/', 1)[-1]) or 'file'
        return (f"assets/files/{name}", f"assets/files/{name}")
    if host == 'static.cargo.site':
        rel = 'assets/static' + path  # preserve path
        return (rel, rel)
    if host == 'type.cargo.site':
        name = path.rsplit('/', 1)[-1]
        return (f"assets/type/{name}", f"assets/type/{name}")
    raise ValueError(real_url)

def main():
    # appearance-string -> real url
    appear = {}
    for html in BUNDLE.values():
        for m in URL_RE.finditer(html):
            s = m.group(0)
            appear[s] = clean(s)
    # stylesheet appearances -> single local css
    style_appear = set()
    for html in BUNDLE.values():
        for m in STYLE_RE.finditer(html):
            style_appear.add(m.group(0))

    # Build real-url -> local map (dedup by real url)
    real_to_local = {}
    for s, real in appear.items():
        if real not in real_to_local:
            real_to_local[real] = local_for(real)

    # mapping appearance-string -> rel_href (what we substitute in HTML)
    sub = {}
    for s, real in appear.items():
        sub[s] = real_to_local[real][1]
    for s in style_appear:
        sub[s] = 'assets/css/member_stylesheet.css'

    # Download every distinct real url
    os.makedirs(SITE, exist_ok=True)
    dl = []  # (real_url, fs_path)
    for real, (fs, rel) in real_to_local.items():
        dl.append((real, os.path.join(SITE, fs)))

    print(f"{len(appear)} distinct URL appearances, {len(real_to_local)} distinct assets to download")
    ok = fail = 0
    for real, fs in dl:
        os.makedirs(os.path.dirname(fs), exist_ok=True)
        if os.path.exists(fs) and os.path.getsize(fs) > 0:
            ok += 1; continue
        r = subprocess.run(['curl', '-s', '-f', '-A', 'Mozilla/5.0', '-o', fs, real],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(fs) and os.path.getsize(fs) > 0:
            ok += 1
        else:
            fail += 1
            print("  FAIL", real[:120])
    print(f"downloaded ok={ok} fail={fail}")

    # Save substitution map for phase 2
    json.dump(sub, open(os.path.join(ROOT, 'asset_subs.json'), 'w'))
    # also save the real->local for reference
    json.dump({k: v[1] for k, v in real_to_local.items()},
              open(os.path.join(ROOT, 'asset_map.json'), 'w'), indent=1)
    print("saved asset_subs.json (%d entries)" % len(sub))

if __name__ == '__main__':
    main()

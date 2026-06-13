#!/usr/bin/env python3
"""Generate site/assets/localize.js: rewrites runtime freight.cargo.site image URLs
   to local copies, keyed by the content hash. Keeps the Cargo engine intact."""
import json, re, os
ROOT = os.path.dirname(os.path.abspath(__file__))
m = json.load(open(os.path.join(ROOT, 'asset_map.json')))

# hash -> best local file (prefer /t/original, then largest /w/NNN)
def rank(url):
    if '/t/original/' in url: return 10**9
    w = re.search(r'/w/(\d+)/', url)
    return int(w.group(1)) if w else 0

best = {}  # hash -> (rank, local)
for url, local in m.items():
    if 'freight.cargo.site' not in url: continue
    mm = re.search(r'/i/([a-f0-9]{16,})/', url)
    if not mm: continue
    h = mm.group(1)
    r = rank(url)
    if h not in best or r > best[h][0]:
        best[h] = (r, local)

hashmap = {h: v[1] for h, (r, v) in ((h, (b[0], b[1])) for h, b in best.items())}
hashmap = {h: best[h][1] for h in best}

js = """/* Local-asset shim for the recovered Cargo site.
   1) Reroots the engine's absolute server paths (/_jsapps, /_api, ...) so the site
      works under a GitHub Pages project subpath (user.github.io/repo/), not just at root.
   2) Redirects runtime freight.cargo.site image URLs to local copies (by content hash),
      so images are served locally and the site no longer depends on cargo.site.
   The Cargo engine still renders galleries/layout/interactivity. */
(function(){
  // --- (1) reroot absolute internal paths to be relative to this page's directory ---
  var BASE = location.pathname.replace(/[^/]*$/, '');  // e.g. "/repo/" or "/"
  function reroot(u){
    if(typeof u!=='string') return u;
    return /^\\/(?:_jsapps|_api|stylesheet|type|rss|followingframe)\\b/.test(u)
      ? BASE + u.replace(/^\\//,'') : u;
  }
  var _fetch = window.fetch;
  if(_fetch) window.fetch = function(input, init){
    try{
      if(typeof input==='string') input = reroot(input);
      else if(input && input.url) input = new Request(reroot(input.url), input);
    }catch(e){}
    return _fetch.call(this, input, init);
  };
  var _open = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(){
    try{ if(arguments.length>1) arguments[1] = reroot(arguments[1]); }catch(e){}
    return _open.apply(this, arguments);
  };

  // --- (2) freight image URL -> local copy, by content hash ---
  var M = %s;
  function loc(u){
    if(!u || u.indexOf('freight.cargo.site')<0) return u;
    var m = u.match(/\\/i\\/([a-f0-9]{16,})\\//);
    return (m && M[m[1]]) ? M[m[1]] : u;
  }
  function fixImg(img){
    var s=img.getAttribute('src'), l=loc(s); if(l!==s) img.setAttribute('src', l);
    var d=img.getAttribute('data-src'), dl=loc(d); if(d&&dl!==d) img.setAttribute('data-src', dl);
  }
  function fixBg(el){
    var st=el.getAttribute && el.getAttribute('style');
    if(st && st.indexOf('freight.cargo.site')>=0){
      el.setAttribute('style', st.replace(/freight\\.cargo\\.site\\/[^"')]*?\\/i\\/([a-f0-9]{16,})\\/[^"')]*/g,
        function(full,h){ return M[h] ? M[h] : full; }));
    }
  }
  function scan(root){
    (root||document).querySelectorAll && (root||document).querySelectorAll('img').forEach(fixImg);
    (root||document).querySelectorAll && (root||document).querySelectorAll('[style*="freight.cargo.site"]').forEach(fixBg);
  }
  try{
    new MutationObserver(function(muts){
      for(var i=0;i<muts.length;i++){var mu=muts[i];
        if(mu.type==='attributes'){ if(mu.target.tagName==='IMG') fixImg(mu.target); else fixBg(mu.target); }
        if(mu.addedNodes) for(var j=0;j<mu.addedNodes.length;j++){var n=mu.addedNodes[j];
          if(n.tagName==='IMG') fixImg(n); if(n.nodeType===1) scan(n);}
      }
    }).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src','data-src','style']});
  }catch(e){}
  if(document.readyState!=='loading') scan(); else document.addEventListener('DOMContentLoaded',function(){scan();});
  var n=0,iv=setInterval(function(){scan(); if(++n>20) clearInterval(iv);},400); // ~8s safety net
})();
""" % json.dumps(hashmap)

os.makedirs(os.path.join(ROOT, 'site/assets'), exist_ok=True)
open(os.path.join(ROOT, 'site/assets/localize.js'), 'w').write(js)
print("wrote site/assets/localize.js with", len(hashmap), "hash mappings")

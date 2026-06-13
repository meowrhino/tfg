/* Slideshow controller: arrows + autoplay (only while in view, paused on hover).
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
      b.textContent = d === 'prev' ? '\u2039' : '\u203A';
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

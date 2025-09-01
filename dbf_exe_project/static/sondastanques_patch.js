/*! sondastanques_patch.js — TankFuel PATCH v001c (force gradient + stop movement) */
(function(){
  function cssVar(name, fallback){
    try{ const v = getComputedStyle(document.documentElement).getPropertyValue(name);
      return (v && v.trim()) || fallback; }catch(e){ return fallback; }
  }
  function colorForPercent(p){
    if (p <= 20) return cssVar('--bad', '#ff3b30');
    if (p <= 50) return cssVar('--warn','#ffa500');
    if (p <= 90) return cssVar('--good','#00cc44');
    return cssVar('--brand-2','#66ff99');
  }
  function gradientFor(color){
    return `linear-gradient(180deg, rgba(255,255,255,.06) 0%, rgba(255,255,255,.02) 10%, ${color} 12%)`;
  }
  function guessPercent(card){
    const pctNode = card.querySelector('[data-percent]');
    if(pctNode){
      const val = pctNode.getAttribute('data-percent');
      if(val!=null && val!==""){
        const n = Number(String(val).replace(',','.'));
        if(Number.isFinite(n)) return n;
      }
    }
    const badge = card.querySelector('.percent-badge, .pct, .badge');
    if(badge){
      const m = (badge.textContent||'').match(/(\d+(?:[.,]\d+)?)\s*%/);
      if(m){ const n = Number(m[1].replace(',', '.')); if(Number.isFinite(n)) return n; }
    }
    const vol = card.querySelector('[data-volumen],[data-volume]');
    const cap = card.querySelector('[data-capacidad],[data-capacity]');
    if(vol && cap){
      const v = Number((vol.getAttribute('data-volumen')||vol.getAttribute('data-volume')||'').replace(',','.'));
      const c = Number((cap.getAttribute('data-capacidad')||cap.getAttribute('data-capacity')||'').replace(',','.'));
      if(Number.isFinite(v) && Number.isFinite(c) && c>0) return (v*100)/c;
    }
    return NaN;
  }
  function paintFill(card, percent){
    const tank = card.querySelector('.tank');
    const fill = card.querySelector('.liquid, .tank-fill');
    if(!tank || !fill) return;
    const p = Math.max(0, Math.min(100, Number(percent)||0));

    try{
      tank.style.filter='none';
      fill.style.filter='none';
      fill.style.transition='none';
      fill.style.animation='none';
      fill.style.transform='translateZ(0)';
      fill.style.imageRendering='-webkit-optimize-contrast';
      fill.style.backfaceVisibility='hidden';
    }catch(e){}

    fill.style.height = p + '%';

    const color = (function(p){
      if (p <= 20) return getComputedStyle(document.documentElement).getPropertyValue('--bad').trim() || '#ff3b30';
      if (p <= 50) return getComputedStyle(document.documentElement).getPropertyValue('--warn').trim() || '#ffa500';
      if (p <= 90) return getComputedStyle(document.documentElement).getPropertyValue('--good').trim() || '#00cc44';
      return getComputedStyle(document.documentElement).getPropertyValue('--brand-2').trim() || '#66ff99';
    })(p);

    fill.style.setProperty('--tank-color', color);
    fill.style.backgroundImage = `linear-gradient(180deg, rgba(255,255,255,.06) 0%, rgba(255,255,255,.02) 10%, ${color} 12%)`;
    fill.style.backgroundColor = color;
  }
  function scanAndPaint(){
    document.querySelectorAll('.tank-card, .card').forEach(card=>{
      const p = guessPercent(card);
      if(Number.isFinite(p)) paintFill(card, p);
    });
  }
  (function hook(){
    let orig=null, tries=0;
    const iv=setInterval(function(){
      tries++;
      if(typeof window.setData==='function'){
        if(!orig){
          orig = window.setData;
          window.setData = function(){
            const ret = orig.apply(this, arguments);
            requestAnimationFrame(scanAndPaint);
            return ret;
          };
        }
        clearInterval(iv);
      } else if(tries>60){ clearInterval(iv); }
    },100);
  })();
  if(document.readyState==='loading'){
    document.addEventListener('DOMContentLoaded', scanAndPaint);
  }else{ scanAndPaint(); }
  window.TankFuelPatch = Object.assign(window.TankFuelPatch||{}, { repaint: scanAndPaint });
})();
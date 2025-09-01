/*! sondastanques_patch.js — TankFuel PATCH v001
 *  Cárgalo DESPUÉS de tu sondastanques_mod.js original.
 *  No renderiza nada; solo añade nitidez y color al líquido.
 *  Seguro incluso si window.setData no existe.
 */
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
      fill.style.transform='translateZ(0)';
      fill.style.imageRendering='-webkit-optimize-contrast';
    }catch(e){}
    fill.style.height = p + '%';
    const color = colorForPercent(p);
    fill.style.setProperty('--tank-color', color);
    const currentBg = getComputedStyle(fill).backgroundImage || '';
    if(!currentBg || currentBg.indexOf('linear-gradient') === -1){
      fill.style.background = color;
    }
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

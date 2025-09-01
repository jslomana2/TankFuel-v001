
/* STATUS TEXT + ICON Patch (non-intrusive) */
(function(){
  function parseRgb(s){ const m = /(\d+)[^\d]+(\d+)[^\d]+(\d+)/.exec(s||""); return m?{r:+m[1],g:+m[2],b:+m[3]}:null; }
  function dist(a,b){ const dx=a.r-b.r, dy=a.g-b.g, dz=a.b-b.b; return Math.sqrt(dx*dx+dy*dy+dz*dz); }
  const CLR = {
    rojo:     {r:239,g:68, b:68},
    naranja:  {r:245,g:158,b:11},
    verde:    {r:34, g:197,b:94},
    verclaro: {r:134,g:239,b:172}
  };
  function labelFromColor(rgb){
    if(!rgb) return null;
    const c = parseRgb(rgb); if(!c) return null;
    const scores = [
      ['Bajo',     dist(c, CLR.rojo)],
      ['Medio',    dist(c, CLR.naranja)],
      ['Alto',     dist(c, CLR.verde)],
      ['Muy alto', dist(c, CLR.verclaro)]
    ].sort((a,b)=>a[1]-b[1]);
    return scores[0][0];
  }
  function ensureStatusBits(card){
    let status = card.querySelector('.status');
    if(!status){
      const h3 = card.querySelector('h3') || card.querySelector('.title, header');
      if(!h3) return {};
      status = document.createElement('span');
      status.className = 'status';
      h3.appendChild(status);
    }
    let dot = status.querySelector('.dot, .status-dot');
    if(!dot){
      dot = document.createElement('span');
      dot.className = 'dot';
      dot.style.display = 'inline-block';
      dot.style.width = '8px'; dot.style.height = '8px'; dot.style.borderRadius='50%';
      dot.style.marginLeft = '8px';
      status.appendChild(dot);
    }
    let icon = status.querySelector('.status-icon');
    if(!icon){
      icon = document.createElement('span');
      icon.className = 'status-icon';
      icon.style.marginLeft = '8px';
      icon.style.display = 'none';
      status.appendChild(icon);
    }
    let text = status.querySelector('.status-text, .status-label');
    if(!text){
      text = document.createElement('span');
      text.className = 'status-text';
      text.style.marginLeft = '8px';
      status.appendChild(text);
    }
    return {status, dot, icon, text};
  }
  function applyOne(card){
    const bits = ensureStatusBits(card);
    if(!bits.status) return;
    const rgb = getComputedStyle(bits.dot).backgroundColor;
    let label = labelFromColor(rgb);
    // Si no hay color en el dot (p.e., sin fondo), intentamos por porcentaje visible en tarjeta
    if(!label){
      // Busca un porcentaje visible en elementos típicos
      const cand = card.querySelector('[data-percent], .badge, .percent, .pct, .porcentaje');
      let p = null;
      if(cand){
        const m = String(cand.getAttribute('data-percent')||cand.textContent||'').match(/(\d+(?:[.,]\d+)?)\s*%/);
        if(m) p = parseFloat(m[1].replace(',','.'));
      }
      if(p!=null){
        if(p<=20) label='Bajo';
        else if(p<=50) label='Medio';
        else if(p<=90) label='Alto';
        else label='Muy alto';
      }
    }
    if(!label) return; // nada que hacer
    // Toggle icono/bola y texto
    if(label==='Bajo'){
      bits.icon.textContent = '⚠';
      bits.icon.style.display = 'inline';
      bits.icon.style.color = '#ef4444';
      bits.dot.style.display = 'none';
    }else{
      bits.icon.style.display = 'none';
      bits.dot.style.display = 'inline-block';
    }
    bits.text.textContent = label;
    // Reemplazar "Normal" que esté suelto en el título
    const h3 = card.querySelector('h3');
    if(h3){
      h3.childNodes.forEach(n=>{
        if(n.nodeType===3 && /normal/i.test(n.textContent)) n.textContent = ' '+label;
      });
    }
  }
  function apply(root){
    (root.querySelectorAll('.card, .tank-card, [data-tanque-id], [data-tank-id]')||[]).forEach(applyOne);
  }
  document.addEventListener('DOMContentLoaded',()=>{
    const container = document.getElementById('grid-tanques') || document.body;
    apply(document);
    new MutationObserver(()=>apply(document)).observe(container,{childList:true,subtree:true});
    const ref = document.getElementById('btn-refresh');
    if(ref) ref.addEventListener('click', ()=> setTimeout(()=>apply(document),0));
  });
})();

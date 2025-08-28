/*
  Patch "solo texto de estado" (no toca estilos ni tu render):
  - Actualiza el texto junto al punto (o icono) según % o color detectado.
  - Intenta varias formas de leer el % (data-percent, .badge, .tank-fill height).
  - Si no encuentra % pero sí detecta el color del punto, mapea color->texto.
  - Se ejecuta en carga y cada vez que se re-pintan tarjetas (MutationObserver).
*/
(function(){
  const LOG = false;
  const Q_CARDS = '.card, .tank-card';
  const COLOR_TARGETS = ['.status .dot', '.status-dot', '.dot'];

  function log(...a){ if(LOG) console.log('[status-patch]', ...a); }
  function num(x){ return Number(String(x).replace(',', '.')); }

  function parsePercent(card){
    // 1) data-percent en la tarjeta
    const attr = card.getAttribute('data-percent');
    if (attr !== null && attr !== '') return num(attr);
    // 2) data-percent en elementos hijos típicos
    const any = card.querySelector('[data-percent]');
    if (any) return num(any.getAttribute('data-percent'));
    // 3) .badge "23 %"
    const b = card.querySelector('.badge');
    if (b){
      const m = b.textContent.match(/(\d+(?:[.,]\d+)?)\s*%/);
      if (m) return num(m[1]);
    }
    // 4) style height:23% de .tank-fill
    const fill = card.querySelector('.tank-fill');
    if (fill){
      const m = (fill.getAttribute('style') || '').match(/height:\s*([\d.]+)%/i);
      if (m) return num(m[1]);
    }
    // 5) atributo aria-valuenow / data-value
    const a = card.querySelector('[aria-valuenow]');
    if (a) return num(a.getAttribute('aria-valuenow'));
    const dv = card.querySelector('[data-value]');
    if (dv) return num(dv.getAttribute('data-value'));
    return NaN;
  }

  function rgbToStatusText(rgb){
    // rgb: "rgb(r, g, b)"
    const m = rgb && rgb.match(/(\d+)[^\d]+(\d+)[^\d]+(\d+)/);
    if(!m) return null;
    const r = +m[1], g = +m[2], b = +m[3];
    // Heurística simple
    if (r > 200 && g < 120) return 'Bajo';         // rojo
    if (r > 200 && g > 200) return 'Muy alto';     // muy claro
    if (g > 170 && r < 120) return 'Alto';         // verde
    if (r > 200 && g > 120 && g < 200) return 'Medio'; // naranja
    // fallback por componente dominante
    if (r > g+40) return 'Bajo';
    if (g > r+40) return 'Alto';
    return null;
  }

  function statusForPercent(p){
    if (!(p >= 0)) return null;
    if (p <= 20) return 'Bajo';
    if (p <= 50) return 'Medio';
    if (p <= 90) return 'Alto';
    return 'Muy alto';
  }

  function findDot(card){
    for (const sel of COLOR_TARGETS){
      const el = card.querySelector(sel);
      if (el) return el;
    }
    return null;
  }
  function findLabel(card){
    // etiqueta preferente
    let t = card.querySelector('.status-text, .status-label');
    if (t) return t;
    // si no hay etiqueta, crea una junto al dot
    const dot = findDot(card);
    if (dot && dot.parentElement){
      t = document.createElement('span');
      t.className = 'status-text';
      t.style.marginLeft = '8px';
      dot.parentElement.appendChild(t);
      return t;
    }
    return null;
  }

  function applyToCard(card){
    // 1) Por porcentaje
    const p = parsePercent(card);
    const fromP = statusForPercent(p);
    if (fromP){
      const label = findLabel(card);
      if (label) label.textContent = fromP;
      return;
    }
    // 2) Por color detectado en el punto
    const dot = findDot(card);
    if (dot){
      // Por clase semántica
      const cls = dot.className.toLowerCase();
      if (/bad|danger|rojo|red/.test(cls)) return (findLabel(card)||{}).textContent = 'Bajo';
      if (/warn|orange|naranja/.test(cls)) return (findLabel(card)||{}).textContent = 'Medio';
      if (/ok|verde|green/.test(cls)) return (findLabel(card)||{}).textContent = 'Alto';
      if (/very|light|claro/.test(cls)) return (findLabel(card)||{}).textContent = 'Muy alto';
      // Por color computado
      const rgb = getComputedStyle(dot).backgroundColor;
      const t = rgbToStatusText(rgb);
      if (t){
        const label = findLabel(card);
        if (label) label.textContent = t;
      }
    }
  }

  function apply(root){
    (root.querySelectorAll(Q_CARDS) || []).forEach(applyToCard);
  }

  const container = document.getElementById('grid-tanques') || document.body;
  apply(document);
  const mo = new MutationObserver(m => apply(document));
  mo.observe(container, { childList:true, subtree:true });

  const ref = document.getElementById('btn-refresh');
  if (ref) ref.addEventListener('click', ()=> setTimeout(()=>apply(document),0));
})();
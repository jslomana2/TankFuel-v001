/*! sondastanques_mod.js — TankFuel PATCH v001 (non-destructive)
 *  Objetivos:
 *   - Pintar el líquido del tanque con color nítido según porcentaje
 *   - Mantener tu layout/HTML sin exigir cambios
 *   - Evitar borrosidad por filtros heredados
 *   - Fallbacks seguros y sin romper tu lógica existente
 */

/* ---------------- Utilidades de color ------------------ */
function tf_cssVar(name, fallback){
  try {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name);
    return (v && v.trim()) || fallback;
  } catch(e){
    return fallback;
  }
}

function tf_getTankColor(percent){
  // Usa tus variables CSS si existen; si no, fallback
  if (percent <= 20) return tf_cssVar('--bad', '#ff3b30');
  if (percent <= 50) return tf_cssVar('--warn', '#ffa500');
  if (percent <= 90) return tf_cssVar('--good', '#00cc44');
  return tf_cssVar('--brand-2', '#66ff99');
}

/* -------------- Pintado nítido del líquido -------------- */
function tf_paintFillInCard(card, percent){
  // card debería ser .card o .tank-card; buscamos .tank y .liquid
  const tank = card.querySelector('.tank');
  const fill = card.querySelector('.liquid, .tank-fill');
  if(!tank || !fill) return;

  const p = Math.max(0, Math.min(100, Number(percent)||0));
  // Asegurar nitidez y evitar filtros heredados
  try {
    tank.style.filter = 'none';
    fill.style.filter = 'none';
    fill.style.transform = 'translateZ(0)';
    fill.style.imageRendering = '-webkit-optimize-contrast';
  } catch(e){ /* no-op */ }

  // Altura
  fill.style.height = p + '%';

  // Color (respetando tu gradiente base si lo tienes: usamos CSS custom prop)
  const color = tf_getTankColor(p);
  fill.style.setProperty('--tank-color', color);
  // Si tu CSS base usa un gradiente con color final, intenta asignarlo
  // sin destruir tu background (muchos usan linear-gradient con un color final):
  const currentBg = getComputedStyle(fill).backgroundImage || '';
  if(!currentBg || currentBg.indexOf('linear-gradient') === -1){
    // Fallback: color directo
    fill.style.background = color;
  }
}

/* -------------- Lectura de porcentaje en la tarjeta ------ */
function tf_guessPercent(card){
  // 1) data-percent en algún nodo
  const pctNode = card.querySelector('[data-percent]');
  if (pctNode){
    const val = pctNode.getAttribute('data-percent');
    if (val != null && val !== '') {
      const n = Number(String(val).replace(',', '.'));
      if (Number.isFinite(n)) return n;
    }
  }
  // 2) texto como "48 %" en badges
  const badge = card.querySelector('.percent-badge, .pct, .badge');
  if (badge){
    const m = (badge.textContent||'').match(/(\d+(?:[.,]\d+)?)\s*%/);
    if (m) {
      const n = Number(m[1].replace(',', '.'));
      if (Number.isFinite(n)) return n;
    }
  }
  // 3) data-volume/data-capacity
  const vol = card.querySelector('[data-volumen],[data-volume]');
  const cap = card.querySelector('[data-capacidad],[data-capacity]');
  if (vol && cap){
    const v = Number((vol.getAttribute('data-volumen')||vol.getAttribute('data-volume')||'').replace(',','.'));
    const c = Number((cap.getAttribute('data-capacidad')||cap.getAttribute('data-capacity')||'').replace(',','.'));
    if (Number.isFinite(v) && Number.isFinite(c) && c>0){
      return (v*100)/c;
    }
  }
  return NaN;
}

/* -------------- Repintado de todas las tarjetas ---------- */
function tf_scanAndPaintAll(){
  const cards = document.querySelectorAll('.tank-card, .card');
  cards.forEach(card=>{
    const p = tf_guessPercent(card);
    if(Number.isFinite(p)) tf_paintFillInCard(card, p);
  });
}

/* -------------- Nombre de almacén (opcional/fallback) ----- */
function tf_setAlmacenNombre(value){
  const txt = (value && String(value).trim()) ? String(value).trim() : '–';
  const nodes = document.querySelectorAll('.toolbar .almacen-nombre, .header .almacen-nombre, #almacenNombre');
  nodes.forEach(n=>{
    n.textContent = txt;
  if(!txt || txt === '–') n.classList.remove('badge'); // evita “cuadro” vacío estilizado
  });
}

/* -------------- Enganche no intrusivo a setData ----------- */
(function hookSetData(){
  let orig = null, tries=0;
  const iv = setInterval(function(){
    tries++;
    if (typeof window.setData === 'function'){
      if (!orig){
        orig = window.setData;
        window.setData = function(input){
          // Ejecuta tu setData original
          const ret = orig.apply(this, arguments);

          // Fijar nombre de almacén si viene info
          try{
            if (input && Array.isArray(input.almacenes) && input.almacenes.length){
              let nombre = '–';
              if (input.activoId == null){
                nombre = 'Todos';
              }else{
                const a = input.almacenes.find(x=> String(x.id) === String(input.activoId)) || input.almacenes[0];
                nombre = (a && a.nombre) ? a.nombre : '–';
              }
              tf_setAlmacenNombre(nombre);
            }
          }catch(e){ /* silencioso */ }

          // Tras render, repinta el líquido de todas las tarjetas
          requestAnimationFrame(tf_scanAndPaintAll);
          return ret;
        };
      }
      clearInterval(iv);
    }else if(tries>60){ // ~6s
      clearInterval(iv);
    }
  }, 100);
})();

/* -------------- Primera pasada ----------------------------- */
if (document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', tf_scanAndPaintAll);
}else{
  tf_scanAndPaintAll();
}

/* -------------- API pública opcional ----------------------- */
window.TankFuelUI = Object.assign(window.TankFuelUI || {}, {
  repaint: tf_scanAndPaintAll,
  setWarehouseName: tf_setAlmacenNombre,
  colorForPercent: tf_getTankColor
});

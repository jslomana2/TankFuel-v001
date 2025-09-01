// === Patch v001 — nitidez de color, nombre de almacén y cuadro vacío ===

// Helper: color del líquido según %
function tf_getTankColor(percent){
  if(percent <= 20) return getComputedStyle(document.documentElement).getPropertyValue('--tank-low') || '#ff3b30';
  if(percent <= 50) return getComputedStyle(document.documentElement).getPropertyValue('--tank-med') || '#ffa500';
  if(percent <= 90) return getComputedStyle(document.documentElement).getPropertyValue('--tank-high')|| '#00cc44';
  return getComputedStyle(document.documentElement).getPropertyValue('--tank-max') || '#66ff99';
}

// Aplica color de forma NÍTIDA (sin blur heredado)
function tf_paintFill(tankNode, percent){
  const fill = tankNode.querySelector('.tank-fill');
  if(!fill) return;
  const color = tf_getTankColor(percent);
  fill.style.setProperty('--tank-color', color.trim());
  fill.style.height = Math.max(0, Math.min(100, percent)) + '%';
}

// Pinta cabecera de almacén con fallback a “–” y sin cuadros vacíos
function tf_setAlmacenNombre(value){
  const nodes = document.querySelectorAll('.toolbar .almacen-nombre, .header .almacen-nombre');
  const txt = (value && String(value).trim()) ? String(value).trim() : '–';
  nodes.forEach(n=>{
    n.textContent = txt;
    if(!txt || txt === '–') n.classList.remove('badge'); // evita pill vacío estilo badge
  });
}

// Cuando montes cada tarjeta de tanque, llama a tf_paintFill
// Ejemplo de integración (ajusta a tu render actual):
window.addEventListener('DOMContentLoaded', ()=>{
  document.querySelectorAll('.tank-card').forEach(card=>{
    const pctNode = card.querySelector('[data-percent]');
    const percent = pctNode ? Number(pctNode.getAttribute('data-percent')) : NaN;
    if(!Number.isFinite(percent)) return;
    tf_paintFill(card, percent);
  });
});

// Si tu backend cambia el almacén seleccionado, usa:
// tf_setAlmacenNombre(datos?.almacen_descripcion);

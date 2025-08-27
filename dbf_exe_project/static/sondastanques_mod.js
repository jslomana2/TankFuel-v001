
async function getJSON(url){ const r = await fetch(url); if(!r.ok) throw new Error(await r.text()); return r.json(); }
const qs=(s,el=document)=>el.querySelector(s);
const qsa=(s,el=document)=>[...el.querySelectorAll(s)];

function formatNum(n){ if(n==null) return "—"; return Intl.NumberFormat('es-ES',{maximumFractionDigits:2}).format(n); }
function pct(n){ return Intl.NumberFormat('es-ES',{maximumFractionDigits:1}).format(n); }

async function loadAlmacenes(){
  const data = await getJSON('/api/almacenes?n=5');
  const sel = qs('#almacenSelect'); sel.innerHTML="";
  (data.almacenes||[]).forEach(a => {
    const opt = document.createElement('option');
    opt.value = a.codigo; opt.textContent = `${a.codigo} – ${a.nombre}`;
    sel.appendChild(opt);
  });
  return sel.value || null;
}

function renderResumen(arr){
  const host = qs('#resumen'); host.innerHTML = "";
  if(!arr || !arr.length){ host.textContent = "Sin datos."; return; }
  arr.forEach(r => {
    const row = document.createElement('div'); row.className='row';
    const tag = document.createElement('div'); tag.className='tag';
    const dot = document.createElement('span'); dot.className='dot'; dot.style.background = r.color_hex || '#444';
    const name = document.createElement('b'); name.textContent = r.producto_nombre || r.producto || "Producto";
    const stats = document.createElement('span'); stats.textContent = `${formatNum(r.total_litros15)} L · ${pct(r.porcentaje)}% · ${r.num_tanques} tqs`;
    tag.append(dot,name);
    const bar = document.createElement('div'); bar.className='bar';
    const fill = document.createElement('i'); fill.style.width = `${r.porcentaje}%`; fill.style.background = r.color_hex || '#555';
    bar.appendChild(fill);
    row.append(tag, stats);
    host.append(row, bar);
  });
}

function renderGrid(tanques){
  const grid = qs('#grid'); grid.innerHTML = "";
  if(!tanques || !tanques.length){ grid.innerHTML = '<div class="empty">Sin tanques con lecturas válidas.</div>'; return; }
  tanques.forEach(t=>{
    const card = document.createElement('div'); card.className='tank';
    const top = document.createElement('div'); top.className='head';
    const name = document.createElement('div'); name.className='name'; name.textContent = `${t.tanque_nombre||'Tanque'} · ${t.tanque}`;
    const chip = document.createElement('div'); chip.className='chip';
    const dot = document.createElement('span'); dot.className='dot'; dot.style.background = t.producto_color || '#888';
    const prod = document.createElement('span'); prod.textContent = t.producto_nombre || t.producto || 'Producto';
    chip.append(dot,prod); top.append(name, chip);

    const meta = document.createElement('div'); meta.className='meta';
    meta.innerHTML = `
      <div class="kv"><label>Capacidad</label><b>${formatNum(t.capacidad)} L</b></div>
      <div class="kv"><label>Temperatura</label><b>${formatNum(t.temperatura)} ºC</b></div>
      <div class="kv"><label>Volumen</label><b>${formatNum(t.volumen)} L</b></div>
      <div class="kv"><label>Litros a 15º</label><b>${formatNum(t.litros15)} L</b></div>
    `;
    card.append(top, meta);

    card.addEventListener('click', ()=>{
      qs('#detalle').innerHTML = `
        <div class="kv"><label>Tanque</label><b>${t.tanque} — ${t.tanque_nombre||''}</b></div>
        <div class="kv"><label>Producto</label><b>${t.producto} — ${t.producto_nombre||''}</b></div>
        <div class="kv"><label>Temperatura</label><b>${formatNum(t.temperatura)} ºC</b></div>
        <div class="kv"><label>Volumen</label><b>${formatNum(t.volumen)} L</b></div>
        <div class="kv"><label>Litros 15º</label><b>${formatNum(t.litros15)} L</b></div>
      `;
    });

    grid.appendChild(card);
  });
}

async function loadYpintar(){
  const sel = qs('#almacenSelect');
  const cod = sel.value;
  const data = await getJSON(`/api/tanques_norm?almacen=${encodeURIComponent(cod)}&n=5`);
  renderGrid(data.tanques||[]);
  renderResumen(data.resumen_productos||[]);
}

document.addEventListener('DOMContentLoaded', async () => {
  const cod = await loadAlmacenes();
  await loadYpintar();
  qs('#refreshBtn').addEventListener('click', loadYpintar);
  qs('#almacenSelect').addEventListener('change', loadYpintar);
});

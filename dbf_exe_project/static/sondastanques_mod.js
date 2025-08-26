async function getJSON(url){
  const r = await fetch(url);
  if(!r.ok) throw new Error(await r.text());
  return await r.json();
}

function pct(value, capacity){
  if(!value || !capacity || capacity<=0) return 0;
  return Math.max(0, Math.min(100, (value/capacity)*100));
}

function clsFor(p){
  if(p >= 70) return "ok";
  if(p >= 40) return "warn";
  return "bad";
}

function fmt(n, decimals=1){
  if(n===null || n===undefined) return "–";
  return Number(n).toLocaleString('es-ES', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
}

async function loadAlmacenes(){
  try{
    const data = await getJSON('/api/almacenes');
    const sel = document.getElementById('almacenSelect');
    sel.innerHTML = '<option value="">Todos</option>';
    const items = data.almacenes || [];
    // detectar posibles campos ID y DESCRIPCIÓN flexibles
    const sample = items[0] || {};
    const keys = Object.keys(sample);
    function findKey(...cands){
      const lower = k => k.toLowerCase();
      for(const c of cands){
        const hit = keys.find(k => lower(k)===c.toLowerCase() || lower(k).includes(c.toLowerCase()));
        if(hit) return hit;
      }
      return null;
    }
    const fId = findKey('IDALMA','CODALMA','ALMACEN','ID_ALMA') || 'IDALMA';
    const fNm = findKey('NOMBRE','DESCRIPCION','DESCR','NOMALMA') || fId;
    for(const a of items){
      const id = a[fId];
      const nm = a[fNm] ?? id;
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `${id} – ${nm}`;
      sel.appendChild(opt);
    }
  }catch(e){
    console.error(e);
  }
}

async function loadTanques(){
  const grid = document.getElementById('tanquesGrid');
  grid.innerHTML = '<div class="badge">Cargando…</div>';
  const almacen = document.getElementById('almacenSelect').value;
  const qs = almacen ? `?almacen=${encodeURIComponent(almacen)}` : '';
  const data = await getJSON('/api/tanques_norm'+qs);
  grid.innerHTML = '';
  (data.tanques||[]).forEach(t => {
    const v = t.volumen, l15 = t.litros15, temp = t.temperatura;
    const cap = t.capacidad || Math.max(v||0, l15||0, 1); // fallback visual
    const p = pct(v, cap);
    const div = document.createElement('div');
    div.className = 'card';
    div.innerHTML = `
      <h3>${t.almacen_id ?? '–'} · Tanque ${t.tanque_id ?? '–'}</h3>
      <div class="meta">
        <span class="badge">${t.producto_desc ?? (t.producto_id ?? '–')}</span>
        ${t.almacen_desc ? `<span class="badge">${t.almacen_desc}</span>` : ''}
      </div>
      <div class="bar"><div class="fill ${clsFor(p)}" style="width:${p.toFixed(1)}%"></div></div>
      <div class="kpis">
        <div class="kpi"><div class="label">Volumen</div><div class="value">${fmt(v)} L</div></div>
        <div class="kpi"><div class="label">A 15ºC</div><div class="value">${fmt(l15)} L</div></div>
        <div class="kpi"><div class="label">Temp</div><div class="value">${fmt(temp,1)} ºC</div></div>
      </div>
    `;
    div.addEventListener('click', () => showDetalle(t));
    grid.appendChild(div);
  });
  if((data.tanques||[]).length===0){
    grid.innerHTML = '<div class="badge">Sin tanques con lecturas válidas.</div>';
  }
}

function showDetalle(t){
  const el = document.getElementById('detalleBody');
  el.innerHTML = `
    <div class="meta" style="margin:0 0 8px 0">
      <span class="badge">Almacén: ${t.almacen_id}</span>
      <span class="badge">Tanque: ${t.tanque_id}</span>
      ${t.producto_desc ? `<span class="badge">${t.producto_desc}</span>`:''}
    </div>
    <ul>
      <li><strong>Volumen actual:</strong> ${fmt(t.volumen)} L</li>
      <li><strong>Volumen a 15ºC:</strong> ${fmt(t.litros15)} L</li>
      <li><strong>Temperatura:</strong> ${fmt(t.temperatura)} ºC</li>
      ${t.capacidad ? `<li><strong>Capacidad:</strong> ${fmt(t.capacidad)} L</li>`:''}
    </ul>
    <p style="color:var(--muted);font-size:12px">Nota: se muestran solo tanques con lecturas (FFCALA) válidas recientes (hasta 5 últimas, tomando la última no nula).</p>
  `;
}

document.getElementById('refreshBtn').addEventListener('click', loadTanques);
document.getElementById('almacenSelect').addEventListener('change', loadTanques);

(async function init(){
  await loadAlmacenes();
  await loadTanques();
})();
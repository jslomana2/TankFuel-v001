
async function fetchJSON(url){
  const r = await fetch(url, {cache:'no-store'});
  return await r.json();
}

function statusClassAndText(st){
  const key = st.key; // low/mid/high/full
  const label = st.label;
  const color = st.color;
  const shape = st.shape; // 'warning' or 'circle'
  let cls = key;
  let html = '';
  if(shape === 'warning'){
    html = `⚠ ${label}`;
  }else{
    html = `<i class="dot" style="background:${color}"></i> ${label}`;
  }
  return {cls, html, color};
}

function cardHTML(row){
  const st = statusClassAndText(row.status);
  const pct = row.porcentaje || 0;
  const fillStyle = `width:${pct}%;`;
  return `
    <article class="card" data-tanque="${row.tanque_id}">
      <div class="row">
        <div class="name">Tanque ${row.tanque_id}</div>
        <div class="badge ${st.cls}" title="${pct}%">${st.html}</div>
      </div>
      <div class="tankbar" data-color="${st.cls}"><div class="fill" style="${fillStyle}"></div></div>
      <div class="meta">
        ${row.almacen} · ${row.almacen_descr} — ${row.articulo} · ${row.articulo_descr} · ${pct}% (${row.cantidad}/${row.capacidad})
      </div>
    </article>
  `;
}

async function loadAlmacenes(){
  const sel = document.getElementById('selAlmacen');
  sel.innerHTML = '';
  const data = await fetchJSON('/api/almacenes');
  const opt0 = document.createElement('option');
  opt0.value = '';
  opt0.textContent = '— Selecciona almacén —';
  sel.appendChild(opt0);
  for(const a of data){
    const o = document.createElement('option');
    o.value = a.almacen;
    o.textContent = `${a.almacen} — ${a.descr}`;
    sel.appendChild(o);
  }
}

async function loadCards(almacen=''){
  const url = almacen ? `/api/tanques_norm?almacen=${encodeURIComponent(almacen)}` : '/api/tanques_norm';
  const data = await fetchJSON(url);
  const cont = document.getElementById('cards');
  cont.innerHTML = data.map(cardHTML).join('');
  // bind click -> historico
  for(const el of cont.querySelectorAll('.card')){
    el.addEventListener('click', () => {
      const tanque = el.getAttribute('data-tanque');
      loadHistorico(tanque);
    });
  }
}

async function loadHistorico(tanque){
  const hist = document.getElementById('hist');
  hist.innerHTML = 'Cargando...';
  const data = await fetchJSON(`/api/calibraciones/ultimas?tanque_id=${encodeURIComponent(tanque)}&n=30`);
  if(!data.length){
    hist.innerHTML = 'Sin datos';
    return;
  }
  let html = `<div><strong>Tanque ${tanque}</strong></div><ol>`;
  for(const r of data){
    html += `<li>${r.fecha} ${r.hora} — ${r.volumen}</li>`;
  }
  html += `</ol>`;
  hist.innerHTML = html;
}

async function init(){
  await loadAlmacenes();
  await loadCards();
  document.getElementById('btnRefrescar').addEventListener('click', () => {
    const sel = document.getElementById('selAlmacen');
    loadCards(sel.value || '');
  });
  document.getElementById('btnVerTodos').addEventListener('click', () => {
    const sel = document.getElementById('selAlmacen');
    sel.value = '';
    loadCards('');
  });
  document.getElementById('selAlmacen').addEventListener('change', (e) => {
    loadCards(e.target.value || '');
  });
}
document.addEventListener('DOMContentLoaded', init);

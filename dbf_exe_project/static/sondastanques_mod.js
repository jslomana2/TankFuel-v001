async function loadTanks(){
  let resp = await fetch('/api/tanques_norm');
  let data = await resp.json();
  if(!data.rows || data.rows.length===0){
    document.getElementById('noData').hidden=false;
    return;
  }
  document.getElementById('noData').hidden=true;
  renderTanks(data.rows);
}

function renderTanks(rows){
  let grid=document.getElementById('grid'); grid.innerHTML='';
  rows.forEach(t=>{
    let div=document.createElement('div');
    div.className='tank';
    div.innerHTML=`<h3>${t.descripcion||('Tanque '+t.tanque_id)}</h3>
      <p>Almacén: ${t.almacen_id}</p>
      <p>Capacidad: ${t.capacidad_l}</p>
      <p>Stock: ${t.stock_l}</p>
      <p>Producto: ${t.producto_nombre||t.producto_id}</p>
      <p>Temp: ${t.temp_ultima_c}</p>`;
    div.addEventListener('click', ()=>loadHist(t.tanque_id, t.descripcion));
    grid.appendChild(div);
  });
}

async function loadHist(tid, name){
  let resp=await fetch(`/api/calibraciones/ultimas?tanque_id=${tid}&n=10`);
  let data=await resp.json();
  let panel=document.getElementById('histPanel');
  panel.hidden=false;
  document.getElementById('histTitle').textContent='Histórico '+(name||tid);
  let tbody=document.querySelector('#histTable tbody');
  tbody.innerHTML='';
  if(!data.rows || data.rows.length===0){
    let tr=document.createElement('tr');
    tr.innerHTML='<td colspan=4>Sin lecturas disponibles</td>';
    tbody.appendChild(tr);
    return;
  }
  data.rows.forEach(r=>{
    let tr=document.createElement('tr');
    tr.innerHTML=`<td>${r.fecha||''} ${r.hora||''}</td>
      <td>${r.litros||''}</td>
      <td>${r.litros15||''}</td>
      <td>${r.tempera||''}</td>`;
    tbody.appendChild(tr);
  });
}

window.addEventListener('DOMContentLoaded', loadTanks);

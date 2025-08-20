async function loadTanks(){
  try{
    let resp = await fetch('/api/tanques_norm');
    let data = await resp.json();
    if(!data.rows || data.rows.length===0){
      document.getElementById('grid').innerHTML='<p>No hay tanques disponibles</p>';
      return;
    }
    renderTanks(data.rows);
  }catch(e){
    console.error('Error cargando tanques', e);
  }
}

function renderTanks(rows){
  let grid=document.getElementById('grid'); grid.innerHTML='';
  rows.forEach(t=>{
    let div=document.createElement('div');
    div.className='tank';
    div.innerHTML=`<h3>${t.descripcion||('Tanque '+t.tanque_id)}</h3>
      <p><b>Almacén:</b> ${t.almacen_id}</p>
      <p><b>Capacidad:</b> ${t.capacidad_l}</p>
      <p><b>Stock:</b> ${t.stock_l}</p>
      <p><b>Producto:</b> ${t.producto_nombre||t.producto_id}</p>
      <p><b>Temp:</b> ${t.temp_ultima_c}</p>`;
    div.addEventListener('click', ()=>loadHist(t.tanque_id, t.descripcion));
    grid.appendChild(div);
  });
}

async function loadHist(tid, name){
  try{
    let resp=await fetch(`/api/calibraciones/ultimas?tanque_id=${tid}&n=10`);
    let data=await resp.json();
    let panel=document.getElementById('histPanel');
    panel.hidden=false;
    document.getElementById('histTitle').textContent='Histórico '+(name||tid);
    let tbody=document.querySelector('#histTable tbody');
    tbody.innerHTML='';
    if(!data.rows || data.rows.length===0){
      tbody.innerHTML='<tr><td colspan=4>Sin lecturas</td></tr>';
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
  }catch(e){
    console.error('Error cargando histórico', e);
  }
}

document.addEventListener('DOMContentLoaded', ()=>{
  loadTanks();
  document.getElementById('refreshBtn').addEventListener('click', loadTanks);
});

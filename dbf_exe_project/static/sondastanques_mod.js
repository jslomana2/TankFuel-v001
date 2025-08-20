async function loadData(){
  try{
    let resp = await fetch('/api/tanques_norm');
    if(!resp.ok){ throw new Error('Error HTTP '+resp.status); }
    let data = await resp.json();
    if(!data.rows || data.rows.length===0){
      document.getElementById('noData').hidden = false;
      return;
    }
    document.getElementById('noData').hidden = true;
    renderTanks(data.rows);
  }catch(err){
    console.error('Fallo al cargar tanques', err);
    document.getElementById('noData').hidden = false;
  }
}

function renderTanks(rows){
  let grid = document.getElementById('grid');
  grid.innerHTML = '';
  rows.forEach(t=>{
    let div = document.createElement('div');
    div.className = 'tank';
    div.innerHTML = `
      <h3>${t.descripcion||'Tanque '+t.tanque_id}</h3>
      <p>Almacén: ${t.almacen_id}</p>
      <p>Capacidad: ${t.capacidad_l||'?'}</p>
      <p>Stock: ${t.stock_l||'?'}</p>
      <p>Producto: ${t.producto_nombre||t.producto_id||'?'}</p>
      <p>Temp: ${t.temp_ultima_c||'?'}</p>
    `;
    grid.appendChild(div);
  });
}

window.addEventListener('DOMContentLoaded', loadData);

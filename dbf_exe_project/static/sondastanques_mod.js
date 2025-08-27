async function getJSON(u){const r=await fetch(u);if(!r.ok) throw new Error(await r.text());return r.json();}
document.addEventListener('DOMContentLoaded', async()=>{
  const d=await getJSON('/api/almacenes'); const sel=document.getElementById('almacenSelect');
  sel.innerHTML=''; (d.almacenes||[]).forEach(a=>{const o=document.createElement('option');o.value=a.codigo;o.textContent=`${a.codigo} – ${a.nombre}`;sel.appendChild(o);});
});
(function(){
  var almacenes = []; var idxActivo = 0; var historyByTank = {};
  var selectedTank = null; var filteredRows = [];
  
  // FUNCIÓN AUXILIAR PARA CONVERTIR HEX A RGB
  function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
      r: parseInt(result[1], 16),
      g: parseInt(result[2], 16),
      b: parseInt(result[3], 16)
    } : null;
  }
  
  // AUTOREFRESCO INTELIGENTE
  var autoRefresh = {
    enabled: true,
    interval: 60000,
    timer: null,
    lastCheck: 0,
    checking: false,
    
    start: function() {
      if(this.timer) clearInterval(this.timer);
      this.timer = setInterval(() => this.checkForUpdates(), this.interval);
      console.log('Autorefresco activado cada', this.interval/1000, 'segundos');
    },
    
    stop: function() {
      if(this.timer) {
        clearInterval(this.timer);
        this.timer = null;
      }
      console.log('Autorefresco desactivado');
    },
    
    async checkForUpdates() {
      if(this.checking) return;
      this.checking = true;
      
      try {
        console.log('Verificando cambios...');
        const response = await fetch('/api/status');
        const data = await response.json();
        
        if(data.ok && data.changes_detected) {
          console.log('Cambios detectados, recargando datos...');
          this.showRefreshIndicator();
          await window.__sondasUI.refreshData();
          this.hideRefreshIndicator();
        } else {
          console.log('Sin cambios detectados');
        }
      } catch(e) {
        console.error('Error verificando actualizaciones:', e);
      }
      
      this.checking = false;
      this.lastCheck = Date.now();
    },
    
    showRefreshIndicator() {
      const btn = document.getElementById('refreshBtn');
      if(btn) {
        btn.style.backgroundColor = '#f59e0b';
        btn.textContent = 'Actualizando...';
        btn.disabled = true;
      }
    },
    
    hideRefreshIndicator() {
      const btn = document.getElementById('refreshBtn');
      if(btn) {
        btn.style.backgroundColor = '';
        btn.textContent = 'Refrescar';
        btn.disabled = false;
      }
    }
  };

  function toHex(n){ return ("0"+n.toString(16)).slice(-2); }
  
// ---- Ultra-rápido: capa de diff y refresco ----
var __STATE = { lastKey:null, cardsByKey:new Map(), sectionByAlm:new Map(), pendingFrame:0, lastRenderAt:0, refreshing:false };
function hashKey(obj){ try{ var s=JSON.stringify(obj,function(k,v){ if(v&&typeof v==='object'){ if('spark'in v){ var c=Object.assign({},v); delete c.spark; return c; } } return v;}); var h=5381; for(var i=0;i<s.length;i++) h=((h<<5)+h)+s.charCodeAt(i); return (h>>>0).toString(16);}catch(_){return String(Math.random());} }
function keyForTank(a,t){ return (a.id!=null?a.id:a.nombre||'A') + '|' + (t.id_tanque||t.codigo||t.nombre||Math.random()); }

// FUNCIÓN upsertCard OPTIMIZADA PARA VELOCIDAD
function upsertCard(a,t,grid){
  try {
    var key=keyForTank(a,t); 
    var ref=__STATE.cardsByKey.get(key);
    var col=colorFrom(t.color||t.colorProducto||t.colorRGB); 
    
    // CORREGIDO: Solo usar colores por defecto si realmente no hay color válido
    if(!col || col === "#1987ff" || col === "#CCCCCC" || col === "undefined" || col === "null") {
      col = "#2563eb";
    } else {
      // Verificar que el color no sea muy claro/gris
      var rgb = hexToRgb(col);
      if(rgb && (rgb.r > 220 && rgb.g > 220 && rgb.b > 220)) {
        col = "#2563eb";
      }
    }
    
    var pct=(t.capacidad>0)? percent((t.volumen/t.capacidad)*100):0;
    var nivel = nivelFromPct(pct); 
    var colorNivel = nivelColorFromPct(pct);
    
    if(!ref){
      var card=document.createElement("div"); 
      card.className="card";
      
      var tankWrap=document.createElement("div"); 
      tankWrap.className="tankWrap";
      
      var tank=document.createElement("div"); 
      tank.className="tank";
      
      var liquid=document.createElement("div"); 
      liquid.className="liquid";
      
      // ELIMINADO: Ondas complejas que causan lentitud
      // Solo efectos básicos
      
      var gloss=document.createElement("div"); 
      gloss.className="gloss"; 
      tank.appendChild(gloss);
      
      tank.appendChild(liquid); 
      makeScaleSimple(tankWrap);
      tankWrap.appendChild(tank);
      
      var pctLabel=document.createElement("div"); pctLabel.className="pct"; 
      tankWrap.appendChild(pctLabel);
      
      var info=document.createElement("div");
      
      var r1=document.createElement("div"); 
      r1.style.cssText="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px";
      
      var nm=document.createElement("div"); 
      nm.className="name";
      
      var st=document.createElement("div"); 
      st.className="status"; 
      var dt=document.createElement("span"); 
      dt.className="dot"; 
      var stx=document.createElement("span"); 
      st.appendChild(dt); 
      st.appendChild(stx);
      
      r1.appendChild(nm); 
      r1.appendChild(st); 
      info.appendChild(r1);
      
      var c=document.createElement("canvas"); 
      c.className="spark"; 
      info.appendChild(c);
      
      var kv=document.createElement("div"); 
      kv.className="kv"; 
      info.appendChild(kv);
      
      card.appendChild(tankWrap); 
      card.appendChild(info);
      
      // OPTIMIZADO: Efectos hover simples y rápidos
      card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-2px)';
      });
      
      card.addEventListener('mouseleave', function() {
        this.style.transform = '';
      });
      
      // OPTIMIZADO: Click handler más rápido
      card.onclick=function(){ 
        var cards=document.querySelectorAll(".card"); 
        for(var i=0;i<cards.length;i++) cards[i].classList.remove("sel"); 
        card.classList.add("sel");
        renderHistory(t); 
      };
      
      ref={
        el:card, 
        parts:{liquid,pctLabel,nm,dt,stx,kv,spark:c}, 
        last:{pct:-1,volumen:-1,capacidad:-1,nombre:null,nivel:null,color:null,fecha:null}
      };
      
      __STATE.cardsByKey.set(key, ref);
    }
    
    var p=ref.parts;
    
    // OPTIMIZADO: Aplicar color de forma eficiente
    if(ref.last.color !== col) {
      p.liquid.style.background = col;
      p.liquid.style.opacity = "0.9";
      ref.last.color=col;
    }
    
    // Actualizar porcentaje
    if(ref.last.pct!==pct){ 
      p.liquid.style.height = pct + "%";
      p.pctLabel.textContent=pct.toFixed(0)+" %"; 
      ref.last.pct=pct; 
    }
    
    var nombre=(t.nombre||"TANQUE"); 
    if(ref.last.nombre!==nombre){ 
      p.nm.textContent=nombre; 
      p.nm.style.color = "#e7eef6";
      ref.last.nombre=nombre; 
    }
    
    // Estado simplificado
    if(ref.last.nivel!==nivel){ 
      if(pct <= 20){ 
        p.dt.textContent="⚠"; 
        p.dt.style.color="#ef4444"; 
        p.dt.style.background="transparent";
      } else { 
        p.dt.textContent="●"; 
        p.dt.style.color=colorNivel;
        p.dt.style.background="transparent";
      }
      p.stx.textContent=nivel;
      ref.last.nivel=nivel; 
    }
    
    // Actualizar información
    if(ref.last.volumen!==(t.volumen||0) || ref.last.capacidad!==(t.capacidad||0) || ref.last.fecha!==(t.fecha_ultimo_calado||'')){
      var ullage=(t.capacidad||0)-(t.volumen||0);
      var fechaDisplay = t.fecha_ultimo_calado || '-';
      
      p.kv.innerHTML=
        "<div>Volumen</div><div><strong>"+litersLabel(t.volumen||0)+"</strong></div>"+
        "<div>Capacidad</div><div>"+litersLabel(t.capacidad||0)+"</div>"+
        "<div>Disponible</div><div>"+litersLabel(ullage)+"</div>"+
        "<div>Producto</div><div>"+(t.articulo_nombre||t.producto||"-")+"</div>"+
        "<div>Temp.</div><div>"+(t.temperatura!=null?t.temperatura.toFixed(1)+' °C':'-')+"</div>"+
        "<div>Última lectura</div><div style='color:#4dd0ff;font-weight:700'>"+fechaDisplay+"</div>";
      
      ref.last.volumen=(t.volumen||0); 
      ref.last.capacidad=(t.capacidad||0); 
      ref.last.fecha=(t.fecha_ultimo_calado||'');
    }
    
    // OPTIMIZADO: Sparkline simple
    drawSparkSimple(p.spark, t.spark||[], col); 
    
    return ref.el;
    
  } catch(e) {
    console.error('Error en upsertCard:', e);
    return document.createElement("div");
  }
}

function diffRenderAlmacen(a, host){ var grid=host.querySelector(':scope > .grid'); if(!grid){ grid=document.createElement('div'); grid.className='grid'; host.appendChild(grid);} var frag=document.createDocumentFragment(); (a.tanques||[]).forEach(function(t){ frag.appendChild(upsertCard(a,t,grid)); }); }

function fastRenderAll(almacenes){ 
  try {
    console.log('fastRenderAll - Almacenes recibidos:', almacenes.length);
    
    var gridHost=document.getElementById("grid"); 
    if(!gridHost) {
      console.error('No se encontró elemento #grid');
      return;
    }
    
    gridHost.innerHTML=""; 
    gridHost.style.display = "block";
    __STATE.cardsByKey.clear(); 
    __STATE.sectionByAlm.clear(); 
    
    var totalTanques = 0;
    
    almacenes.forEach(function(a, index){ 
      console.log(`Procesando almacén ${index + 1}: ${a.nombre || a.id}`, a);
      
      if(!a.tanques || !a.tanques.length) {
        console.log(`Almacén ${a.nombre || a.id} sin tanques`);
        return;
      }
      
      var section=document.createElement('section'); 
      section.className='almacenSection'; 
      
      var h=document.createElement('h2'); 
      h.className='almacenTitle'; 
      h.textContent=(a.nombre || a.id || "Almacén"); 
      section.appendChild(h); 
      
      var tanksGrid=document.createElement('div'); 
      tanksGrid.className='tanks-grid'; 
      tanksGrid.style.cssText='display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:24px;padding:0';
      
      a.tanques.forEach(function(t, tIndex){ 
        try {
          console.log(`Renderizando tanque ${tIndex + 1}: ${t.nombre}`);
          var card = upsertCard(a, t, tanksGrid);
          tanksGrid.appendChild(card); 
          totalTanques++;
        } catch(e) {
          console.error(`Error renderizando tanque ${t.nombre}:`, e);
        }
      }); 
      
      section.appendChild(tanksGrid);
      gridHost.appendChild(section); 
      __STATE.sectionByAlm.set(a.id||a.nombre||Math.random(), section);
      
      console.log(`Almacén ${a.nombre || a.id} completado con ${a.tanques.length} tanques`);
    }); 
    
    console.log(`fastRenderAll completado - Total tanques: ${totalTanques}`);
    
  } catch(e) {
    console.error('Error en fastRenderAll:', e);
  }
}

function fastRenderSingle(a){ var gridHost=document.getElementById("grid"); gridHost.innerHTML=""; var section=document.createElement('section'); section.className='almacenSection'; var h=document.createElement('h2'); h.className='almacenTitle'; h.textContent=((a.id!=null?a.id:"") + " — " + (a.nombre||"Almacén")).trim(); section.appendChild(h); gridHost.appendChild(section); diffRenderAlmacen(a, section); }

// Estado por porcentaje
function nivelFromPct(p){ p = Math.max(0, Math.min(100, Math.round(p||0))); return (p>=91)?"Lleno":(p>=51)?"Alto":(p>=21)?"Medio":"Bajo"; }
function nivelColorFromPct(p){ p = Math.max(0, Math.min(100, Math.round(p||0))); return (p>=91)?"#4ade80":(p>=51)?"#16a34a":(p>=21)?"#f59e0b":"#ef4444"; }

// FUNCIÓN colorFrom CORREGIDA PARA RESPETAR COLORES DEL ARCHIVO
function colorFrom(v){ 
  if(typeof v==="string" && v && v !== "#CCCCCC" && v !== "#1987ff" && v !== "undefined" && v !== "null") {
    var rgb = hexToRgb(v);
    if(rgb && (rgb.r > 220 && rgb.g > 220 && rgb.b > 220)) {
      return "#2563eb";
    }
    return v; 
  }
  if(typeof v==="number"){ 
    var r=(v&255),g=(v>>8)&255,b=(v>>16)&255; 
    if(r > 220 && g > 220 && b > 220) {
      return "#2563eb";
    }
    return "#"+toHex(r)+toHex(g)+toHex(b);
  } 
  return "#2563eb";
}

function shade(hex, pct){ var m=/(?:#)?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(hex); if(!m) return hex; var r=parseInt(m[1],16),g=parseInt(m[2],16),b=parseInt(m[3],16); function adj(x){ return Math.max(0,Math.min(255,Math.round(x+pct*255))); } return "#"+toHex(adj(r))+toHex(adj(g))+toHex(adj(b)); }
function statusColor(s){ return s==="ok"?"var(--ok)":(s==="warn"?"var(--warn)":"var(--bad)"); }
function litersFmt(n){ return (Math.round(n||0)).toLocaleString(); }
function litersLabel(n){ return litersFmt(n)+" L"; }
function diffClass(d){ return d>0?"diffPos":(d<0?"diffNeg":"diffZero"); }
function percent(n){ return Math.max(0, Math.min(100, n)); }
function percentFmt(n){ return percent(n).toFixed(0)+" %"; }
function parseDateStr(s){ var p=s.split(' '); var d=p[0].split('-'); var t=(p[1]||'00:00').split(':'); return new Date(Number(d[0]),Number(d[1])-1,Number(d[2]),Number(t[0]||0),Number(t[1]||0)); }

// SPARKLINE SIMPLE Y RÁPIDO
function drawSparkSimple(canvas, points, stroke) {
  if (!canvas || !canvas.getContext || !points || !points.length) return;
  
  var ctx = canvas.getContext("2d");
  var w = canvas.clientWidth || 100;
  var h = canvas.clientHeight || 32;
  
  canvas.width = w;
  canvas.height = h;
  
  ctx.clearRect(0, 0, w, h);
  
  var min = Math.min.apply(null, points);
  var max = Math.max.apply(null, points);
  if(min === max) { min = min - 1; max = max + 1; }
  
  var pad = 4;
  
  // Línea simple
  ctx.beginPath();
  for (var i = 0; i < points.length; i++) {
    var x = pad + (w - 2 * pad) * (i / Math.max(1, points.length - 1));
    var y = h - pad - (h - 2 * pad) * ((points[i] - min) / (max - min));
    
    if (i === 0) {
      ctx.moveTo(x, y);
    } else {
      ctx.lineTo(x, y);
    }
  }
  
  ctx.lineWidth = 2;
  ctx.strokeStyle = stroke;
  ctx.stroke();
  
  // Puntos simples
  for (var i = 0; i < points.length; i++) {
    var x = pad + (w - 2 * pad) * (i / Math.max(1, points.length - 1));
    var y = h - pad - (h - 2 * pad) * ((points[i] - min) / (max - min));
    
    ctx.beginPath();
    ctx.arc(x, y, 1.5, 0, 2 * Math.PI);
    ctx.fillStyle = stroke;
    ctx.fill();
  }
}

function drawSpark(canvas, points, stroke){
  drawSparkSimple(canvas, points, stroke);
}

function drawLineChart(canvas, series, opts){
  if(!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext("2d");
  var dpr = Math.max(1, window.devicePixelRatio||1);
  var w = canvas.clientWidth || 600;
  var h = canvas.clientHeight || 260;
  canvas.width = w*dpr; canvas.height = h*dpr; ctx.scale(dpr,dpr);
  ctx.clearRect(0,0,w,h);
  var padL=42,padR=12,padT=14,padB=24;
  ctx.strokeStyle = "rgba(255,255,255,.25)"; ctx.lineWidth=1;
  ctx.beginPath(); ctx.moveTo(padL, padT); ctx.lineTo(padL, h-padB); ctx.lineTo(w-padR, h-padB); ctx.stroke();
  var allY = []; series.forEach(function(s){ s.data.forEach(function(v){ allY.push(v); }); });
  if(!allY.length) return;
  var yMin = Math.min.apply(null, allY), yMax = Math.max.apply(null, allY);
  if(yMin===yMax){ yMin = Math.max(0,yMin-1); yMax=yMax+1; }
  function yTo(v){ return h-padB - (h-padT-padB) * ((v-yMin)/(yMax-yMin)); }
  var L = series[0].data.length;
  function xTo(i){ return padL + (w-padL-padR) * (L<=1?0.5:i/(L-1)); }
  ctx.strokeStyle="rgba(255,255,255,.12)";
  ctx.beginPath();
  for(var g=0; g<=4; g++){ var yy=padT+(h-padT-padB)*g/4; ctx.moveTo(padL,yy); ctx.lineTo(w-padR,yy); }
  ctx.stroke();
  ctx.fillStyle="#a6b8c9"; ctx.font="11px system-ui,Arial";
  for(var gy=0; gy<=4; gy++){ var val = yMax - (yMax-yMin)*gy/4; var yy = padT+(h-padT-padB)*gy/4; ctx.fillText(Math.round(val).toLocaleString(), 4, yy+4); }
  ctx.textAlign="center";
  var labels = opts.labels||[];
  var step = Math.ceil(L/8);
  for(var i=0;i<L;i+=step){ ctx.fillText(labels[i]||"", xTo(i), h-6); }
  series.forEach(function(s,i){
    ctx.beginPath();
    for(var j=0;j<L;j++){ var x=xTo(j), y=yTo(s.data[j]); if(j===0) ctx.moveTo(x,y); else ctx.lineTo(x,y); }
    ctx.lineWidth=2; ctx.strokeStyle=s.color||"#9fd2ff"; ctx.stroke();
  });
}

function groupForChart(rows, mode){
  var lab=[], lit=[], lit15=[];
  if(mode==="days"){
    var map={};
    rows.forEach(function(r){
      var d = r.fecha.substr(0,10);
      if(!map[d]) map[d] = {l:0,l15:0,c:0};
      map[d].l += (r.litros||0);
      map[d].l15 += (r.litros_15||0);
      map[d].c += 1;
    });
    Object.keys(map).sort().forEach(function(d){
      lab.push(d); lit.push(map[d].l/map[d].c); lit15.push(map[d].l15/map[d].c);
    });
  }else{
    rows.forEach(function(r){ 
      var timeLabel = r.fecha + (r.hora ? " " + r.hora : "");
      lab.push(timeLabel); 
      lit.push(r.litros||0); 
      lit15.push(r.litros_15||0); 
    });
  }
  return {labels:lab, litros:lit, litros_15:lit15};
}

function groupByAlmacen(items){
  var map = {}; (items||[]).forEach(function(t){ var k=t.almacen||t.almacenNombre||"General"; if(!map[k]) map[k]={ id:k, nombre:k, tanques:[] }; map[k].tanques.push(t); });
  return Object.keys(map).sort().map(function(k){ return map[k]; });
}

function renderSelect(){
  var sel = document.getElementById("almacenSel"); sel.innerHTML="";
  almacenes.forEach(function(a,i){ var o=document.createElement("option"); o.value=a.id; o.textContent=a.nombre+" ("+(a.tanques?a.tanques.length:0)+")"; if(i===idxActivo) o.selected=true; sel.appendChild(o); });
}

// ESCALA SIMPLE
function makeScaleSimple(container){
  var scale = document.createElement("div"); 
  scale.className="scale";
  
  [100,75,50,25,0].forEach(function(p){ 
    var row=document.createElement("div"); 
    row.className="tick"; 
    
    var line=document.createElement("div"); 
    line.className="line"; 
    
    var lab=document.createElement("div"); 
    lab.textContent=p+"%";
    
    row.appendChild(line); 
    row.appendChild(lab); 
    scale.appendChild(row); 
  });
  
  container.appendChild(scale);
}

function makeScale(container){
  makeScaleSimple(container);
}

function renderHistory(tank){
  selectedTank = tank || null;
  var panel = document.getElementById("histPanel");
  if(!tank){ panel.hidden = true; return; }
  
  var today = new Date();
  var weekAgo = new Date();
  weekAgo.setDate(today.getDate() - 6);
  
  function fmtISO(d){ return d? (d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")) : ""; }
  
  var fd = document.getElementById("fromDate"); 
  var td = document.getElementById("toDate");
  if(fd) fd.value = fmtISO(weekAgo);
  if(td) td.value = fmtISO(today);
  
  document.getElementById("histTitle").textContent = "Histórico · " + (tank.nombre||"") + " ("+(tank.articulo_nombre||tank.producto||"-")+")";
  document.getElementById("histInfo").textContent = (tank.almacen || "Almacén") + " · Últimos 7 días";
  panel.hidden = false;
  applyFilterAndRender();
}

function applyFilterAndRender(){
  if(!selectedTank){ return; }
  var key = (selectedTank.almacen||"") + "|" + (selectedTank.nombre||"");
  var rows = (historyByTank[key]||[]).slice().sort(function(a,b){ return parseDateStr(a.fecha + " " + (a.hora||"00:00")) - parseDateStr(b.fecha + " " + (b.hora||"00:00")); });
  var fd = document.getElementById("fromDate").value;
  var td = document.getElementById("toDate").value;
  var df = fd? new Date(fd+"T00:00:00") : null;
  var dt = td? new Date(td+"T23:59:59") : null;
  filteredRows = rows.filter(function(r){ var d = parseDateStr(r.fecha + " 00:00"); return (!df || d>=df) && (!dt || d<=dt); });
  document.getElementById("rowsCount").textContent = filteredRows.length + " filas";

  var tb = document.querySelector("#histTable tbody"); tb.innerHTML = "";
  filteredRows.forEach(function(r){
    var dif = (r.litros||0) - (r.litros_15||0);
    var tr = document.createElement("tr");
    tr.innerHTML = "<td style='text-align:left'>"+r.fecha+"</td>"
                 + "<td style='text-align:left'>"+(r.hora||"--:--")+"</td>"
                 + "<td>"+litersFmt(r.litros||0)+"</td>"
                 + "<td>"+litersFmt(r.litros_15||0)+"</td>"
                 + "<td class='"+diffClass(dif)+"'>"+litersFmt(dif)+"</td>";
    tb.appendChild(tr);
  });

  var mode = document.getElementById("groupSel").value || "days";
  var grouped = groupForChart(filteredRows, mode);
  var col = colorFrom(selectedTank.color || selectedTank.colorProducto || selectedTank.colorRGB);
  drawLineChart(document.getElementById("histChart"),
    [{name:"Litros", data: grouped.litros, color: col},
     {name:"Litros a 15º", data: grouped.litros_15, color: "#9fd2ff"}],
    {labels: grouped.labels});
}

function exportCsv(filename, rows){
  var csv = "Fecha;Hora;Litros;Litros a 15º;Diferencia (L)\r\n";
  (rows||[]).forEach(function(r){ 
    var d=(r.litros||0)-(r.litros_15||0); 
    csv += [r.fecha, r.hora||"", r.litros||0, r.litros_15||0, d].join(";") + "\r\n"; 
  });
  var blob = new Blob([csv], {type:"text/csv;charset=utf-8;"});
  if(window.navigator.msSaveOrOpenBlob){ window.navigator.msSaveOrOpenBlob(blob, filename); }
  else{ var a=document.createElement("a"); var url=URL.createObjectURL(blob); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); setTimeout(function(){ URL.revokeObjectURL(url); a.remove(); }, 0); }
}

function exportPdf(){
  var win = window.open("", "_blank", "noopener");
  if(!win){ alert("No se pudo abrir la ventana de impresión."); return; }
  var chart = document.getElementById("histChart");
  var img = chart.toDataURL("image/png");
  var tank = selectedTank||{};
  var fd = document.getElementById("fromDate").value || "";
  var td = document.getElementById("toDate").value || "";
  var title = "Histórico - " + (tank.nombre||"") + " ("+(tank.articulo_nombre||tank.producto||"-")+")";
  var css = "body{font:12px Arial;margin:16px;color:#111}h1{font-size:18px;margin:0 0 8px}h2{font-size:14px;margin:10px 0 6px}table{border-collapse:collapse;width:100%;font-size:11px}th,td{border:1px solid #ddd;padding:6px 8px;text-align:right}th:first-child,th:nth-child(2),td:first-child,td:nth-child(2){text-align:left}img{max-width:100%} .meta{margin-bottom:8px;color:#333}";
  var html = "<!doctype html><html><head><meta charset='utf-8'><title>"+title+"</title></head><body>";
  html += "<h1>"+title+"</h1>";
  html += "<div class='meta'>Almacén: <b>"+(tank.almacen||"")+"</b> · Rango: <b>"+(fd||"-")+"</b> a <b>"+(td||"-")+"</b></div>";
  html += "<h2>Evolución (Litros vs Litros a 15º)</h2><img src='"+img+"'/>";
  html += "<h2>Tabla de lecturas</h2><table><thead><tr><th>Fecha</th><th>Hora</th><th>Litros</th><th>Litros a 15º</th><th>Dif. (L)</th></tr></thead><tbody>";
  (filteredRows||[]).forEach(function(r){ 
    var d=(r.litros||0)-(r.litros_15||0); 
    html += "<tr><td>"+r.fecha+"</td><td>"+(r.hora||"--:--")+"</td><td>"+(r.litros||0)+"</td><td>"+(r.litros_15||0)+"</td><td>"+d+"</td></tr>"; 
  });
  html += "</tbody></table></body></html>";
  win.document.open(); win.document.write(html); win.document.close();
  win.focus(); win.print();
}

function renderTotals(a){
  var host = document.getElementById("totales"); host.innerHTML = "";
  if(!a || !a.tanques || !a.tanques.length) return;
  var map = {};
  a.tanques.forEach(function(t){
    var key = t.articulo_nombre || t.producto || "—";
    if(!map[key]) map[key] = {vol:0, cap:0, count:0, color: (t.color||t.colorProducto||t.colorRGB)||"#2563eb"};
    map[key].vol += (t.volumen||0);
    map[key].cap += (t.capacidad||0);
    map[key].count += 1;
    if(!map[key].color && (t.color||t.colorProducto||t.colorRGB)) map[key].color = (t.color||t.colorProducto||t.colorRGB);
  });
  Object.keys(map).forEach(function(prod){
    var it = map[prod]; var pct = it.cap? Math.round(it.vol/it.cap*100) : 0;
    var div = document.createElement("div"); div.className="tchip";
    var sw = document.createElement("span"); sw.className="sw"; sw.style.background = colorFrom(it.color);
    div.appendChild(sw);
    var txt = document.createElement("span"); txt.innerHTML = "<strong>"+prod+"</strong> · "+litersFmt(it.vol)+" L ("+pct+"%) · "+it.count+" tqs";
    div.appendChild(txt);
    host.appendChild(div);
  });
}

function render(){
  try {
    var gridHost = document.getElementById("grid");
    
    if(!almacenes.length){ 
      if(gridHost) gridHost.innerHTML = ""; 
      renderTotals(null); 
      document.getElementById("histPanel").hidden=true; 
      return; 
    }
    
    if(window.__showAllMode){ 
      console.log('Modo "Ver todos" activo - Almacenes:', almacenes.length);
      
      if(gridHost) {
        gridHost.className = "show-all-mode";
      }
      
      fastRenderAll(almacenes); 
      document.getElementById("footerInfo").textContent = "Almacenes: "+almacenes.length+" • Modo: Todos";
      
      var globalTotals = {tanques: []};
      almacenes.forEach(function(alm){ 
        if(alm.tanques) {
          alm.tanques.forEach(function(t){ globalTotals.tanques.push(t); }); 
        }
      });
      renderTotals(globalTotals);
      return; 
    }
    
    if(gridHost) {
      gridHost.className = "";
      gridHost.innerHTML = "";
    }
    
    var a = almacenes[idxActivo]; 
    if(!a) {
      console.error('No hay almacén activo válido:', idxActivo);
      return;
    }
    
    renderSelect();
    
    var currentKey = hashKey(a);
    if(currentKey === __STATE.lastKey && !window.__forceRender){ return; }
    __STATE.lastKey = currentKey;
    
    var total=0, cap=0, alarms=0;
    
    (a.tanques||[]).forEach(function(t){
      total += t.volumen||0; 
      cap += t.capacidad||0; 
      if(t.status==="bad") alarms++;

      var card = upsertCard(a, t, gridHost);
      gridHost.appendChild(card);
    });

    renderTotals(a);
    
    var s = document.getElementById("summary");
    var pctTot = cap ? (total/cap*100) : 0;
    s.textContent = (a.nombre||"Almacén")+": "+percentFmt(pctTot)+" ("+litersLabel(total)+" de "+litersLabel(cap)+") • Alarmas: "+alarms;
    document.getElementById("footerInfo").textContent = "Almacenes: "+almacenes.length+" • Activo: "+(idxActivo+1)+"/"+almacenes.length;
    
    window.__forceRender = false;
    
  } catch(e) {
    console.error('Error en render():', e);
  }
}

window.setData = function(input){
  try{
    console.log('setData llamado con:', input);
    if(typeof input === "string") input = JSON.parse(input);
    if(Array.isArray(input)){ almacenes = groupByAlmacen(input);
    }else if(input && Array.isArray(input.almacenes)){
      almacenes = input.almacenes; if(input.activoId){ var i = almacenes.findIndex(function(a){ return a.id==input.activoId; }); if(i>=0) idxActivo = i; }
    }else{ almacenes = []; }
    idxActivo = Math.min(Math.max(0, idxActivo), Math.max(0, almacenes.length-1));
    console.log('Almacenes procesados:', almacenes.length, 'Activo:', idxActivo);
    render(); window.__vfp_integration__ = true;
  }catch(e){ console.error("setData error:", e); }
};
window.setWarehouse = function(idOrName){ var i = almacenes.findIndex(function(a){ return a.id==idOrName || a.nombre==idOrName; }); if(i>=0){ idxActivo=i; render(); } };
window.nextWarehouse = function(){ if(almacenes.length){ idxActivo=(idxActivo+1)%almacenes.length; render(); } };
window.prevWarehouse = function(){ if(almacenes.length){ idxActivo=(idxActivo-1+almacenes.length)%almacenes.length; render(); } };
window.setHistoryData = function(map){ historyByTank = map || {}; };

document.getElementById("almacenSel").addEventListener("change", function(e){ window.setWarehouse(e.target.value); });
document.getElementById("prevBtn").addEventListener("click", function(){ window.prevWarehouse(); });
document.getElementById("nextBtn").addEventListener("click", function(){ window.nextWarehouse(); });
document.getElementById("refreshBtn").addEventListener("click", function(){ 
  autoRefresh.showRefreshIndicator();
  if(typeof window.vfpRefresh==='function') window.vfpRefresh(); 
  else if(window.__sondasUI && window.__sondasUI.refreshData) {
    window.__sondasUI.refreshData().then(() => autoRefresh.hideRefreshIndicator());
  } else {
    location.reload(); 
  }
});
document.getElementById("groupSel").addEventListener("change", applyFilterAndRender);
document.getElementById("applyFilter").addEventListener("click", applyFilterAndRender);
document.getElementById("quick7").addEventListener("click", function(){
  var td = document.getElementById("toDate"); var fd = document.getElementById("fromDate");
  var end = new Date(); var start = new Date(); start.setDate(end.getDate()-6);
  function fmt(d){ return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0"); }
  td.value = fmt(end); fd.value = fmt(start); applyFilterAndRender();
});
document.getElementById("quick30").addEventListener("click", function(){
  var td = new Date(); var fd = new Date(); fd.setDate(td.getDate()-29);
  function fmt(d){ return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0"); }
  document.getElementById("toDate").value = fmt(td); document.getElementById("fromDate").value = fmt(fd); applyFilterAndRender();
});
document.getElementById("exportBtn").addEventListener("click", function(){ if(!selectedTank) return; exportCsv("historico_"+(selectedTank.nombre||"tanque")+".csv", filteredRows); });
document.getElementById("pdfBtn").addEventListener("click", function(){ if(!selectedTank) return; exportPdf(); });
window.addEventListener("resize", function(){ applyFilterAndRender(); });

// Inicializar autorefresco al cargar
window.addEventListener('load', function() {
  setTimeout(() => {
    autoRefresh.start();
    console.log('Sistema de autorefresco iniciado');
  }, 5000);
});

// DATOS DEMO
var amarillo="#fbbf24", azul="#3b82f6", rojo="#ef4444", hvo="#10b981";
function t(n,prod,col,cap,vol,alm){ return { almacen:alm, nombre:n, articulo_nombre:prod, producto:prod, color:col, capacidad:cap, volumen:vol, status:"ok", temperatura:24.0, spark:[50,52,51,53,54,55,56,58,59,57], fecha_ultimo_calado:"31/08/2025 14:30" }; }

var demo = {
  almacenes:[
    { id:"ALM1", nombre:"ALMACEN 1", tanques:[
      t("T1","Gasóleo A",amarillo,50000,41000,"ALMACEN 1"),
      t("T2","Gasóleo A",amarillo,50000,38000,"ALMACEN 1"),
      t("T3","Gasóleo C",azul,   50000,12000,"ALMACEN 1"),
      t("T4","Gasóleo B",rojo,   30000,17000,"ALMACEN 1"),
      t("T5","Gasóleo B",rojo,   30000,29000,"ALMACEN 1")
    ]},
    { id:"ALM2", nombre:"ALMACEN 2", tanques:[
      t("T1","Gasóleo A",amarillo,50000,34000,"ALMACEN 2"),
      t("T2","HVO",       hvo,     50000,22000,"ALMACEN 2")
    ]},
    { id:"ALM3", nombre:"ALMACEN 3", tanques:[
      t("T1","Gasóleo B",rojo,40000,30000,"ALMACEN 3"),
      t("T2","Gasóleo B",rojo,40000,26000,"ALMACEN 3"),
      t("T3","Gasóleo B",rojo,40000,19000,"ALMACEN 3")
    ]}
  ],
  activoId:"ALM1"
};

var hist = {
  "ALMACEN 1|T1":[
    {fecha:"2025-07-28", hora:"08:00", litros:40100, litros_15:40020},
    {fecha:"2025-07-29", hora:"08:00", litros:40150, litros_15:40100},
    {fecha:"2025-07-30", hora:"08:00", litros:40200, litros_15:40120},
    {fecha:"2025-07-31", hora:"08:00", litros:40450, litros_15:40380},
    {fecha:"2025-08-01", hora:"08:00", litros:40500, litros_15:40300},
    {fecha:"2025-08-01", hora:"14:30", litros:40480, litros_15:40290},
    {fecha:"2025-08-02", hora:"08:00", litros:40800, litros_15:40600},
    {fecha:"2025-08-02", hora:"16:15", litros:40750, litros_15:40580},
    {fecha:"2025-08-03", hora:"08:00", litros:41000, litros_15:40950},
    {fecha:"2025-08-03", hora:"14:00", litros:40500, litros_15:40400},
    {fecha:"2025-08-03", hora:"20:00", litros:39800, litros_15:39600},
    {fecha:"2025-08-04", hora:"08:00", litros:39200, litros_15:39000}
  ]
};

if(!window.__vfp_integration__) { window.setData(demo); window.setHistoryData(hist); }
})();

// CONTROL PARA MOSTRAR TODOS LOS ALMACENES
(function(){
  var cb, lastRaw = null, setDataOrig = null, allAlmacenes = [];
  function qs(id){ return document.getElementById(id); }
  function setControlsEnabled(flag){
    var sel = qs("almacenSel"), prev = qs("prevBtn"), next = qs("nextBtn");
    if(sel) sel.disabled = !flag;
    if(prev) prev.disabled = !flag;
    if(next) next.disabled = !flag;
  }
  
  function applyMode(){
    if(!setDataOrig) return;
    var all = !!(cb && cb.checked);
    window.__showAllMode = all;
    window.__forceRender = true;
    
    if(all && allAlmacenes.length > 0){
      setControlsEnabled(false);
      setDataOrig({ almacenes: allAlmacenes, activoId: null });
    }else if(!all && lastRaw){
      setControlsEnabled(true);
      if(lastRaw && lastRaw.almacenes && lastRaw.almacenes.length > 0) {
        idxActivo = 0;
        setDataOrig({ almacenes: lastRaw.almacenes, activoId: lastRaw.almacenes[0].id });
      } else {
        setDataOrig(lastRaw);
      }
    }
  }
  
  function hookSetDataSoon(){
    var tries = 0;
    var iv = setInterval(function(){
      tries++;
      if(typeof window.setData === "function"){
        if(!setDataOrig){
          setDataOrig = window.setData;
          window.setData = function(input){
            lastRaw = input;
            if(input && input.almacenes){
              allAlmacenes = input.almacenes.slice();
            }
            applyMode();
          };
        }
        clearInterval(iv);
      }else if(tries>50){
        clearInterval(iv);
      }
    }, 100);
  }
  
  function init(){
    cb = qs("allToggle");
    window.__showAllMode = false;
    hookSetDataSoon();
    if(cb){
      cb.checked = false;
      cb.addEventListener("change", applyMode);
    }
  }
  
  if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", init);
  }else{
    init();
  }
})();

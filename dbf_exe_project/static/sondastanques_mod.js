(function(){
  var almacenes = []; var idxActivo = 0; var historyByTank = {};
  var selectedTank = null; var filteredRows = [];

  function toHex(n){ return ("0"+n.toString(16)).slice(-2); }
  
// ---- Ultra-rápido: capa de diff y refresco ----
var __STATE = { lastKey:null, cardsByKey:new Map(), sectionByAlm:new Map(), pendingFrame:0, lastRenderAt:0, refreshing:false };
function hashKey(obj){ try{ var s=JSON.stringify(obj,function(k,v){ if(v&&typeof v==='object'){ if('spark'in v){ var c=Object.assign({},v); delete c.spark; return c; } } return v;}); var h=5381; for(var i=0;i<s.length;i++) h=((h<<5)+h)+s.charCodeAt(i); return (h>>>0).toString(16);}catch(_){return String(Math.random());} }
function keyForTank(a,t){ return (a.id!=null?a.id:a.nombre||'A') + '|' + (t.id_tanque||t.codigo||t.nombre||Math.random()); }

function renderAllGrouped(almList){
  var host = document.getElementById("grid");
  host.innerHTML = "";
  var frag = document.createDocumentFragment();
  (almList||[]).forEach(function(a){
    // Section container
    var section = document.createElement("div");
    section.className = "section";
    // Title
    var h = document.createElement("h3");
    var nom = (a.id!=null?a.id:a.codigo||a.nombre||"");
    var desc = (a.nombre||a.descripcion||"");
    h.className = "section-title";
    h.textContent = (nom? (String(nom)+" — "):"") + (desc||"");
    section.appendChild(h);
    // Cards grid
    var grid = document.createElement("div");
    grid.className = "cards";
    // Render each tank card
    (a.tanques||[]).forEach(function(t){ grid.appendChild(upsertCard(a,t,grid)); });
    section.appendChild(grid);
    frag.appendChild(section);
  });
  host.appendChild(frag);
}
function upsertCard(a,t,grid){
  var key=keyForTank(a,t); var ref=__STATE.cardsByKey.get(key);
  var col=colorFrom(t.color||t.colorProducto||t.colorRGB); var colLight=shade(col,+0.24);
  var pct=(t.capacidad>0)? percent((t.volumen/t.capacidad)*100):0;
  var nivel = nivelFromPct(pct); var colorNivel = nivelColorFromPct(pct);
  if(!ref){
    var card=document.createElement("div"); card.className="card";
    var tankWrap=document.createElement("div"); tankWrap.className="tankWrap";
    var tank=document.createElement("div"); tank.className="tank";
    var liquid=document.createElement("div"); liquid.className="liquid";
    liquid.style.setProperty("--fill",col); liquid.style.setProperty("--fillLight",colLight);
    var w1=document.createElement("div"); w1.className="wave"; var w2=document.createElement("div"); w2.className="wave wave2"; var w3=document.createElement("div"); w3.className="wave wave3";
    liquid.appendChild(w1); liquid.appendChild(w2); liquid.appendChild(w3);
    var gloss=document.createElement("div"); gloss.className="gloss"; tank.appendChild(gloss);
    var stripe=document.createElement("div"); stripe.className="stripe"; tank.appendChild(stripe);
    if(t.alturaAgua>0){ var water=document.createElement("div"); water.className="water"; tank.appendChild(water); }
    tank.appendChild(liquid); makeScale(tankWrap); tankWrap.appendChild(tank);
    var pctLabel=document.createElement("div"); pctLabel.className="pct"; tankWrap.appendChild(pctLabel);
    var stLayer=document.createElement("div"); stLayer.className="st-layer"; tankWrap.appendChild(stLayer);
    var info=document.createElement("div");
    var r1=document.createElement("div"); r1.style.display="flex"; r1.style.alignItems="center"; r1.style.justifyContent="space-between"; r1.style.margin="4px 0";
    var nm=document.createElement("div"); nm.className="name";
    var st=document.createElement("div"); st.className="status"; var dt=document.createElement("span"); dt.className="dot"; var stx=document.createElement("span"); st.appendChild(dt); st.appendChild(stx);
    r1.appendChild(nm); r1.appendChild(st); info.appendChild(r1);
    var c=document.createElement("canvas"); c.className="spark"; info.appendChild(c);
    var kv=document.createElement("div"); kv.className="kv"; info.appendChild(kv);
    card.appendChild(tankWrap); card.appendChild(info); grid.appendChild(card);
    card.onclick=function(){ var cards=document.querySelectorAll(".card"); for(var i=0;i<cards.length;i++) cards[i].classList.remove("sel"); card.classList.add("sel"); renderHistory(t); };
    ref={el:card, parts:{liquid,pctLabel,nm,dt,stx,kv,spark:c,water:null}, last:{pct:-1,volumen:-1,capacidad:-1,nombre:null,nivel:null,color:null}};
    __STATE.cardsByKey.set(key, ref);
  }
  var p=ref.parts;
  if(ref.last.color!==col){ p.liquid.style.setProperty("--fill",col); p.liquid.style.setProperty("--fillLight",colLight); ref.last.color=col; }
  if(ref.last.pct!==pct){ p.liquid.style.height=pct+"%"; p.pctLabel.textContent=percentFmt(pct); ref.last.pct=pct; }
  var nombre=(t.nombre||"TANQUE"); if(ref.last.nombre!==nombre){ p.nm.textContent=nombre; ref.last.nombre=nombre; }
  if(ref.last.nivel!==nivel){ p.dt.style.background=colorNivel; p.stx.textContent=nivel; ref.last.nivel=nivel;  p.stLayer.textContent=nivel; p.stLayer.style.background=colorNivel; }
  if(ref.last.volumen!==(t.volumen||0) || ref.last.capacidad!==(t.capacidad||0)){
    var ullage=(t.capacidad||0)-(t.volumen||0);
    p.kv.innerHTML="<div>Volumen</div><div><strong>"+litersLabel(t.volumen||0)+"</strong></div>"
                  +"<div>Capacidad</div><div>"+litersLabel(t.capacidad||0)+"</div>"
                  +"<div>Disponible</div><div>"+litersLabel(ullage)+"</div>"
                  +"<div>Producto</div><div>"+(t.producto||"-")+"</div>"
                  +"<div>Temp.</div><div>"+(t.temperatura!=null?t.temperatura.toFixed(1)+' °C':'-')+"</div>"
                  +"<div>Agua</div><div>"+(t.alturaAgua!=null?t.alturaAgua.toFixed(1)+' mm':'-')+"</div>";
    ref.last.volumen=(t.volumen||0); ref.last.capacidad=(t.capacidad||0);
  }
  (window.requestIdleCallback?requestIdleCallback:setTimeout)(function(){ drawSpark(p.spark, t.spark||[], col); },0);
  return ref.el;
}
function diffRenderAlmacen(a, host){ var grid=host.querySelector(':scope > .grid'); if(!grid){ grid=document.createElement('div'); grid.className='grid'; host.appendChild(grid);} var frag=document.createDocumentFragment(); (a.tanques||[]).forEach(function(t){ frag.appendChild(upsertCard(a,t,grid)); }); }
function fastRenderAll(almacenes){ var gridHost=document.getElementById("grid"); gridHost.innerHTML=""; __STATE.sectionByAlm.clear(); almacenes.forEach(function(a){ var section=document.createElement('section'); section.className='almacenSection'; var h=document.createElement('h2'); h.className='almacenTitle'; h.textContent=((a.id!=null?a.id:"") + " – " + (a.nombre||"Almacén")).trim(); section.appendChild(h); gridHost.appendChild(section); __STATE.sectionByAlm.set(a.id||a.nombre||Math.random(), section); diffRenderAlmacen(a, section); }); }
function fastRenderSingle(a){ var gridHost=document.getElementById("grid"); gridHost.innerHTML=""; var section=document.createElement('section'); section.className='almacenSection'; var h=document.createElement('h2'); h.className='almacenTitle'; h.textContent=((a.id!=null?a.id:"") + " – " + (a.nombre||"Almacén")).trim(); section.appendChild(h); gridHost.appendChild(section); diffRenderAlmacen(a, section); }


// -- Estado por porcentaje (Bajo/Medio/Alto/Lleno) --
function nivelFromPct(p){ p = Math.max(0, Math.min(100, Math.round(p||0))); return (p>=91)?"Lleno":(p>=51)?"Alto":(p>=21)?"Medio":"Bajo"; }
function nivelColorFromPct(p){ p = Math.max(0, Math.min(100, Math.round(p||0))); return (p>=91)?"#4ade80":(p>=51)?"#16a34a":(p>=21)?"#f59e0b":"#ef4444"; }

function colorFrom(v){ if(typeof v==="string") return v; if(typeof v==="number"){ var r=(v&255),g=(v>>8)&255,b=(v>>16)&255; return "#"+toHex(r)+toHex(g)+toHex(b);} return "#1987ff"; }
  function shade(hex, pct){ var m=/(?:#)?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(hex); if(!m) return hex; var r=parseInt(m[1],16),g=parseInt(m[2],16),b=parseInt(m[3],16); function adj(x){ return Math.max(0,Math.min(255,Math.round(x+pct*255))); } return "#"+toHex(adj(r))+toHex(adj(g))+toHex(adj(b)); }
  function statusColor(s){ return s==="ok"?"var(--ok)":(s==="warn"?"var(--warn)":"var(--bad)"); }
  function litersFmt(n){ return (Math.round(n||0)).toLocaleString(); }
  function litersLabel(n){ return litersFmt(n)+" L"; }
  function diffClass(d){ return d>0?"diffPos":(d<0?"diffNeg":"diffZero"); }
  function percent(n){ return Math.max(0, Math.min(100, n)); }
  function percentFmt(n){ return percent(n).toFixed(0)+" %"; }
  function parseDateStr(s){ var p=s.split(' '); var d=p[0].split('-'); var t=(p[1]||'00:00').split(':'); return new Date(Number(d[0]),Number(d[1])-1,Number(d[2]),Number(t[0]||0),Number(t[1]||0)); }

  function drawSpark(canvas, points, stroke){
    if(!canvas || !canvas.getContext) return;
    var ctx = canvas.getContext("2d");
    var w = canvas.width = canvas.clientWidth;
    var h = canvas.height = canvas.clientHeight;
    ctx.clearRect(0,0,w,h);
    if(!points || !points.length) return;
    var min = Math.min.apply(null, points);
    var max = Math.max.apply(null, points);
    var pad = 3;
    ctx.beginPath();
    for(var i=0;i<points.length;i++){
      var x = pad + (w-2*pad) * (i/(points.length-1));
      var y = h - pad - (h-2*pad) * ((points[i]-min)/Math.max(1,(max-min)));
      if(i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
    }
    ctx.lineWidth = 2;
    ctx.strokeStyle = stroke || "#9fd2ff";
    ctx.stroke();
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
    var lab=[], med=[], lib=[];
    if(mode==="days"){
      var map={};
      rows.forEach(function(r){
        var d = r.fecha.substr(0,10);
        if(!map[d]) map[d] = {m:0,l:0,c:0};
        map[d].m += (r.medido||0);
        map[d].l += (r.libro||0);
        map[d].c += 1;
      });
      Object.keys(map).sort().forEach(function(d){
        lab.push(d); med.push(map[d].m/map[d].c); lib.push(map[d].l/map[d].c);
      });
    }else{
      rows.forEach(function(r){ lab.push(r.fecha); med.push(r.medido||0); lib.push(r.libro||0); });
    }
    return {labels:lab, medido:med, libro:lib};
  }

  function groupByAlmacen(items){
    var map = {}; (items||[]).forEach(function(t){ var k=t.almacen||t.almacenNombre||"General"; if(!map[k]) map[k]={ id:k, nombre:k, tanques:[] }; map[k].tanques.push(t); });
    return Object.keys(map).sort().map(function(k){ return map[k]; });
  }

  function renderSelect(){
    var sel = document.getElementById("almacenSel"); sel.innerHTML="";
    almacenes.forEach(function(a,i){ var o=document.createElement("option"); o.value=a.id; o.textContent=a.nombre+" ("+(a.tanques?a.tanques.length:0)+")"; if(i===idxActivo) o.selected=true; sel.appendChild(o); });
  }

  function makeScale(container){
    var scale = document.createElement("div"); scale.className="scale";
    [100,75,50,25,0].forEach(function(p){ var row=document.createElement("div"); row.className="tick"; var line=document.createElement("div"); line.className="line"; var lab=document.createElement("div"); lab.textContent=p+"%"; row.appendChild(line); row.appendChild(lab); scale.appendChild(row); });
    container.appendChild(scale);
  }

  function renderHistory(tank){
    selectedTank = tank || null;
    var panel = document.getElementById("histPanel");
    if(!tank){ panel.hidden = true; return; }
    var key = (tank.almacen||"") + "|" + (tank.nombre||"");
    var rows = (historyByTank[key]||[]).slice().sort(function(a,b){ return parseDateStr(a.fecha) - parseDateStr(b.fecha); });
    var minD = rows.length? parseDateStr(rows[0].fecha) : null;
    var maxD = rows.length? parseDateStr(rows[rows.length-1].fecha) : null;
    var fd = document.getElementById("fromDate"); var td = document.getElementById("toDate");
    function fmtISO(d){ return d? (d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")) : ""; }
    if(minD && maxD){ fd.value = fmtISO(minD); td.value = fmtISO(maxD); }
    document.getElementById("histTitle").textContent = "Histórico · " + (tank.nombre||"") + " ("+(tank.producto||"-")+")";
    document.getElementById("histInfo").textContent = (tank.almacen || "Almacén");
    panel.hidden = false;
    applyFilterAndRender();
  }

  function applyFilterAndRender(){
    if(!selectedTank){ return; }
    var key = (selectedTank.almacen||"") + "|" + (selectedTank.nombre||"");
    var rows = (historyByTank[key]||[]).slice().sort(function(a,b){ return parseDateStr(a.fecha) - parseDateStr(b.fecha); });
    var fd = document.getElementById("fromDate").value;
    var td = document.getElementById("toDate").value;
    var df = fd? new Date(fd+"T00:00:00") : null;
    var dt = td? new Date(td+"T23:59:59") : null;
    filteredRows = rows.filter(function(r){ var d = parseDateStr(r.fecha); return (!df || d>=df) && (!dt || d<=dt); });
    document.getElementById("rowsCount").textContent = filteredRows.length + " filas";

    var tb = document.querySelector("#histTable tbody"); tb.innerHTML = "";
    filteredRows.forEach(function(r){
      var dif = (r.medido||0) - (r.libro||0);
      var tr = document.createElement("tr");
      tr.innerHTML = "<td style='text-align:left'>"+r.fecha+"</td>"
                   + "<td>"+litersFmt(r.medido||0)+"</td>"
                   + "<td>"+litersFmt(r.libro||0)+"</td>"
                   + "<td class='"+diffClass(dif)+"'>"+litersFmt(dif)+"</td>";
      tb.appendChild(tr);
    });

    var mode = document.getElementById("groupSel").value || "days";
    var grouped = groupForChart(filteredRows, mode);
    var col = colorFrom(selectedTank.color || selectedTank.colorProducto || selectedTank.colorRGB);
    drawLineChart(document.getElementById("histChart"),
      [{name:"Medido", data: grouped.medido, color: col},
       {name:"Libro", data: grouped.libro, color: "#9fd2ff"}],
      {labels: grouped.labels});
  }

  function exportCsv(filename, rows){
    var csv = "Fecha;Medido (L);Libro (L);Diferencia (L)\r\n";
    (rows||[]).forEach(function(r){ var d=(r.medido||0)-(r.libro||0); csv += [r.fecha, r.medido||0, r.libro||0, d].join(";") + "\r\n"; });
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
    var title = "Histórico - " + (tank.nombre||"") + " ("+(tank.producto||"-")+")";
    var css = "body{font:12px Arial;margin:16px;color:#111}h1{font-size:18px;margin:0 0 8px}h2{font-size:14px;margin:10px 0 6px}table{border-collapse:collapse;width:100%;font-size:11px}th,td{border:1px solid #ddd;padding:6px 8px;text-align:right}th:first-child,td:first-child{text-align:left}img{max-width:100%} .meta{margin-bottom:8px;color:#333}";
    var html = "<!doctype html><html><head><meta charset='utf-8'><title>"+title+"</title></head><body>";
    html += "<h1>"+title+"</h1>";
    html += "<div class='meta'>Almacén: <b>"+(tank.almacen||"")+"</b> · Rango: <b>"+(fd||"-")+"</b> a <b>"+(td||"-")+"</b></div>";
    html += "<h2>Evolución (Medido vs Libro)</h2><img src='"+img+"'/>";
    html += "<h2>Tabla de lecturas</h2><table><thead><tr><th>Fecha</th><th>Medido (L)</th><th>Libro (L)</th><th>Dif. (L)</th></tr></thead><tbody>";
    (filteredRows||[]).forEach(function(r){ var d=(r.medido||0)-(r.libro||0); html += "<tr><td>"+r.fecha+"</td><td>"+(r.medido||0)+"</td><td>"+(r.libro||0)+"</td><td>"+d+"</td></tr>"; });
    html += "</tbody></table></body></html>";
    win.document.open(); win.document.write(html); win.document.close();
    win.focus(); win.print();
  }

  function renderTotals(a){
    var host = document.getElementById("totales"); host.innerHTML = "";
    if(!a || !a.tanques || !a.tanques.length) return;
    var map = {};
    a.tanques.forEach(function(t){
      var key = t.producto || "—";
      if(!map[key]) map[key] = {vol:0, cap:0, count:0, color: (t.color||t.colorProducto||t.colorRGB)||"#888"};
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
    if(!almacenes.length){ document.getElementById("grid").innerHTML = ""; renderTotals(null); document.getElementById("histPanel").hidden=true; return; }
    if(window.__showAllMode){ renderAllGrouped(almacenes); document.getElementById("footerInfo").textContent = "Almacenes: "+almacenes.length+" • Activo: todos"; return; }
    var a = almacenes[idxActivo]; renderSelect();
    var currentKey = hashKey(window.__showAllMode ? almacenes : almacenes[idxActivo]);
    if(currentKey === __STATE.lastKey){ return; }
    __STATE.lastKey = currentKey;
    var total=0, cap=0, alarms=0; var grid = document.getElementById("grid"); grid.innerHTML = "";

    (a.tanques||[]).forEach(function(t){
      total += t.volumen||0; cap += t.capacidad||0; if(t.status==="bad") alarms++;

      var col = colorFrom(t.color || t.colorProducto || t.colorRGB);
      var colLight = shade(col, +0.24);
      var card = document.createElement("div"); card.className="card";
      var tankWrap = document.createElement("div"); tankWrap.className="tankWrap";
      var tank = document.createElement("div"); tank.className="tank";
      var liquid = document.createElement("div"); liquid.className="liquid";
      liquid.style.setProperty("--fill", col);
      liquid.style.setProperty("--fillLight", colLight);
      var pct = (t.capacidad>0)? percent((t.volumen/t.capacidad)*100) : 0; liquid.style.height = pct+"%";
      var w1=document.createElement("div"); w1.className="wave";
      var w2=document.createElement("div"); w2.className="wave wave2";
      var w3=document.createElement("div"); w3.className="wave wave3";
      liquid.appendChild(w1); liquid.appendChild(w2); liquid.appendChild(w3);
      var gloss=document.createElement("div"); gloss.className="gloss"; tank.appendChild(gloss);
      var stripe=document.createElement("div"); stripe.className="stripe"; tank.appendChild(stripe);
      if(t.alturaAgua>0){ var water=document.createElement("div"); water.className="water"; tank.appendChild(water); }
      tank.appendChild(liquid);
      makeScale(tankWrap);
      tankWrap.appendChild(tank);
      var pctLabel=document.createElement("div"); pctLabel.className="pct"; pctLabel.textContent = percentFmt(pct); tankWrap.appendChild(pctLabel);

      var info = document.createElement("div");
      var r1 = document.createElement("div"); r1.style.display="flex"; r1.style.alignItems="center"; r1.style.justifyContent="space-between"; r1.style.margin="4px 0";
      var nm = document.createElement("div"); nm.className="name"; nm.textContent = (t.nombre||"TANQUE");
      var st = document.createElement("div"); st.className="status";
      var dt = document.createElement("span"); dt.className="dot"; dt.style.background = nivelColorFromPct(pct);
      var stx = document.createElement("span"); stx.textContent = (t.status==="ok"?"Normal":(t.status==="warn"?"Atención":"Alarma"));
      st.appendChild(dt); st.appendChild(stx);
      r1.appendChild(nm); r1.appendChild(st);
      info.appendChild(r1);

      var c = document.createElement("canvas"); c.className="spark"; info.appendChild(c);

      var ullage = (t.capacidad||0) - (t.volumen||0);
      var kv = document.createElement("div"); kv.className="kv";
      kv.innerHTML = "<div>Volumen</div><div><strong>"+litersLabel(t.volumen||0)+"</strong></div>"
                   + "<div>Capacidad</div><div>"+litersLabel(t.capacidad||0)+"</div>"
                   + "<div>Disponible</div><div>"+litersLabel(ullage)+"</div>"
                   + "<div>Producto</div><div>"+(t.producto||"-")+"</div>"
                   + "<div>Temp.</div><div>"+(t.temperatura!=null? t.temperatura.toFixed(1)+' °C' : '-')+"</div>"
                   + "<div>Agua</div><div>"+(t.alturaAgua!=null? t.alturaAgua.toFixed(1)+' mm' : '-')+"</div>";
      info.appendChild(kv);

      card.appendChild(tankWrap); card.appendChild(info); grid.appendChild(card);
      setTimeout(function(){ drawSpark(c, t.spark||[], col); }, 0);

      card.onclick = function(){
        var cards = document.querySelectorAll(".card"); for(var i=0;i<cards.length;i++) cards[i].classList.remove("sel");
        card.classList.add("sel");
        renderHistory(t);
      };
    });

    renderTotals(a);
    var s = document.getElementById("summary");
    var pctTot = cap ? (total/cap*100) : 0;
    s.textContent = (a.nombre||"Almacén")+": "+percentFmt(pctTot)+" ("+litersLabel(total)+" de "+litersLabel(cap)+") • Alarmas: "+alarms;
    document.getElementById("footerInfo").textContent = "Almacenes: "+almacenes.length+" • Activo: "+(idxActivo+1)+"/"+almacenes.length;
  }

  window.setData = function(input){
    try{
      if(typeof input === "string") input = JSON.parse(input);
      if(Array.isArray(input)){ almacenes = groupByAlmacen(input);
      }else if(input && Array.isArray(input.almacenes)){
        almacenes = input.almacenes; if(input.activoId){ var i = almacenes.findIndex(function(a){ return a.id==input.activoId; }); if(i>=0) idxActivo = i; }
      }else{ almacenes = []; }
      idxActivo = Math.min(Math.max(0, idxActivo), Math.max(0, almacenes.length-1));
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
  
  document.getElementById("allToggle").addEventListener("change", function(e){ window.__showAllMode = !!e.target.checked; render(); });
document.getElementById("refreshBtn").addEventListener("click", function(){ if(typeof window.vfpRefresh==='function') window.vfpRefresh(); else location.reload(); });
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

  var amarillo="#fbbf24", azul="#3b82f6", rojo="#ef4444", hvo="#39FF14";
  function t(n,prod,col,cap,vol,alm){ return { almacen:alm, nombre:n, producto:prod, color:col, capacidad:cap, volumen:vol, status:"ok", alturaAgua:2, temperatura:24.0, spark:[50,52,51,53,54,55,56,58,59,57] }; }

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
      {fecha:"2025-07-28 08:00", medido:40100, libro:40020},
      {fecha:"2025-07-29 08:00", medido:40150, libro:40100},
      {fecha:"2025-07-30 08:00", medido:40200, libro:40120},
      {fecha:"2025-07-31 08:00", medido:40450, libro:40380},
      {fecha:"2025-08-01 08:00", medido:40500, libro:40300},
      {fecha:"2025-08-02 08:00", medido:40800, libro:40600},
      {fecha:"2025-08-03 08:00", medido:41000, libro:40950},
      {fecha:"2025-08-03 14:00", medido:40500, libro:40400},
      {fecha:"2025-08-03 20:00", medido:39800, libro:39600},
      {fecha:"2025-08-04 08:00", medido:39200, libro:39000}
    ],
    "ALMACEN 1|T3":[
      {fecha:"2025-07-30 08:00", medido:14000, libro:14120},
      {fecha:"2025-07-31 08:00", medido:13500, libro:13600},
      {fecha:"2025-08-01 08:00", medido:13000, libro:13100},
      {fecha:"2025-08-02 08:00", medido:12500, libro:12600},
      {fecha:"2025-08-03 08:00", medido:12000, libro:12100}
    ],
    "ALMACEN 2|T2":[
      {fecha:"2025-07-31 08:00", medido:22500, libro:22500},
      {fecha:"2025-08-01 08:00", medido:22400, libro:22350},
      {fecha:"2025-08-02 08:00", medido:22200, libro:22100}
    ]
  };

  if(!window.__vfp_integration__) { window.setData(demo); window.setHistoryData(hist); }
})();
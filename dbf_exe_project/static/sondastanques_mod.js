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
    h.textContent = (nom? (String(nom)+" - "):"") + (desc||"");
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
    var map = {};
    (items||[]).forEach(function(t){
      var k = t.almacen || t.almacen_key || t.almaKey || t.codigoAlmacen || t.id_alma || t.alma || "—";
      var nombre = t.almacenNombre || t.almacen_descr || t.poblacion || t.nombreAlmacen || t.almaNombre || t.localidad || t.descripcionAlmacen || null;
      if(!map[k]){ map[k] = { id: k, nombre: nombre || k, tanques: [] }; }
      else if(!map[k].nombre && nombre){ map[k].nombre = nombre; }
      map[k].tanques.push(t);
    });
    return Object.keys(map).sort().map(function(k){ return map[k]; });
  }
)();
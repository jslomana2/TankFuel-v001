# -*- coding: utf-8 -*-
import os, threading, webbrowser
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from flask import Flask, jsonify, render_template, request, Response
try:
    from dbfread import DBF
except Exception:
    DBF = None
app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("PROCONSI-Tanques")
def _read_dbf(path: str) -> List[Dict[str, Any]]:
    if DBF is None: raise RuntimeError("Falta 'dbfread'")
    if not os.path.exists(path): raise FileNotFoundError(path)
    return list(DBF(path, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
def _dt(fecha, hora):
    try:
        if fecha is None or hora is None: return None
        y,m,d = fecha.year, fecha.month, fecha.day
        s=str(hora).strip().zfill(6); h=int(s[0:2]); mi=int(s[2:4]); se=int(s[4:6])
        return datetime(y,m,d,h,mi,se)
    except: return None
def _f(v):
    try:
        if v is None: return None
        return float(str(v).replace(',','.').strip())
    except: return None
def _hex(n):
    try:
        if n is None: return None
        return "#" + format(int(float(n)) & 0xFFFFFF, "06X")
    except: return None
def load_almacenes_all(base):
    rows = _read_dbf(os.path.join(base, "FFALMA.DBF"))
    out = [{"codigo": str(r.get("CODIGO")), "nombre": str(r.get("POBLACION") or "")} for r in rows]
    out.sort(key=lambda x: x["codigo"] or "")
    return out
def load_articulos(base):
    rows = _read_dbf(os.path.join(base, "FFARTI.DBF"))
    return {str(r.get("CODIGO")): {"nombre": str(r.get("DESCRI") or ""), "color": _hex(r.get("COLORPRODU")) or "#2E8B57"} for r in rows}
def load_tanques(base):
    rows = _read_dbf(os.path.join(base, "FFTANQ.DBF"))
    out=[]; 
    for r in rows:
        out.append({"almacen": str(r.get("ALMACEN") or r.get("CODALMA") or r.get("IDALMA") or ""),
                    "tanque": str(r.get("CODIGO")),
                    "articulo": str(r.get("ARTICULO")),
                    "nombre": str(r.get("DESCRI") or ""),
                    "capacidad": _f(r.get("CAPACIDAD"))})
    return out
def load_calados(base):
    rows = _read_dbf(os.path.join(base, "FFCALA.DBF"))
    out=[]; 
    for r in rows:
        out.append({"almacen": str(r.get("ALMACEN")),
                    "tanque": str(r.get("CODIGO")),
                    "dt": _dt(r.get("FECHA"), r.get("HORA")),
                    "litros": _f(r.get("LITROS")),
                    "litros15": _f(r.get("LITROS15")),
                    "temperatura": _f(r.get("TEMPERA"))})
    return out
def latest_valid_by_tank(calados):
    calados=[c for c in calados if c["dt"] is not None]
    calados.sort(key=lambda x:(x["almacen"],x["tanque"],x["dt"]), reverse=True)
    latest={}
    for c in calados:
        k=(c["almacen"], c["tanque"])
        if k in latest: continue
        if c["litros"] is None or c["litros15"] is None or c["temperatura"] is None: continue
        latest[k]=c
    return latest
def filter_almacenes_with_data(base):
    almacenes = load_almacenes_all(base)
    calados = load_calados(base)
    last = latest_valid_by_tank(calados)
    valid = {k[0] for k in last.keys()}
    return [a for a in almacenes if a["codigo"] in valid]
def build_resp(base, almacen_sel=None):
    almacenes = filter_almacenes_with_data(base)
    if not almacenes: return {"ok": True, "almacenes": [], "tanques": [], "resumen_productos": []}
    if not almacen_sel: almacen_sel = almacenes[0]["codigo"]
    art=load_articulos(base); tqs=load_tanques(base); cal=load_calados(base); last=latest_valid_by_tank(cal)
    tanques_out=[]
    for t in tqs:
        if t["almacen"]!=str(almacen_sel): continue
        k=(t["almacen"], t["tanque"]); c=last.get(k)
        if not c: continue
        a=art.get(t["articulo"], {"nombre": None, "color": None})
        tanques_out.append({"almacen": t["almacen"], "tanque": t["tanque"], "tanque_nombre": t["nombre"],
                            "producto": t["articulo"], "producto_nombre": a["nombre"], "producto_color": a["color"],
                            "capacidad": t["capacidad"], "volumen": c["litros"], "litros15": c["litros15"], "temperatura": c["temperatura"]})
    total=sum([(x["litros15"] or 0) for x in tanques_out]) or 1.0
    res={}
    for x in tanques_out:
        r=res.setdefault(x["producto"], {"producto": x["producto"], "producto_nombre": x["producto_nombre"], "color_hex": x["producto_color"], "total_litros15":0.0, "num_tanques":0})
        r["total_litros15"] += x["litros15"] or 0; r["num_tanques"] += 1
    for r in res.values(): r["porcentaje"]=round((r["total_litros15"]/total)*100,1)
    return {"ok": True, "almacen": almacen_sel, "almacenes": almacenes, "tanques": tanques_out, "resumen_productos": list(res.values())}
@app.route("/")
def home(): return render_template("sondastanques_mod.html")
@app.route("/compat")
def compat(): return Response(status=204)
@app.route("/favicon.ico")
def ico(): return Response(status=204)
@app.route("/api/almacenes")
def api_alma(): return jsonify({"ok": True, "almacenes": filter_almacenes_with_data(os.getcwd())})
@app.route("/api/tanques_norm")
def api_tq(): return jsonify(build_resp(os.getcwd(), request.args.get("almacen")))
@app.route("/api/where")
def api_where(): return jsonify({"cwd": os.getcwd(), "files": sorted(os.listdir(os.getcwd()))})
if __name__ == "__main__":
    port=int(os.environ.get("PORT","5000")); url=f"http://127.0.0.1:{port}"
    threading.Timer(1.0, lambda: webbrowser.open(url, new=1, autoraise=True)).start()
    log.info(f"Iniciando servidor en {url}")
    app.run(host="127.0.0.1", port=port, debug=True)

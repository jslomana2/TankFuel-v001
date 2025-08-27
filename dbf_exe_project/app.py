
# -*- coding: utf-8 -*-
import os, sys, threading, webbrowser, logging
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from flask import Flask, jsonify, render_template, request, Response

try:
    from dbfread import DBF
except Exception:
    DBF = None

app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("PROCONSI-Tanques")

def get_dbf_base() -> str:
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()

def _read_dbf(path: str):
    if DBF is None: raise RuntimeError("Falta 'dbfread'.")
    if not os.path.exists(path): raise FileNotFoundError(path)
    return list(DBF(path, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))

def _dt(fecha, hora):
    try:
        if fecha is None or hora is None: return None
        y,m,d = fecha.year, fecha.month, fecha.day
        s=str(hora).strip().zfill(6); h=int(s[0:2]); mi=int(s[2:4]); se=int(s[4:6])
        return datetime(y,m,d,h,mi,se)
    except Exception:
        return None

def _f(v):
    try:
        if v is None: return None
        return float(str(v).replace(',','.').strip())
    except Exception:
        return None

def _hex(n):
    try:
        if n is None: return None
        return "#" + format(int(float(n)) & 0xFFFFFF, "06X")
    except Exception:
        return None

def _last_non_null(values):
    for v in values:
        if v is None: continue
        if isinstance(v, str) and v.strip()=='': continue
        return v
    return None

def load_almacenes_all(base: str):
    rows = _read_dbf(os.path.join(base, "FFALMA.DBF"))
    out = [{"codigo": str(r.get("CODIGO")), "nombre": str(r.get("POBLACION") or "")} for r in rows]
    out.sort(key=lambda x: x["codigo"] or "")
    return out

def load_articulos(base: str):
    rows = _read_dbf(os.path.join(base, "FFARTI.DBF"))
    return {str(r.get("CODIGO")): {"codigo": str(r.get("CODIGO")), "nombre": str(r.get("DESCRI") or ""), "color": _hex(r.get("COLORPRODU")) or "#2E8B57"} for r in rows}

def load_tanques(base: str):
    rows = _read_dbf(os.path.join(base, "FFTANQ.DBF"))
    out=[]
    for r in rows:
        out.append({"almacen": str(r.get("ALMACEN") or r.get("CODALMA") or r.get("IDALMA") or ""),
                    "tanque":  str(r.get("CODIGO")),
                    "articulo": str(r.get("ARTICULO")),
                    "nombre":   str(r.get("DESCRI") or ""),
                    "capacidad": _f(r.get("CAPACIDAD"))})
    def keyfunc(t):
        try: return (t["almacen"], float(t["tanque"]))
        except Exception: return (t["almacen"], t["tanque"])
    out.sort(key=keyfunc)
    return out

def load_calados(base: str):
    rows = _read_dbf(os.path.join(base, "FFCALA.DBF"))
    out=[]
    for r in rows:
        out.append({"almacen": str(r.get("ALMACEN")),
                    "tanque":  str(r.get("TANQUE")),
                    "articulo": str(r.get("ARTICULO")),
                    "articulo_nombre": str(r.get("DESCRI") or ""),
                    "dt": _dt(r.get("FECHA"), r.get("HORA")),
                    "litros": _f(r.get("LITROS")),
                    "litros15": _f(r.get("LITROS15")),
                    "temperatura": _f(r.get("TEMPERA"))})
    return out

def latest_by_rule(calados):
    groups={}
    for c in calados:
        if c["dt"] is None: continue
        groups.setdefault((c["almacen"], c["tanque"]), []).append(c)
    for k in groups:
        groups[k].sort(key=lambda x: x["dt"], reverse=True)
        groups[k]=groups[k][:5]
    latest={}
    for k, rows in groups.items():
        v=_last_non_null([r["litros"] for r in rows])
        l15=_last_non_null([r["litros15"] for r in rows])
        t=_last_non_null([r["temperatura"] for r in rows])
        if v is None or l15 is None or t is None: continue
        latest[k]={"volumen": v, "litros15": l15, "temperatura": t}
    return latest

def filter_almacenes_with_data(base):
    tqs=load_tanques(base); cal=load_calados(base); last=latest_by_rule(cal)
    valid={t["almacen"] for t in tqs if (t["almacen"], t["tanque"]) in last}
    alma=load_almacenes_all(base); name_by={a["codigo"]: a["nombre"] for a in alma}
    return [{"codigo": c, "nombre": name_by.get(c, "")} for c in sorted(valid) if c in name_by]

def build_response(base, almacen_sel):
    almacenes=filter_almacenes_with_data(base)
    if not almacenes: return {"ok": True, "almacenes": [], "tanques": [], "resumen_productos": []}
    if not almacen_sel: almacen_sel=almacenes[0]["codigo"]
    art=load_articulos(base); tqs=load_tanques(base); cal=load_calados(base); last=latest_by_rule(cal)
    tanques_out=[]
    for t in tqs:
        if t["almacen"]!=str(almacen_sel): continue
        k=(t["almacen"], t["tanque"]); c=last.get(k)
        if not c: continue
        a=art.get(t["articulo"], {"nombre": None, "color": None})
        tanques_out.append({"almacen": t["almacen"], "tanque": t["tanque"], "tanque_nombre": t["nombre"],
                            "producto": t["articulo"], "producto_nombre": a["nombre"], "producto_color": a["color"],
                            "capacidad": t["capacidad"], **c})
    total=sum([(x["litros15"] or 0) for x in tanques_out]) or 1.0
    res={}
    for x in tanques_out:
        r=res.setdefault(x["producto"], {"producto": x["producto"], "producto_nombre": x["producto_nombre"], "color_hex": x["producto_color"], "total_litros15":0.0, "num_tanques":0})
        r["total_litros15"]+=x["litros15"] or 0; r["num_tanques"]+=1
    for r in res.values(): r["porcentaje"]=round((r["total_litros15"]/total)*100,1)
    return {"ok": True, "almacen": almacen_sel, "almacenes": almacenes, "tanques": tanques_out, "resumen_productos": sorted(res.values(), key=lambda x: -x["total_litros15"])}

@app.route("/")
def home(): return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    base=get_dbf_base()
    if request.args.get("all")=="1":
        return jsonify({"ok": True, "almacenes": load_almacenes_all(base)})
    return jsonify({"ok": True, "almacenes": filter_almacenes_with_data(base)})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    base=get_dbf_base()
    return jsonify(build_response(base, request.args.get("almacen")))

@app.route("/api/ffcala/campos")
def api_campos():
    base=get_dbf_base()
    rows=_read_dbf(os.path.join(base,"FFCALA.DBF"))
    fields=list(rows[0].keys()) if rows else []
    return jsonify({"ok": True, "fields": fields, "count": len(rows)})

@app.route("/api/where")
def api_where():
    base=get_dbf_base()
    return jsonify({"base_dir": base, "files": sorted(os.listdir(base))})

@app.route("/favicon.ico")
def ico(): return Response(status=204)

def _open(url):
    try: webbrowser.open(url, new=1, autoraise=True)
    except Exception: pass

if __name__=="__main__":
    port=int(os.environ.get("PORT","5000")); url=f"http://127.0.0.1:{port}"
    threading.Timer(1.0, _open, args=(url,)).start()
    log.info(f"Iniciando servidor en {url}")
    app.run(host="127.0.0.1", port=port, debug=True)

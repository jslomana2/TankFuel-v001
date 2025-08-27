# -*- coding: utf-8 -*-
import os, sys, logging, re, threading, webbrowser
from datetime import datetime
from functools import lru_cache
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("PROCONSI-Tanques")

def base_dir():
    # En EXE (PyInstaller): carpeta del ejecutable; en dev: cwd
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()

def _f(x):
    try:
        if x is None: return None
        return float(str(x).replace(',','.'))
    except Exception:
        return None

def _dt(fecha, hora):
    try:
        if fecha is None or hora is None: return None
        y,m,d = fecha.year, fecha.month, fecha.day
        s = re.sub(r'\D','', str(hora))
        s = (s or "0").zfill(6)[-6:]
        h,mi,se = int(s[:2]), int(s[2:4]), int(s[4:6])
        return datetime(y,m,d,h,mi,se)
    except Exception:
        return None

def _color_hex_from_colorref(n):
    """FFARTI.COLORPRODU en COLORREF (BGR) decimal -> #RRGGBB (RGB)."""
    try:
        v = int(float(n)) & 0xFFFFFF
        r = v & 0xFF
        g = (v >> 8) & 0xFF
        b = (v >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return None

def _norm(c):
    s = ("" if c is None else str(c)).strip()
    s2 = s.lstrip("0")
    return s if s2=="" else s2

@lru_cache(maxsize=1)
def _almacenes_all():
    rows = list(DBF(os.path.join(base_dir(), "FFALMA.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = []
    for r in rows:
        cod = str(r.get("CODIGO"))
        out.append({"codigo": cod, "key": _norm(cod), "nombre": str(r.get("POBLACION") or "")})
    out.sort(key=lambda x: x["codigo"] or "")
    return out

@lru_cache(maxsize=1)
def _articulos():
    rows = list(DBF(os.path.join(base_dir(), "FFARTI.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = {}
    for r in rows:
        cod = str(r.get("CODIGO"))
        out[cod] = {
            "codigo": cod,
            "nombre": str(r.get("DESCRI") or ""),
            "color": _color_hex_from_colorref(r.get("COLORPRODU")) or "#CCCCCC"
        }
    return out

@lru_cache(maxsize=1)
def _tanques_all():
    rows = list(DBF(os.path.join(base_dir(), "FFTANQ.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = []
    for r in rows:
        alma = str(r.get("ALMACEN") or r.get("CODALMA") or r.get("IDALMA") or "")
        out.append({
            "almacen": alma,
            "almacen_key": _norm(alma),
            "tanque": str(r.get("CODIGO")),
            "articulo": str(r.get("ARTICULO")),
            "nombre": str(r.get("DESCRI") or ""),
            "capacidad": _f(r.get("CAPACIDAD"))
        })
    def k(t):
        try: return (t["almacen_key"], float(t["tanque"]))
        except Exception: return (t["almacen_key"], t["tanque"])
    out.sort(key=k)
    return out

def _last_non_null(seq):
    for v in seq:
        if v is None: continue
        if isinstance(v, str) and not v.strip(): continue
        return v
    return None

def _latest_for_almacen(almacen_key:str, n:int=5):
    """Lee FFCALA y conserva solo las últimas n por tanque del almacén pedido."""
    path = os.path.join(base_dir(), "FFCALA.DBF")
    latest = {}
    buffers = {}  # tanque -> list rows
    for r in DBF(path, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'):
        alma = _norm(str(r.get("ALMACEN")))
        if alma != almacen_key: 
            continue
        t = str(r.get("TANQUE"))
        dt = _dt(r.get("FECHA"), r.get("HORA"))
        if dt is None: 
            continue
        lst = buffers.setdefault(t, [])
        lst.append({
            "dt": dt,
            "litros": _f(r.get("LITROS")),
            "litros15": _f(r.get("LITROS15")),
            "temperatura": _f(r.get("TEMPERA"))
        })
    for t, rows in buffers.items():
        rows.sort(key=lambda x:x["dt"], reverse=True)
        rows = rows[:max(1,int(n))]
        v = _last_non_null([r["litros"] for r in rows])
        l15 = _last_non_null([r["litros15"] for r in rows])
        te = _last_non_null([r["temperatura"] for r in rows])
        if v is None or l15 is None or te is None:
            continue  # NO mostrar tanque si falta algo
        latest[t] = {
            "volumen": round(v),
            "litros15": round(l15),
            "temperatura": te
        }
    return latest

def _almacenes_validos(n:int=5):
    alma = _almacenes_all()
    key_to_canon = {a["key"]: a["codigo"] for a in alma}
    name_by_canon = {a["codigo"]: a["nombre"] for a in alma}
    keys = sorted({ t["almacen_key"] for t in _tanques_all() })
    out = []
    for k in keys:
        if _latest_for_almacen(k, n=n):
            canon = key_to_canon.get(k)
            if canon:
                out.append({"codigo": canon, "nombre": name_by_canon.get(canon, "")})
    return out

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    n = int(request.args.get("n","5"))
    return jsonify({"ok": True, "almacenes": _almacenes_validos(n=n)})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    n = int(request.args.get("n","5"))
    sel = request.args.get("almacen", "")
    alma_all = _almacenes_all()
    key_to_canon = {a["key"]: a["codigo"] for a in alma_all}
    valid = _almacenes_validos(n=n)
    if not valid:
        return jsonify({"ok": True, "almacenes": [], "tanques": [], "resumen_productos": []})
    sel_key = _norm(sel) if sel else _norm(valid[0]["codigo"])
    canon = key_to_canon.get(sel_key, sel_key)

    latest = _latest_for_almacen(sel_key, n=n)
    art = _articulos()
    tanques = _tanques_all()
    out = []
    for t in tanques:
        if t["almacen_key"] != sel_key: 
            continue
        c = latest.get(t["tanque"])
        if not c: 
            continue
        a = art.get(t["articulo"], {"nombre": None, "color": None})
        out.append({
            "almacen": canon,
            "tanque": t["tanque"],
            "tanque_nombre": t["nombre"],
            "producto": t["articulo"],
            "producto_nombre": a["nombre"],
            "producto_color": a["color"],
            "capacidad": t["capacidad"],
            **c
        })
    total = sum((x["litros15"] or 0) for x in out) or 1.0
    resumen = {}
    for x in out:
        r = resumen.setdefault(x["producto"], {
            "producto": x["producto"], "producto_nombre": x["producto_nombre"],
            "color_hex": x["producto_color"], "total_litros15": 0.0, "num_tanques": 0
        })
        r["total_litros15"] += x["litros15"] or 0
        r["num_tanques"] += 1
    for r in resumen.values():
        r["porcentaje"] = round((r["total_litros15"]/total)*100, 1)

    return jsonify({
        "ok": True,
        "almacen": canon,
        "almacenes": valid,
        "tanques": out,
        "resumen_productos": sorted(resumen.values(), key=lambda x: -x["total_litros15"])
    })

@app.route("/api/where")
def api_where():
    b = base_dir()
    try:
        files = sorted(os.listdir(b))
    except Exception:
        files = []
    return jsonify({"base_dir": b, "files": files})

@app.route("/api/ffcala/campos")
def api_campos():
    path = os.path.join(base_dir(), "FFCALA.DBF")
    rows = list(DBF(path, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    fields = list(rows[0].keys()) if rows else []
    return jsonify({"ok": True, "fields": fields, "count": len(rows)})

@app.route("/favicon.ico")
def ico():
    return Response(status=204)

def open_browser_once(url):
    try:
        webbrowser.open(url, new=1, autoraise=True)
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    threading.Timer(0.8, open_browser_once, args=(url,)).start()
    log.info(f"Iniciando servidor en {url}")
    # use_reloader=False -> evita doble proceso; el EXE queda abierto
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

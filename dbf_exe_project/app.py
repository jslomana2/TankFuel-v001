# -*- coding: utf-8 -*-
import os, sys, logging, re
from datetime import datetime
from functools import lru_cache
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("SondaTanques")

def base_dir():
    # DBFs estarán junto al EXE (o en cwd en modo dev)
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
    """FFARTI.COLORPRODU viene en COLORREF (BGR decimal). Lo convertimos a #RRGGBB"""
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
def _load_articulos():
    rows = list(DBF(os.path.join(base_dir(),"FFARTI.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = {}
    for r in rows:
        cod = str(r.get("CODIGO"))
        out[cod] = {
            "codigo": cod,
            "nombre": str(r.get("DESCRI") or ""),
            "color": _color_hex_from_colorref(r.get("COLORPRODU")) or "#80FFFF"
        }
    return out

@lru_cache(maxsize=1)
def _load_almacenes_all():
    rows = list(DBF(os.path.join(base_dir(),"FFALMA.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = []
    for r in rows:
        cod = str(r.get("CODIGO"))
        out.append({"codigo": cod, "key": _norm(cod), "nombre": str(r.get("POBLACION") or "")})
    out.sort(key=lambda x: x["codigo"] or "")
    return out

@lru_cache(maxsize=1)
def _load_tanques_all():
    rows = list(DBF(os.path.join(base_dir(),"FFTANQ.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = []
    for r in rows:
        alma = str(r.get("ALMACEN") or r.get("CODALMA") or r.get("IDALMA") or "")
        out.append({
            "almacen": alma, "almacen_key": _norm(alma),
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

def _iter_calados():
    return DBF(os.path.join(base_dir(),"FFCALA.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore')

def _last_non_null(seq):
    for v in seq:
        if v is None: continue
        if isinstance(v,str) and not v.strip(): continue
        return v
    return None

def _latest_for_almacen(almacen_key:str, n:int=5):
    """Recorre FFCALA sólo guardando las últimos N por tanque del almacén pedido (rápido)."""
    buckets = {}
    for r in _iter_calados():
        alma = _norm(str(r.get("ALMACEN")))
        if alma != almacen_key: 
            continue
        t = str(r.get("TANQUE"))
        dt = _dt(r.get("FECHA"), r.get("HORA"))
        if dt is None: 
            continue
        b = buckets.setdefault(t, [])
        b.append({
            "dt": dt,
            "litros": _f(r.get("LITROS")),
            "litros15": _f(r.get("LITROS15")),
            "temperatura": _f(r.get("TEMPERA"))
        })
    latest = {}
    for t, rows in buckets.items():
        rows.sort(key=lambda x:x["dt"], reverse=True)
        rows = rows[:max(1,int(n))]
        v = _last_non_null([r["litros"] for r in rows])
        l15 = _last_non_null([r["litros15"] for r in rows])
        te = _last_non_null([r["temperatura"] for r in rows])
        if v is None or l15 is None or te is None:
            continue
        latest[t] = {"volumen": round(v), "litros15": round(l15), "temperatura": te}
    return latest

@lru_cache(maxsize=1)
def _almacenes_con_datos(n:int=5):
    """Construye la lista de almacenes válidos: tanques con últimos n no nulos.
       Para no tardar, tomamos el conjunto de almacenes de FFTANQ y luego
       validamos contra FFCALA rápidamente (primer match)."""
    alma_all = _load_almacenes_all()
    key_to_canon = {a["key"]: a["codigo"] for a in alma_all}
    tanques = _load_tanques_all()
    keys = sorted({t["almacen_key"] for t in tanques})
    valid = []
    for k in keys:
        lat = _latest_for_almacen(k, n=n)
        if lat:  # hay al menos un tanque válido
            canon = key_to_canon.get(k, None)
            if canon:
                nombre = next((a["nombre"] for a in alma_all if a["codigo"]==canon), "")
                valid.append({"codigo": canon, "nombre": nombre})
    return valid

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    n = int(request.args.get("n","5"))
    return jsonify({"ok": True, "almacenes": _almacenes_con_datos(n=n)})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    n = int(request.args.get("n","5"))
    alma_param = request.args.get("almacen", "")
    alma_all = _load_almacenes_all()
    key_to_canon = {a["key"]: a["codigo"] for a in alma_all}
    sel_key = _norm(alma_param) if alma_param else _norm(_almacenes_con_datos(n=n)[0]["codigo"])
    canon = key_to_canon.get(sel_key, sel_key)

    latest = _latest_for_almacen(sel_key, n=n)
    tanques = _load_tanques_all()
    art = _load_articulos()
    out = []
    for t in tanques:
        if t["almacen_key"] != sel_key: 
            continue
        c = latest.get(t["tanque"])
        if not c: continue
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
    # resumen por producto
    total = sum((x["litros15"] or 0) for x in out) or 1.0
    resumen = {}
    for x in out:
        r = resumen.setdefault(x["producto"], {
            "producto": x["producto"], "producto_nombre": x["producto_nombre"],
            "color_hex": x["producto_color"], "total_litros15":0.0, "num_tanques":0
        })
        r["total_litros15"] += x["litros15"] or 0
        r["num_tanques"] += 1
    for r in resumen.values():
        r["porcentaje"] = round((r["total_litros15"]/total)*100,1)

    return jsonify({
        "ok": True,
        "almacen": canon,
        "almacenes": _almacenes_con_datos(n=n),
        "tanques": out,
        "resumen_productos": sorted(resumen.values(), key=lambda x: -x["total_litros15"])
    })

@app.route("/favicon.ico")
def ico(): 
    return Response(status=204)

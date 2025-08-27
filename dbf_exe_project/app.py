# -*- coding: utf-8 -*-
import os, sys, logging, re, threading, webbrowser, time
from datetime import datetime
from functools import lru_cache
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

app = Flask(__name__, static_folder="static", template_folder="templates")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("PROCONSI-Tanques")

N_LAST = 5  # cuántas lecturas considerar
_cache = {
    "mtime": None,
    "latest": {},      # (almaKey, tanque) -> dict(volumen, litros15, temperatura, dt)
    "by_almacen": {},  # almaKey -> { tanque -> latest }
}

def base_dir():
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
    try:
        v = int(float(n)) & 0xFFFFFF
        r = v & 0xFF
        g = (v >> 8) & 0xFF
        b = (v >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return "#CCCCCC"

def _norm(s):
    s = ("" if s is None else str(s)).strip()
    s2 = s.lstrip("0")
    return s if s2=="" else s2

@lru_cache(maxsize=1)
def _almacenes_all():
    rows = list(DBF(os.path.join(base_dir(), "FFALMA.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = []
    for r in rows:
        codigo = str(r.get("CODIGO"))
        out.append({"codigo": codigo, "key": _norm(codigo), "nombre": str(r.get("POBLACION") or "")})
    out.sort(key=lambda x: x["codigo"] or "")
    return out

@lru_cache(maxsize=1)
def _articulos():
    rows = list(DBF(os.path.join(base_dir(), "FFARTI.DBF"), ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
    out = {}
    for r in rows:
        cod = str(r.get("CODIGO"))
        out[cod] = {"nombre": str(r.get("DESCRI") or ""), "color": _color_hex_from_colorref(r.get("COLORPRODU"))}
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
            "capacidad": _f(r.get("CAPACIDAD")),
        })
    def k(t):
        try: return (t["almacen_key"], float(t["tanque"]))
        except Exception: return (t["almacen_key"], t["tanque"])
    out.sort(key=k)
    return out

def _last_non_null(vals):
    for v in vals:
        if v is None: continue
        if isinstance(v, str) and not v.strip(): continue
        return v
    return None

def _preload_latest():
    """Carga FFCALA en memoria: últimas N por tanque y alm. Construye cache global."""
    path = os.path.join(base_dir(), "FFCALA.DBF")
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = None
    if _cache["mtime"] == mtime and _cache["latest"]:
        return  # ya válido

    t0 = time.time()
    buffers = {}  # (almaKey, tanque) -> list rows
    for r in DBF(path, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'):
        almaKey = _norm(str(r.get("ALMACEN")))
        tanq = str(r.get("TANQUE"))
        dt = _dt(r.get("FECHA"), r.get("HORA"))
        if dt is None: 
            continue
        lst = buffers.setdefault((almaKey, tanq), [])
        lst.append({
            "dt": dt,
            "litros": _f(r.get("LITROS")),
            "litros15": _f(r.get("LITROS15")),
            "temperatura": _f(r.get("TEMPERA")),
        })
    latest = {}
    by_alm = {}
    for key, rows in buffers.items():
        rows.sort(key=lambda x:x["dt"], reverse=True)
        rows = rows[:N_LAST]
        v = _last_non_null([r["litros"] for r in rows])
        l15 = _last_non_null([r["litros15"] for r in rows])
        te = _last_non_null([r["temperatura"] for r in rows])
        if v is None or l15 is None or te is None:
            continue
        almaKey, tanq = key
        d = {"volumen": round(v), "litros15": round(l15), "temperatura": te, "dt": rows[0]["dt"]}
        latest[key] = d
        by_alm.setdefault(almaKey, {})[tanq] = d

    _cache["latest"] = latest
    _cache["by_almacen"] = by_alm
    _cache["mtime"] = mtime
    log.info("Preload FFCALA: %d tanques válidos en %.2fs", len(latest), time.time()-t0)

def _ensure_preloaded():
    try:
        _preload_latest()
    except Exception as e:
        log.exception("Error precargando FFCALA: %s", e)

def _almacenes_validos():
    _ensure_preloaded()
    alma = _almacenes_all()
    name_by_key = {a["key"]: a["nombre"] for a in alma}
    canon_by_key = {a["key"]: a["codigo"] for a in alma}
    keys = sorted(_cache["by_almacen"].keys())
    out = []
    for k in keys:
        if _cache["by_almacen"].get(k):
            canon = canon_by_key.get(k, k)
            out.append({"codigo": canon, "nombre": name_by_key.get(k, "")})
    return out

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    return jsonify({"ok": True, "almacenes": _almacenes_validos()})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    sel = request.args.get("almacen","")
    alma_all = _almacenes_all()
    key_by_canon = {_norm(a["codigo"]): a["key"] for a in alma_all}
    canon_by_key = {a["key"]: a["codigo"] for a in alma_all}

    _ensure_preloaded()
    valid = _almacenes_validos()
    if not valid:
        return jsonify({"ok": True, "almacenes": [], "tanques": [], "resumen_productos": []})

    alma_key = _norm(sel) if sel else _norm(valid[0]["codigo"])
    # si viene canon, pasa a key
    alma_key = key_by_canon.get(alma_key, alma_key)
    canon = canon_by_key.get(alma_key, sel)

    latest_map = _cache["by_almacen"].get(alma_key, {})
    art = _articulos()
    tanques = _tanques_all()
    out = []
    for t in tanques:
        if t["almacen_key"] != alma_key: 
            continue
        c = latest_map.get(t["tanque"])
        if not c:
            continue
        a = art.get(t["articulo"], {"nombre": None, "color": "#CCCCCC"})
        out.append({
            "almacen": canon,
            "tanque": t["tanque"],
            "tanque_nombre": t["nombre"],
            "producto": t["articulo"],
            "producto_nombre": a["nombre"],
            "producto_color": a["color"],
            "capacidad": t["capacidad"],
            "volumen": c["volumen"],
            "litros15": c["litros15"],
            "temperatura": c["temperatura"],
        })
    total = sum((x["litros15"] or 0) for x in out) or 1.0
    resumen = {}
    for x in out:
        r = resumen.setdefault(x["producto"], {"producto": x["producto"], "producto_nombre": x["producto_nombre"], "color_hex": x["producto_color"], "total_litros15": 0.0, "num_tanques": 0})
        r["total_litros15"] += x["litros15"] or 0
        r["num_tanques"] += 1
    for r in resumen.values():
        r["porcentaje"] = round((r["total_litros15"]/total)*100, 1)

    return jsonify({"ok": True, "almacen": canon, "almacenes": valid, "tanques": out, "resumen_productos": sorted(resumen.values(), key=lambda x: -x["total_litros15"])} )

@app.route("/api/refresh")
def api_refresh():
    # fuerza recarga si cambió el mtime
    _cache["mtime"] = None
    _ensure_preloaded()
    return jsonify({"ok": True})

@app.route("/api/where")
def api_where():
    b = base_dir()
    try:
        files = sorted(os.listdir(b))
    except Exception:
        files = []
    return jsonify({"base_dir": b, "files": files})

@app.route("/favicon.ico")
def ico():
    return Response(status=204)

def open_browser_once(url):
    try: webbrowser.open(url, new=1, autoraise=True)
    except Exception: pass

def _startup():
    # precarga ANTES de abrir navegador para que la primera carga sea instantánea
    _ensure_preloaded()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    _startup()
    threading.Timer(0.5, open_browser_once, args=(url,)).start()
    log.info(f"Iniciando servidor en {url}")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

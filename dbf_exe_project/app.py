# -*- coding: utf-8 -*-
"""
PROCONSI – Tanques (Flask + DBF)
- Lee FFALMA.DBF, FFARTI.DBF, FFTANQ.DBF, FFCALA.DBF desde el MISMO directorio que el .exe/.py
- Endpoints:
    /                                   -> UI (templates/sondastanques_mod.html)
    /api/almacenes                      -> JSON con almacenes
    /api/articulos                      -> JSON con artículos (con color_hex desde FFARTI.COLORPRODU)
    /api/tanques_norm                   -> JSON tanques normalizados (usa COLORPRODU de FFARTI)
    /api/calibraciones/ultimas?tanque_id=ALM[-TANQUE]&n=10  -> últimos n movimientos de FFCALA
"""
import os, sys, json, logging, webbrowser
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from flask import Flask, jsonify, render_template, request

APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
DBF_DIR = APP_DIR  # los DBF están junto al exe

LOG_FILE = os.path.join(APP_DIR, "app.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()]
)
log = logging.getLogger("proconsi-tanques")

try:
    from dbfread import DBF
except Exception as e:
    DBF = None
    log.warning("dbfread no disponible. Instale con: pip install dbfread")

# ----------------------- util -----------------------
def _to_int(v, default=0):
    try:
        if isinstance(v, float):
            return int(v)
        return int(str(v).strip())
    except Exception:
        return default

def _to_float(v, default=0.0):
    try:
        return float(str(v).replace(',', '.'))
    except Exception:
        return default

def _to_str(v, default=""):
    try:
        s = "" if v is None else str(v)
        return s.strip()
    except Exception:
        return default

def _first(rec, keys, default=None):
    for k in keys:
        if k in rec and rec[k] not in (None, ""):
            return rec[k]
    return default

def _color_hex_from_number(n):
    try:
        n = _to_int(n, 0)
        n = max(0, min(n, 0xFFFFFF))
        return f"#{n:06x}"
    except Exception:
        return None

class SafeJSON(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (date, datetime)):
            return o.isoformat()
        if isinstance(o, Decimal):
            return float(o)
        try:
            return str(o)
        except Exception:
            return None

def json_resp(obj):
    return app.response_class(
        response=json.dumps(obj, ensure_ascii=False, cls=SafeJSON),
        status=200,
        mimetype="application/json"
    )

def _read_dbf(file_name):
    """Lee un DBF del directorio DBF_DIR devolviendo lista de dict con CLAVES EN MAYÚSCULAS."""
    path = os.path.join(DBF_DIR, file_name)
    if not os.path.exists(path):
        log.warning("DBF no encontrado: %s", path)
        return []
    if DBF is None:
        log.error("dbfread no instalado. No puedo leer %s", path)
        return []
    try:
        # cp1252 suele ser correcto; si no, latin-1
        table = DBF(path, load=True, encoding="cp1252", ignore_missing_memofile=True)
    except Exception:
        table = DBF(path, load=True, encoding="latin-1", ignore_missing_memofile=True)

    rows = []
    for r in table:
        # normaliza claves a MAYÚSCULAS
        rd = {str(k).upper(): r[k] for k in r}
        rows.append(rd)
    return rows

# ----------------------- cachés -----------------------
@lru_cache(maxsize=1)
def load_almacenes():
    return _read_dbf("FFALMA.DBF")

@lru_cache(maxsize=1)
def load_articulos():
    return _read_dbf("FFARTI.DBF")

@lru_cache(maxsize=1)
def load_tanques_raw():
    return _read_dbf("FFTANQ.DBF")

@lru_cache(maxsize=1)
def load_calibraciones():
    return _read_dbf("FFCALA.DBF")

def invalidate_caches():
    load_almacenes.cache_clear()
    load_articulos.cache_clear()
    load_tanques_raw.cache_clear()
    load_calibraciones.cache_clear()

def map_articulos_by_key():
    """Devuelve dos índices: por (ALMACEN,CODIGO) y por CODIGO (último visto)"""
    by_ac = {}
    by_cod = {}
    for a in load_articulos():
        alm = _to_str(_first(a, ["ALMACEN","CODALM","ALM"]))
        cod = _to_str(_first(a, ["CODIGO","ARTICULO","CODART"]))
        if alm and cod:
            by_ac[(alm, cod)] = a
        if cod:
            by_cod[cod] = a
    return by_ac, by_cod

def map_almacenes_by_codigo():
    d = {}
    for a in load_almacenes():
        cod = _to_str(_first(a, ["CODIGO","ALMACEN","CODALM"]))
        if cod:
            d[cod] = a
    return d

def articulo_color_hex(almacen, articulo):
    by_ac, by_cod = map_articulos_by_key()
    rec = by_ac.get((almacen, articulo)) or by_cod.get(articulo) or {}
    coln = _first(rec, ["COLORPRODU","COLORPRODUC","COLORPRODUCION","COLORPRODU_"])
    hx = _color_hex_from_number(coln) if coln not in (None, "") else None
    return hx

def normalize_tanque_record(rec):
    """Devuelve un dict unificado para un tanque."""
    almacen = _to_str(_first(rec, ["ALMACEN","CODALM","ALM"]))
    tanque_codigo = _to_str(_first(rec, ["TANQUE","CODIGO","CODTANQ","IDTANQUE"]))
    descripcion = _to_str(_first(rec, ["DESCRI","DESCRIPCION","DESC"]))
    capacidad = _to_float(_first(rec, ["CAPACIDAD","CAPACIDAD_L","CAPACIDADL","CAPACIDAD_T"], 0.0))
    stock = _to_float(_first(rec, ["STOCK","STOCK_L","STOCKACT","STOCKL"], 0.0))
    stock15 = _to_float(_first(rec, ["STOCK15","STOCK_15","STOCK15L"], 0.0))
    temp = _first(rec, ["TEMPULT","TEMPERA","TEMPERATURA","TEMP_ULTIMA"])
    articulo = _to_str(_first(rec, ["ARTICULO","PRODUCTO","CODART","CODPROD","PRODUCTO_ID"]))

    alm_map = map_almacenes_by_codigo()
    alm_nombre = _to_str(_first(alm_map.get(almacen, {}), ["NOMBRE","ALMACEN_NOMBRE","NOM"], ""))

    # Busca datos del artículo
    by_ac, by_cod = map_articulos_by_key()
    art = by_ac.get((almacen, articulo)) or by_cod.get(articulo) or {}
    prod_nombre = _to_str(_first(art, ["DESCRI","DESCRIPCION","NOMBRE","DESCRICOM"], ""))
    color_hex = articulo_color_hex(almacen, articulo) or None

    return {
        "almacen_id": almacen,
        "almacen_nombre": alm_nombre,
        "tanque_codigo": tanque_codigo,
        "tanque_id": f"{almacen}-{tanque_codigo}" if almacen and tanque_codigo else tanque_codigo or almacen,
        "descripcion": descripcion or (f"TANQUE {articulo}" if articulo else "TANQUE"),
        "producto_id": articulo,
        "producto_nombre": prod_nombre,
        "capacidad_l": capacidad,
        "stock_l": stock,
        "stock15_l": stock15,
        "temp_ultima_c": temp if isinstance(temp, (int,float,str)) else None,
        "color_hex": color_hex,
    }

def build_tanques_norm():
    rows = load_tanques_raw()
    norm = [normalize_tanque_record(r) for r in rows] if rows else []

    # Si no hay FFTANQ, intenta construir desde FFARTI como fallback
    if not norm:
        for a in load_articulos():
            alm = _to_str(_first(a, ["ALMACEN","CODALM","ALM"]))
            cod = _to_str(_first(a, ["CODIGO","ARTICULO","CODART"]))
            if not (alm and cod):
                continue
            norm.append({
                "almacen_id": alm,
                "almacen_nombre": "",
                "tanque_codigo": cod,
                "tanque_id": f"{alm}-{cod}",
                "descripcion": f"TANQUE {cod}",
                "producto_id": cod,
                "producto_nombre": _to_str(_first(a, ["DESCRI","DESCRIPCION","NOMBRE"], "")),
                "capacidad_l": _to_float(_first(a, ["CAPACIDAD","CAPACIDAD_L"], 0.0)),
                "stock_l": _to_float(_first(a, ["STOCK","STOCK_L"], 0.0)),
                "stock15_l": _to_float(_first(a, ["STOCK15","STOCK_15"], 0.0)),
                "temp_ultima_c": _first(a, ["TEMPULT","TEMPMED","TEMPERATURA"], None),
                "color_hex": _color_hex_from_number(_first(a, ["COLORPRODU"], 0)),
            })

    return {"count": len(norm), "rows": norm}

# ----------------------- web -----------------------
app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    invalidate = request.args.get("invalidate") == "1"
    if invalidate: invalidate_caches()
    rows = load_almacenes()
    # añade color_hex si hubiera COLORFONDO (aunque por diseño usamos COLORPRODU de artículo)
    out = []
    for r in rows:
        d = {k: r[k] for k in r}
        col = _first(r, ["COLORFONDO","COLOR"])
        if col not in (None, ""):
            d["color_hex"] = _color_hex_from_number(col)
        out.append(d)
    return json_resp({"count": len(out), "rows": out})

@app.route("/api/articulos")
def api_articulos():
    invalidate = request.args.get("invalidate") == "1"
    if invalidate: invalidate_caches()
    rows = load_articulos()
    for r in rows:
        col = _first(r, ["COLORPRODU"])
        r["color_hex"] = _color_hex_from_number(col) if col not in (None, "") else None
    return json_resp({"count": len(rows), "rows": rows})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    invalidate = request.args.get("invalidate") == "1"
    if invalidate: invalidate_caches()
    data = build_tanques_norm()
    # filtros opcionales
    alm = request.args.get("almacen")
    if alm:
        rows = [r for r in data["rows"] if r.get("almacen_id") == alm]
        return json_resp({"count": len(rows), "rows": rows})
    return json_resp(data)

@app.route("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    invalidate = request.args.get("invalidate") == "1"
    if invalidate: invalidate_caches()
    q = _to_str(request.args.get("tanque_id"))
    n = int(request.args.get("n") or 10)
    rows = load_calibraciones()

    # Filtra por ALMACEN o por (ALMACEN-TANQUE)
    filt = []
    alm = None; tan = None
    if "-" in q:
        alm, tan = q.split("-", 1)
    else:
        alm = q

    for r in rows:
        r_alm = _to_str(_first(r, ["ALMACEN","ALM"]))
        r_tan = _to_str(_first(r, ["TANQUE","CODTANQUE","TANQ"]))
        if alm and tan:
            if r_alm == alm and r_tan == tan:
                filt.append(r)
        elif alm:
            if r_alm == alm:
                filt.append(r)

    # Ordena por FECHAMOD desc si existe; si no, por FECHA + HORA
    def keyf(x):
        fm = _first(x, ["FECHAMOD"])
        if isinstance(fm, (datetime, date)):
            return fm
        f = _first(x, ["FECHA"])
        h = _first(x, ["HORA"])
        try:
            if isinstance(f, (datetime,date)):
                fdt = datetime.fromordinal(f.toordinal())
            else:
                fdt = None
            if isinstance(h, str) and h:
                # HH:MM
                hh, mm = (h.split(":") + ["0","0"])[:2]
                hm = datetime.now().replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            else:
                hm = None
            return (fdt or datetime.min).replace(hour=(hm.hour if hm else 0), minute=(hm.minute if hm else 0))
        except Exception:
            return datetime.min

    filt.sort(key=keyf, reverse=True)
    return json_resp({"count": len(filt[:n]), "file": os.path.join(DBF_DIR, "FFCALA.DBF"), "rows": filt[:n]})

# ----------------------- main -----------------------
def _open_browser_when_ready(port):
    import threading, time
    def op():
        time.sleep(0.8)
        try:
            webbrowser.open(f"http://127.0.0.1:{port}/")
        except Exception:
            pass
    threading.Thread(target=op, daemon=True).start()

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT") or 5000)
        _open_browser_when_ready(port)
        debug = bool(int(os.environ.get("FLASK_DEBUG", "0")))
        log.info("Iniciando servidor en http://127.0.0.1:%s", port)
        from werkzeug.serving import run_simple
        # Servidor integrado (simple y robusto para local). No activar auto-reload en exe.
        run_simple("127.0.0.1", port, app, use_reloader=debug, use_debugger=debug, threaded=True)
    except Exception as e:
        err_path = os.path.join(APP_DIR, "error.log")
        with open(err_path, "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat()}  {repr(e)}\n")
        raise

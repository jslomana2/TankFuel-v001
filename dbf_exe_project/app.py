
import os
import sys
import logging
from flask import Flask, jsonify, render_template, request, send_from_directory
from dbfread import DBF
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("app")

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------- Utilidades ----------
def exe_dir():
    # Directorio del ejecutable cuando se empaqueta con PyInstaller
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    # Ejecución normal (no congelado)
    return os.path.dirname(os.path.abspath(__file__))

SEARCH_DIRS = [
    os.getcwd(),
    exe_dir(),
    os.path.join(exe_dir(), "dist"),
    os.path.join(exe_dir(), "dbf_exe_project"),
]

def find_file(fname):
    for d in SEARCH_DIRS:
        p = os.path.join(d, fname)
        if os.path.isfile(p):
            return p
    log.warning("DBF no encontrado: %s", os.path.join(exe_dir(), fname))
    return None

def read_dbf(fname, encoding="latin-1"):
    path = find_file(fname)
    if not path:
        return []
    try:
        rows = [dict(r) for r in DBF(path, load=True, encoding=encoding, char_decode_errors='ignore')]
        return rows
    except Exception as e:
        log.exception("Error leyendo %s: %s", fname, e)
        return []

def safe_float(v, default=0.0):
    try:
        if v is None: return default
        if isinstance(v, (int, float)): return float(v)
        v = str(v).strip().replace(',', '.')
        return float(v) if v else default
    except Exception:
        return default

def color_from_int_to_hex(c):
    """Convierte un entero Windows RGB (BGR) o decimal a #RRGGBB. 
       FFARTI.COLORPRODU suele guardar decimal de COLORREF (BGR)."""
    try:
        c = int(float(c))
        # COLORREF almacena 0x00BBGGRR -> convertimos a RRGGBB
        r = c & 0xFF
        g = (c >> 8) & 0xFF
        b = (c >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return None

# ---------- Rutas ----------
@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    rows = read_dbf("FFALMA.DBF")
    return jsonify({"count": len(rows), "rows": rows})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    tanq = read_dbf("FFTANQ.DBF")
    arti = read_dbf("FFARTI.DBF")
    # Índice por CODIGO de artículo
    idx_arti = {}
    for a in arti:
        code = str(a.get("CODIGO") or a.get("COD_ART") or "").strip()
        if code:
            idx_arti[code] = a

    out = []
    for t in tanq:
        alm = str(t.get("ALMACEN") or t.get("ALM") or "").strip()
        tid = str(t.get("TANQUE") or t.get("CODIGO") or t.get("TANQ") or "").strip()
        prod_code = str(t.get("ARTICULO") or t.get("CODART") or "").strip()
        art = idx_arti.get(prod_code, {})
        # Campos del producto (color y nombre)
        prod_nombre = (art.get("DESCRI") or art.get("DESCRIPCION") or "").strip()
        color_produ = art.get("COLORPRODU") or art.get("COLOR_PRODU") or art.get("COLOR")
        color_hex = color_from_int_to_hex(color_produ) or "#2AA8FF"

        capacidad = safe_float(t.get("CAPACIDAD") or t.get("CAPACIDAD_L") or art.get("CAPACIDAD"))
        # Stock: si el tanque trae stock propio úsalo; si no, usa stock del artículo (mejor que nada)
        stock_l = safe_float(t.get("STOCK") or t.get("STOCK_L"))
        if stock_l == 0.0:
            stock_l = safe_float(art.get("STOCK"))

        temp = t.get("TEMPERA") or t.get("TEMPULT") or art.get("TEMPULT")
        temp_c = None
        try:
            temp_c = float(temp) if temp not in (None, "") else None
        except:
            temp_c = None

        out.append({
            "almacen_id": alm,
            "almacen_nombre": alm,  # el front lo puede sustituir si hace falta
            "tanque_id": f"{alm}-{tid}" if alm and tid else tid or alm,
            "tanque_codigo": tid,
            "producto_id": prod_code,
            "producto_nombre": prod_nombre,
            "capacidad_l": capacidad,
            "stock_l": stock_l,
            "stock15_l": safe_float(t.get("STOCK15") or art.get("STOCK15")),
            "temp_ultima_c": temp_c,
            "color_hex": color_hex
        })

    return jsonify({"count": len(out), "rows": out})

@app.route("/api/calibraciones/ultimas")
def api_calibraciones():
    n = int(request.args.get("n", 10))
    tanque = (request.args.get("tanque") or request.args.get("tanque_id") or "").strip()
    alm = request.args.get("almacen") or ""
    rows = read_dbf("FFCALA.DBF")
    # Ordenamos por FECHAMOD o FECHA descendente
    def parse_dt(r):
        for k in ("FECHAMOD","FECHA","FEC_MOD"):
            v = r.get(k)
            if v in (None, ""): 
                continue
            try:
                if isinstance(v, datetime): 
                    return v
                # Intento convert
                return datetime.fromisoformat(str(v))
            except Exception:
                pass
        return datetime.min
    rows.sort(key=parse_dt, reverse=True)
    # Filtrado si viene tanque/almacen
    if tanque:
        rows = [r for r in rows if str(r.get("TANQUE") or "").strip() == tanque]
    if alm:
        rows = [r for r in rows if str(r.get("ALMACEN") or "").strip() == alm]
    rows = rows[:n]
    return jsonify({"count": len(rows), "file": find_file("FFCALA.DBF") or "", "rows": rows})

# Favicon opcional (no bloquea si no existe)
@app.route('/favicon.ico')
def favicon():
    fav = os.path.join(app.static_folder, "favicon.ico")
    if os.path.exists(fav):
        return send_from_directory(app.static_folder, "favicon.ico")
    return ('', 404)

if __name__ == "__main__":
    addr = "127.0.0.1"
    port = int(os.environ.get("PORT", "5000"))
    log.info("Iniciando servidor en http://%s:%s", addr, port)
    app.run(host=addr, port=port, debug=False)

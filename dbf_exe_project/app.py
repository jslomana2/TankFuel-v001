# -*- coding: utf-8 -*-
import os
import logging
from flask import Flask, jsonify, render_template, send_from_directory
from dbfread import DBF

app = Flask(__name__, template_folder="templates", static_folder="static")

# Logging visible in console and in EXE
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("tanques")

# Resolve DBF directory (same dir as the executable/app.py by default)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DBF_DIR = os.environ.get("DBF_DIR", BASE_DIR)

def _dbf_path(name):
    p = os.path.join(DBF_DIR, name)
    if not os.path.exists(p):
        log.warning("DBF no encontrado: %s", p)
    return p

# Helpers ---------------------------------------------------------------------
def read_table(filename, encoding="latin-1"):
    path = _dbf_path(filename)
    if not os.path.exists(path):
        return []
    try:
        rows = list(DBF(path, ignore_missing_memofile=True, encoding=encoding))
        # Convert to plain dict (dbfread returns OrderedDict-like rows)
        return [dict(r) for r in rows]
    except Exception as e:
        log.exception("Error leyendo %s: %s", filename, e)
        return []

def color_from_articulo(codart, ffarti_rows):
    # Busca color en FFARTI campo COLORPRODU (puede variar capitalización)
    key = str(codart).strip() if codart is not None else ""
    color = None
    for r in ffarti_rows:
        rkey = str(r.get("CODART", r.get("CODIGO", ""))).strip()
        if rkey == key:
            # posibles nombres de campo
            for field in ("COLORPRODU", "COLORPRODUCTO", "COLOR", "COLPROD"):
                if field in r and r[field]:
                    color = str(r[field]).strip()
                    break
            break
    return color

def safe_num(x, default=0.0):
    try:
        if x is None: return default
        if isinstance(x, (int, float)): return float(x)
        s = str(x).replace(",", ".").strip()
        return float(s) if s else default
    except:
        return default

# Routes ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    ffalma = read_table("FFALMA.DBF")
    almacenes = []
    for r in ffalma:
        cod = str(r.get("CODALM", r.get("CODIGO", ""))).strip()
        nombre = str(r.get("NOMBRE", r.get("DESCRIPCION", cod))).strip()
        almacenes.append({"codigo": cod, "nombre": nombre})
    almacenes.sort(key=lambda x: x["codigo"])
    return jsonify({"almacenes": almacenes})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    fftanq = read_table("FFTANQ.DBF")
    ffarti = read_table("FFARTI.DBF")
    # Optional extra table with capacities/levels if present
    ffcala = read_table("FFCALA.DBF")

    # Build quick lookup for capacities by tank code
    cap_map = {}
    for c in ffcala:
        code = str(c.get("CODTANQ", c.get("CODIGO", ""))).strip()
        cap = safe_num(c.get("CAPACIDAD", c.get("CAP", 0)))
        if code:
            cap_map[code] = cap

    out = []
    for r in fftanq:
        codtanq = str(r.get("CODTANQ", r.get("CODIGO", ""))).strip()
        almacen = str(r.get("CODALM", r.get("ALMACEN", ""))).strip()
        producto = str(r.get("CODART", r.get("PRODUCTO", ""))).strip()
        nombre = str(r.get("NOMBRE", r.get("DESCRIPCION", codtanq))).strip()

        # Valores medidos/libro/agua
        medido = safe_num(r.get("MEDIDO", r.get("LITROS", r.get("NIVEL", 0))))
        libro  = safe_num(r.get("LIBRO", r.get("TEORICO", 0)))
        agua   = safe_num(r.get("AGUA", r.get("H2O", 0)))

        cap = safe_num(r.get("CAPACIDAD", 0))
        if cap <= 0 and codtanq in cap_map:
            cap = cap_map.get(codtanq, 0.0)

        pct = (medido / cap * 100.0) if cap > 0 else 0.0

        # Color viene de FFARTI.COLORPRODU (petición del usuario)
        color = color_from_articulo(producto, ffarti) or "#2aa8ff"

        # Estado simple (se puede tunear)
        estado = "ok"
        if pct <= 10 or pct >= 95:
            estado = "bad"
        elif pct <= 20 or pct >= 90:
            estado = "warn"

        out.append({
            "codtanq": codtanq,
            "almacen": almacen,
            "producto": producto,
            "nombre": nombre,
            "capacidad": cap,
            "medido": medido,
            "libro": libro,
            "agua": agua,
            "porcentaje": round(pct, 1),
            "estado": estado,
            "colorProducto": color,
            # extras usados por la UI
            "almacenNombre": almacen,
            "productoNombre": producto,
        })

    # Group by almacén for the UI (but the UI also soporta "ver todos")
    almacenes = {}
    for t in out:
        almacenes.setdefault(t["almacen"], {"codigo": t["almacen"], "nombre": t["almacenNombre"], "tanques": []})
        almacenes[t["almacen"]]["tanques"].append(t)

    payload = {
        "almacenes": list(almacenes.values()),
        "totalTanques": len(out)
    }
    return jsonify(payload)

# Static favicon to avoid 404 noise
@app.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    log.info("Iniciando servidor en http://127.0.0.1:%s", port)
    app.run(host="127.0.0.1", port=port, debug=False)

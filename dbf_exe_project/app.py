import os
import logging
from flask import Flask, jsonify, render_template, send_from_directory, request
from dbfread import DBF
from datetime import datetime

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")

app = Flask(__name__)

# === Config ===
# Donde están los DBF: por defecto, misma carpeta que el EXE/APP.
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DBF_DIR = os.environ.get("DBF_DIR", APP_DIR)

# Nombres ficheros
FFALMA = os.environ.get("FFALMA", "FFALMA.DBF")
FFARTI = os.environ.get("FFARTI", "FFARTI.DBF")
FFTANQ = os.environ.get("FFTANQ", "FFTANQ.DBF")
FFCALA = os.environ.get("FFCALA", "FFCALA.DBF")

def dbf_path(name):
    return os.path.join(DBF_DIR, name)

def safe_json_val(v):
    # Normaliza valores DBF a JSON friendly
    if v is None:
        return ""
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8', errors='ignore')
        except Exception:
            return ""
    if isinstance(v, (datetime,)):
        return v.isoformat()
    return v

def load_dbf(name, lower_keys=False):
    path = dbf_path(name)
    if not os.path.exists(path):
        logging.warning("DBF no encontrado: %s", path)
        return []
    try:
        rows = []
        for rec in DBF(path, char_decode_errors='ignore'):
            d = dict(rec)
            if lower_keys:
                d = { (k.lower() if isinstance(k, str) else k): safe_json_val(v) for k, v in d.items() }
            else:
                d = { k: safe_json_val(v) for k, v in d.items() }
            rows.append(d)
        return rows
    except Exception as e:
        logging.exception("Error leyendo %s: %s", path, e)
        return []

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/favicon.ico")
def favicon():
    # Placeholder
    return "", 404

@app.route("/api/almacenes")
def api_almacenes():
    rows = load_dbf(FFALMA)
    return jsonify({"count": len(rows), "rows": rows})

@app.route("/api/articulos")
def api_articulos():
    rows = load_dbf(FFARTI)
    return jsonify({"count": len(rows), "rows": rows})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    # Unimos FFTANQ con FFARTI (por ALMACEN+CODIGO/ARTICULO) para traer COLORPRODU
    tanques = load_dbf(FFTANQ, lower_keys=True)
    articulos = load_dbf(FFARTI, lower_keys=True)
    arts_index = {}
    for a in articulos:
        key = f"{a.get('almacen','')}-{a.get('codigo','')}"
        arts_index[key] = a

    out = []
    for t in tanques:
        # campos esperados en FFTANQ
        almacen_id = str(t.get("almacen","")).zfill(4) if t.get("almacen") else ""
        producto_id = str(t.get("articulo","")).zfill(4) if t.get("articulo") else ""
        key = f"{almacen_id}-{producto_id}"
        art = arts_index.get(key, {})

        colorprodu = art.get("colorprodu", "") or art.get("colorprodu".upper(), "")
        try:
            # puede venir como float -> int
            colorprodu = int(float(colorprodu)) if colorprodu not in ("", None) else None
        except Exception:
            colorprodu = None

        out.append({
            "almacen_id": almacen_id,
            "almacen_nombre": t.get("almacen_nom", "") or "",
            "capacidad_l": t.get("capacidad", 0) or 0,
            "descripcion": t.get("descri", "") or t.get("descripcion","") or "",
            "producto_id": producto_id,
            "producto_nombre": art.get("descri", "") or art.get("descripvp1","") or "",
            "stock15_l": t.get("stock15", 0) or 0,
            "stock_l": t.get("stock", 0) or 0,
            "tanque_codigo": t.get("tanque", "") or t.get("codigo","") or "",
            "tanque_id": f"{almacen_id}-{t.get('tanque','') or t.get('codigo','')}",
            "temp_ultima_c": t.get("tempera", "") or t.get("tempult", "") or "",
            "color_produ": colorprodu,
        })
    return jsonify({"count": len(out), "rows": out})

@app.route("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    tanque_id = request.args.get("tanque_id", "")
    n = int(request.args.get("n", 10))
    rows = load_dbf(FFCALA, lower_keys=True)
    # si tanque_id = "0001-0003" -> almacen 0001, tanque 0003
    almacen = ""
    tanque = ""
    if "-" in tanque_id:
        almacen, tanque = tanque_id.split("-", 1)
    else:
        tanque = tanque_id
    # Filtrado sencillo
    filt = [r for r in rows if (not almacen or str(r.get("almacen","")).zfill(4)==almacen) and (not tanque or str(r.get("tanque","")).zfill(4)==tanque)]
    # ordenar por FECHAMOD descendente si existe
    try:
        filt.sort(key=lambda r: r.get("fechamod","") or "", reverse=True)
    except Exception:
        pass
    return jsonify({"count": len(filt[:n]), "file": dbf_path(FFCALA), "rows": filt[:n]})

if __name__ == "__main__":
    host = "127.0.0.1"
    port = int(os.environ.get("PORT", 5000))
    logging.info("Iniciando servidor en http://%s:%s", host, port)
    app.run(host=host, port=port, debug=True)

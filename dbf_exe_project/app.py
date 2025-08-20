#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, logging
from datetime import datetime
from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from dbfread import DBF, FieldParser

# ---------- Logging básico ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# ---------- Paths seguros (PyInstaller: _MEIPASS) ----------
def resource_path(relpath: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, relpath)

# En exe: carpeta del ejecutable; en desarrollo: la del archivo
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
# 🔴 IMPORTANTE: DBFs en la MISMA carpeta que el .exe (o app.py en dev)
DBF_DIR = BASE_DIR

TEMPLATES_DIR = resource_path("templates")
STATIC_DIR = resource_path("static")

# ---------- dbfread: ignorar memos y bytes seguros ----------
class SafeFieldParser(FieldParser):
    def parseM(self, field, data):
        # Ignora campos memo / blob
        return None

def _safe_val(v):
    if v is None:
        return ""
    if isinstance(v, bytes):
        try:
            return v.decode("latin-1").strip()
        except Exception:
            return v.hex()
    if isinstance(v, datetime):
        return v.isoformat()
    return v

def read_dbf_rows(file_name: str):
    path = os.path.join(DBF_DIR, file_name)
    if not os.path.exists(path):
        logging.warning("DBF no encontrado: %s", path)
        return [], path
    try:
        table = DBF(path, load=True, ignore_missing_memofile=True, parserclass=SafeFieldParser, lowernames=False)
        rows = []
        for rec in table:
            rows.append({k: _safe_val(v) for k, v in dict(rec).items()})
        return rows, path
    except Exception as e:
        logging.exception("Error leyendo %s", path)
        return [], path

# ---------- Flask ----------
app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.wsgi_app = ProxyFix(app.wsgi_app)

@app.get("/")
def index():
    return render_template("sondastanques_mod.html")

@app.get("/api/where")
def api_where():
    files = ["FFALMA.DBF", "FFARTI.DBF", "FFCALA.DBF", "FFTANQ.DBF"]
    out = {}
    for f in files:
        p = os.path.join(DBF_DIR, f)
        out[f.lower()] = {
            "exists": os.path.exists(p),
            "file": f,
            "resolved_path": p,
            "size_bytes": os.path.getsize(p) if os.path.exists(p) else None
        }
    return jsonify(out)

@app.get("/api/almacenes")
def api_almacenes():
    rows, _ = read_dbf_rows("FFALMA.DBF")
    return jsonify({"rows": rows, "count": len(rows)})

@app.get("/api/articulos")
def api_articulos():
    rows, _ = read_dbf_rows("FFARTI.DBF")
    return jsonify({"rows": rows, "count": len(rows)})

def _map_articulos():
    rows, _ = read_dbf_rows("FFARTI.DBF")
    m = {}
    for r in rows:
        cod = str(r.get("CODIGO") or "").strip()
        if cod:
            m[cod] = r
    return m

def _map_almacenes():
    rows, _ = read_dbf_rows("FFALMA.DBF")
    m = {}
    for r in rows:
        cod = str(r.get("CODIGO") or "").strip()
        if cod:
            m[cod] = r
    return m

@app.get("/api/tanques_norm")
def api_tanques_norm():
    tanques, path_t = read_dbf_rows("FFTANQ.DBF")
    if not tanques:
        return jsonify({"rows": [], "count": 0, "file": path_t})
    art_map = _map_articulos()
    alm_map = _map_almacenes()
    out = []
    for t in tanques:
        alm = str(t.get("ALMACEN") or "").strip()
        cod = str(t.get("CODIGO") or "").strip()
        if not alm or not cod:
            continue
        tid = f"{alm}-{cod}"
        art_code = str(t.get("ARTICULO") or "").strip()
        art = art_map.get(art_code)
        alm_obj = alm_map.get(alm)
        out.append({
            "tanque_id": tid,
            "almacen_id": alm,
            "tanque_codigo": cod,
            "descripcion": t.get("DESCRI") or "",
            "capacidad_l": t.get("CAPACIDAD") or 0,
            "stock_l": t.get("STOCK") or 0,
            "stock15_l": t.get("STOCK15") or 0,
            "producto_id": art_code,
            "producto_nombre": (art.get("DESCRI") if art else ""),
            "almacen_nombre": (alm_obj.get("NOMBRE") if alm_obj else ""),
            "temp_ultima_c": t.get("TEMPULT") or "",
        })
    return jsonify({"rows": out, "count": len(out)})

@app.get("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    n = request.args.get("n", default=10, type=int)
    tanque_id = request.args.get("tanque_id", default="", type=str)
    alm_filter, tank_filter = None, None
    if "-" in tanque_id:
        x = tanque_id.split("-", 1)
        alm_filter, tank_filter = x[0].strip(), x[1].strip()
    rows, path_c = read_dbf_rows("FFCALA.DBF")
    if alm_filter:
        rows = [r for r in rows if str(r.get("ALMACEN") or "").strip() == alm_filter]
    if tank_filter:
        rows = [r for r in rows if str(r.get("TANQUES") or "").strip() == tank_filter]
    def _key(r):
        return (r.get("FECHA") or "", r.get("HORA") or "")
    rows = sorted(rows, key=_key)[-n:] if n else rows
    return jsonify({"rows": rows, "count": len(rows), "file": path_c})

# Fallback estáticos en raíz por compatibilidad
@app.get("/sondastanques_mod.css")
def css_root():
    return send_from_directory(STATIC_DIR, "sondastanques_mod.css")

@app.get("/sondastanques_mod.js")
def js_root():
    return send_from_directory(STATIC_DIR, "sondastanques_mod.js")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    logging.info(f"Servidor en http://127.0.0.1:{port} (DBFs en {DBF_DIR})")
    app.run(host="127.0.0.1", port=port, debug=False)

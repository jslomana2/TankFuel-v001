#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROCONSI – Tanques · Vista avanzada
Backend Flask para servir UI y exponer endpoints contra DBF locales.
Requisitos: Flask, dbfread, pandas (opcional para CSV), reportlab (opcional para PDF)
Coloca los DBF (FFALMA.DBF, FFARTI.DBF, FFTANQ.DBF, FFCALA.DBF) EN LA MISMA CARPETA QUE ESTE EXE/APP.
"""

import os, sys, json, math, datetime as dt
from flask import Flask, jsonify, render_template, send_from_directory, request, abort

# ---- Util: path base (donde está el exe o el script) ----
BASE_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))

# ---- Safe helpers ----
def safe_num(v, default=0.0):
    try:
        if v in (None, "", " "): return default
        if isinstance(v, (int, float)): return float(v)
        s = str(v).strip().replace(",", ".")
        return float(s) if s else default
    except Exception:
        return default

def safe_str(v, default=""):
    try:
        if v is None: return default
        s = str(v).strip()
        return s if s else default
    except Exception:
        return default

def wincolor_to_hex(dec):
    """
    Convierte un entero Windows BGR a #RRGGBB.
    Ej: 8454143 => #33CCFF aprox (dependiendo del dato origen).
    Si falla, devuelve None.
    """
    try:
        dec = int(float(dec))
        if dec < 0: dec = (dec + (1<<32)) % (1<<32)
        b = (dec >> 16) & 0xFF
        g = (dec >> 8) & 0xFF
        r = dec & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return None

# ---- Lectura DBF (perezosa) ----
def read_dbf_rows(filename):
    path = os.path.join(BASE_DIR, filename)
    if not os.path.exists(path):
        return []
    try:
        from dbfread import DBF
        rows = [dict(r) for r in DBF(path, load=True, char_decode_errors='ignore')]
        return rows
    except Exception as e:
        print(f"[WARN] No se pudo leer {filename}: {e}")
        return []

# Cache primitiva en memoria (refresco manual con ?nocache=1 si quieres)
_cache = {}
def get_cached(name, loader):
    if request.args.get("nocache") == "1" or name not in _cache:
        _cache[name] = loader()
    return _cache[name]

# ---- Endpoints ----
@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    rows = get_cached("FFALMA", lambda: read_dbf_rows("FFALMA.DBF"))
    return jsonify({"count": len(rows), "rows": rows})

@app.route("/api/articulos")
def api_articulos():
    rows = get_cached("FFARTI", lambda: read_dbf_rows("FFARTI.DBF"))
    return jsonify({"count": len(rows), "rows": rows})

@app.route("/api/tanques_raw")
def api_tanques_raw():
    rows = get_cached("FFTANQ", lambda: read_dbf_rows("FFTANQ.DBF"))
    return jsonify({"count": len(rows), "rows": rows})

@app.route("/api/calibraciones/ultimas")
def api_cal_ultimas():
    tanque = request.args.get("tanque_id", "").strip()
    n = int(request.args.get("n", 10))
    rows = get_cached("FFCALA", lambda: read_dbf_rows("FFCALA.DBF"))
    # Filtro aproximado: por TANQUE y/o ALMACEN si llega "0001-0003" → split
    if "-" in tanque:
        alm, tk = tanque.split("-", 1)
        f = [r for r in rows if safe_str(r.get("ALMACEN")) == alm and safe_str(r.get("TANQUE")) == tk]
    else:
        f = [r for r in rows if safe_str(r.get("TANQUE")) == tanque or safe_str(r.get("ID")) == tanque]
    f = sorted(f, key=lambda r: (safe_str(r.get("FECHAMOD")), safe_str(r.get("HORA"))), reverse=True)[:n]
    return jsonify({"count": len(f), "file": os.path.join(BASE_DIR, "FFCALA.DBF"), "rows": f})

@app.route("/api/tanques_norm")
def api_tanques_norm():
    """
    Normaliza la información relevante de tanques + join con artículos para coger el COLOR del producto desde FFARTI.COLORPRODU.
    """
    tanques = get_cached("FFTANQ", lambda: read_dbf_rows("FFTANQ.DBF"))
    articulos = get_cached("FFARTI", lambda: read_dbf_rows("FFARTI.DBF"))
    # Indices por (ALMACEN, CODIGO) y por CODIGO a secas (fallback)
    idx_art_alm = {}
    idx_art = {}
    for a in articulos:
        cod = safe_str(a.get("CODIGO"))
        alm = safe_str(a.get("ALMACEN"))
        idx_art[(cod)] = a
        if alm:
            idx_art_alm[(alm, cod)] = a

    out = []
    for t in tanques:
        alm = safe_str(t.get("ALMACEN"))
        desc = safe_str(t.get("DESCRIPCION", t.get("DESCRI", "")))
        prod_id = safe_str(t.get("PRODUCTO", t.get("ARTICULO", "")))
        prod_name = safe_str(t.get("DESCPROD", t.get("DESCRI_PROD", "")))
        cap = safe_num(t.get("CAPACIDAD"))
        stock = safe_num(t.get("STOCK"))
        stock15 = safe_num(t.get("STOCK15"))
        temp = t.get("TEMP")
        if temp in ("", None): temp = ""
        tanque_codigo = safe_str(t.get("TANQUE", t.get("CODIGO", "")))
        tanque_id = f"{alm}-{tanque_codigo}" if alm and tanque_codigo else safe_str(t.get("ID"), "")
        # JOIN color desde FFARTI por (almacen, producto) → si no, por producto
        a = idx_art_alm.get((alm, prod_id)) or idx_art.get(prod_id) or {}
        color_dec = a.get("COLORPRODU") or a.get("COLORPRODU".upper()) or a.get("COLORPRODU".lower())
        color_hex = wincolor_to_hex(color_dec) if color_dec not in (None, "", 0) else None

        out.append({
            "almacen_id": alm,
            "almacen_nombre": "",  # cliente puede completar con FFALMA si hace falta
            "capacidad_l": cap,
            "descripcion": desc,
            "producto_id": prod_id,
            "producto_nombre": prod_name if prod_name else safe_str(a.get("DESCRI")),
            "stock15_l": stock15,
            "stock_l": stock,
            "tanque_codigo": tanque_codigo,
            "tanque_id": tanque_id,
            "temp_ultima_c": temp,
            "color_hex": color_hex,  # << NUEVO
        })
    return jsonify({"count": len(out), "rows": out})

# ---- Archivos grandes (descargas) opcionales ----
@app.route("/download/<path:filename>")
def download(filename):
    return send_from_directory(BASE_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Iniciando servidor en http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)

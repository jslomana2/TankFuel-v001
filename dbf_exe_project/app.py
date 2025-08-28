
import os
import math
from datetime import datetime
from flask import Flask, jsonify, render_template, request
from dbfread import DBF

APP_TITLE = "PROCONSI – SondaTanques (HEADER_WHITE)"
ENCODING = "latin-1"

app = Flask(__name__, static_url_path='/static', static_folder='static', template_folder='templates')

def dbf_path(name):
    # DBFs are expected alongside the EXE, but in dev they're next to app.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # If running as bundled EXE (PyInstaller), _MEIPASS may exist
    if getattr(sys := globals().get("sys", None), "_MEIPASS", None):
        base_dir = os.path.dirname(sys.executable)
    candidate = os.path.join(base_dir, name)
    return candidate

def read_dbf(name):
    path = dbf_path(name)
    if not os.path.exists(path):
        return []
    try:
        tbl = DBF(path, ignore_missing_memofile=True, encoding=ENCODING, char_decode_errors='ignore')
        return [dict(r) for r in tbl]
    except Exception as e:
        # fail-soft
        return []

def safe(v, default="–"):
    if v in (None, "", " ", "  "):
        return default
    return v

def pct(capacidad, cantidad):
    try:
        c = float(cantidad or 0.0)
        cap = float(capacidad or 0.0)
        if cap <= 0:
            return 0
        p = max(0.0, min(100.0, (c / cap) * 100.0))
        return round(p, 1)
    except Exception:
        return 0

def status_from_pct(p):
    # Mapping requested by Javier:
    # 0–20%: red warning icon + label "Bajo"
    # 21–50%: orange circle + "Medio"
    # 51–90%: green circle + "Alto"
    # 91–100%: light-green circle + "Muy lleno"
    if p <= 20:
        return {"key":"low", "label":"Bajo", "shape":"warning", "color":"#e53935"}  # red
    if 21 <= p <= 50:
        return {"key":"mid", "label":"Medio", "shape":"circle", "color":"#fb8c00"}  # orange
    if 51 <= p <= 90:
        return {"key":"high", "label":"Alto", "shape":"circle", "color":"#2e7d32"}  # green
    return {"key":"full", "label":"Muy lleno", "shape":"circle", "color":"#66bb6a"} # light green

def load_lookup():
    # FFALMA: almacenes
    almacenes = read_dbf('FFALMA.DBF')
    Alm = {str(a.get("ALMACEN")).strip(): a for a in almacenes if a.get("ALMACEN") is not None}

    # FFARTI: articulos (productos)
    articulos = read_dbf('FFARTI.DBF')
    Art = {str(a.get("CODIGO")).strip(): a for a in articulos if a.get("CODIGO") is not None}

    return Alm, Art

def normalize_tank_rows():
    # FFTANQ: tanques (IDs, capacidades, almacén, artículo)
    tanques = read_dbf('FFTANQ.DBF')
    # FFCALA: calibraciones/lecturas recientes por tanque
    calibras = read_dbf('FFCALA.DBF')

    Alm, Art = load_lookup()

    # Última lectura por tanque -> cantidad actual
    last_by_tanque = {}
    for c in calibras:
        tid = str(c.get("TANQUE") or c.get("IDTANQUE") or c.get("CODTANQ") or "").strip()
        if not tid:
            continue
        # pick last by FECHA/HORA if available
        key = (c.get("FECHA"), c.get("HORA"))
        if tid not in last_by_tanque or key > last_by_tanque[tid]["_key"]:
            c2 = dict(c)
            c2["_key"] = key
            last_by_tanque[tid] = c2

    rows = []
    for t in tanques:
        tanque_id = str(t.get("TANQUE") or t.get("IDTANQUE") or t.get("CODTANQ") or "").strip()
        cod_alm = str(t.get("ALMACEN") or "").strip()
        cod_art = str(t.get("CODARTI") or t.get("ARTICULO") or "").strip()

        cap = t.get("CAPACIDAD") or t.get("CAPAC") or 0
        cap = float(cap or 0)

        lectura = last_by_tanque.get(tanque_id, {})
        cantidad = lectura.get("CANTIDAD") or lectura.get("VOLUMEN") or lectura.get("VOL") or t.get("STOCK") or 0
        cantidad = float(cantidad or 0)

        por = pct(cap, cantidad)
        st = status_from_pct(por)

        alm = Alm.get(cod_alm, {})
        art = Art.get(cod_art, {})

        rows.append({
            "tanque_id": tanque_id,
            "almacen": cod_alm,
            "almacen_descr": safe(alm.get("DESCRI") or alm.get("NOMBRE")),
            "articulo": cod_art,
            "articulo_descr": safe(art.get("DESCRI") or art.get("NOMBRE")),
            "capacidad": cap,
            "cantidad": round(cantidad, 2),
            "porcentaje": por,
            "status": st,  # includes label, color, shape
        })
    return rows

@app.route("/")
def home():
    return render_template("sondastanques_mod.html", app_title=APP_TITLE)

@app.route("/api/tanques_norm")
def api_tanques_norm():
    almacen = request.args.get("almacen", "").strip()
    rows = normalize_tank_rows()
    if almacen:
        rows = [r for r in rows if str(r["almacen"]) == almacen]
    # sort by almacen, then tanque
    rows.sort(key=lambda r: (str(r["almacen"]), str(r["tanque_id"])))
    return jsonify(rows)

@app.route("/api/almacenes")
def api_almacenes():
    Alm, _ = load_lookup()
    out = []
    for k, a in Alm.items():
        out.append({"almacen": k, "descr": (a.get("DESCRI") or a.get("NOMBRE") or "–")})
    out.sort(key=lambda r: r["almacen"])
    return jsonify(out)

@app.route("/api/articulos")
def api_articulos():
    _, Art = load_lookup()
    out = []
    for k, a in Art.items():
        out.append({"codigo": k, "descr": (a.get("DESCRI") or a.get("NOMBRE") or "–")})
    out.sort(key=lambda r: r["codigo"])
    return jsonify(out)

@app.route("/api/calibraciones/ultimas")
def api_calib_ultimas():
    tanque_id = request.args.get("tanque_id", "").strip()
    n = int(request.args.get("n", 30))
    calibras = read_dbf('FFCALA.DBF')
    rows = []
    for c in calibras:
        tid = str(c.get("TANQUE") or c.get("IDTANQUE") or c.get("CODTANQ") or "").strip()
        if tanque_id and tid != tanque_id:
            continue
        fecha = c.get("FECHA")
        hora = c.get("HORA")
        vol = c.get("CANTIDAD") or c.get("VOLUMEN") or c.get("VOL")
        if isinstance(fecha, (int, float)):
            fecha_str = str(fecha)
        else:
            fecha_str = str(fecha or "")
        rows.append({
            "tanque_id": tid,
            "fecha": fecha_str,
            "hora": str(hora or ""),
            "volumen": float(vol or 0),
        })
    # order by fecha/hora descending and take n
    rows.sort(key=lambda r: (r["fecha"], r["hora"]), reverse=True)
    return jsonify(rows[:n])

@app.route("/api/where")
def api_where():
    # Simple generic filter over tanques_norm
    q = request.args.get("q", "").strip().lower()
    rows = normalize_tank_rows()
    if q:
        def ok(r):
            blob = " ".join(str(v) for v in r.values()).lower()
            return q in blob
        rows = [r for r in rows if ok(r)]
    return jsonify(rows)

if __name__ == "__main__":
    print("Iniciando servidor en http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)

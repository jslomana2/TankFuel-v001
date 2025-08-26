import os
from flask import Flask, jsonify, render_template, request
from datetime import datetime
from dbfread import DBF

app = Flask(__name__, template_folder="templates", static_folder="static")

def to_float(v):
    try:
        if v in (None, ""): return None
        return float(v)
    except Exception:
        return None

def to_str(v):
    return "" if v is None else str(v).strip()

def dbf_path(name):
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(here, f"{name}.DBF")

def safe_dbf(name):
    p = dbf_path(name)
    if os.path.exists(p):
        return DBF(p, ignore_missing_memofile=True, encoding="latin-1")
    return None

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

@app.get("/api/almacenes")
def api_almacenes():
    t = safe_dbf("FFALMA")
    out = []
    if t:
        for r in t:
            out.append({
                "id": to_str(r.get("ALMACEN")),
                "nombre": to_str(r.get("NOMBRE") or r.get("DESCRI") or r.get("DESCRIPCION") or "--"),
            })
    return jsonify(out)

@app.get("/api/articulos")
def api_articulos():
    t = safe_dbf("FFARTI")
    out = []
    if t:
        for r in t:
            out.append({
                "articulo": to_str(r.get("ARTICULO") or r.get("CODIGO")),
                "descripcion": to_str(r.get("DESCRI") or r.get("DESCRIPCION") or "--"),
                "color": r.get("COLORPRODU") or r.get("COLOR") or None,
                "colorRGB": r.get("COLORRGB") or None,
            })
    return jsonify(out)

@app.get("/api/tanques_norm")
def api_tanques_norm():
    almacen = request.args.get("almacen")
    t_tq = safe_dbf("FFTANQ")
    t_ar = safe_dbf("FFARTI")

    art_map = {}
    if t_ar:
        for a in t_ar:
            key = to_str(a.get("ARTICULO") or a.get("CODIGO"))
            art_map[key] = {
                "producto": to_str(a.get("DESCRI") or a.get("DESCRIPCION") or "--"),
                "color": a.get("COLORPRODU") or a.get("COLOR") or None,
                "colorRGB": a.get("COLORRGB") or None,
            }

    out = []
    if t_tq:
        for r in t_tq:
            alm = to_str(r.get("ALMACEN"))
            if almacen and alm.upper() != almacen.upper():
                continue
            nombre = to_str(r.get("NOMBRE") or r.get("CODIGO") or "TANQUE")
            articulo = to_str(r.get("ARTICULO"))
            cap = to_float(r.get("CAPACIDAD")) or 0.0
            stock = to_float(r.get("STOCK15") or r.get("STOCK") or 0.0) or 0.0
            agua = to_float(r.get("AGUA") or r.get("ALTAGUA") or 0.0) or 0.0
            temp = to_float(r.get("TEMP") or r.get("TEMPERATURA"))
            prod = art_map.get(articulo, {})

            out.append({
                "almacen": alm,
                "nombre": nombre,
                "producto": prod.get("producto", "--"),
                "color": prod.get("color"),
                "colorRGB": prod.get("colorRGB"),
                "capacidad": cap,
                "volumen": stock,
                "alturaAgua": agua,
                "temperatura": temp,
                "status": "ok",
                "spark": [],
            })
    return jsonify(out)

@app.get("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    tanque_id = request.args.get("tanque_id", "")
    n = int(request.args.get("n", 50))
    t = safe_dbf("FFCALA")
    rows = []
    if t:
        tmp = []
        for r in t:
            alm = to_str(r.get("ALMACEN"))
            tq = to_str(r.get("TANQUE") or r.get("NOMBRE"))
            key = f"{alm}|{tq}"
            if tanque_id and key.upper() != tanque_id.upper():
                continue

            fecha = r.get("FECHA") or r.get("FECLECT") or None
            if isinstance(fecha, datetime):
                fecha_txt = fecha.strftime("%Y-%m-%d %H:%M")
            else:
                fecha_txt = to_str(fecha)

            tmp.append({
                "fecha": fecha_txt,
                "medido": to_float(r.get("MEDIDO")) or 0.0,
                "libro": to_float(r.get("LIBRO") or r.get("STOCK")) or 0.0,
                "almacen": alm,
                "tanque": tq,
            })
        tmp.sort(key=lambda x: x["fecha"])
        rows = tmp[-n:]
    return jsonify(rows)

@app.get("/api/where")
def api_where():
    table = (request.args.get("table") or "FFTANQ").upper()
    field = request.args.get("field") or ""
    value = request.args.get("value") or ""
    t = safe_dbf(table)
    out = []
    if t and field:
        for r in t:
            if to_str(r.get(field)).upper() == to_str(value).upper():
                out.append({k: ("" if v is None else v) for k, v in r.items()})
    return jsonify(out)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)

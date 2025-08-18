#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, threading, webbrowser, json, time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, render_template, Response
from werkzeug.middleware.proxy_fix import ProxyFix

def resource_path_multi(subdir: str) -> str:
    """
    Busca 'subdir' (templates/static) en:
    1) MEIPASS (si está embebido)
    2) EXE_DIR (carpeta junto al .exe)
    3) CWD (directorio actual)
    Retorna la primera ruta existente; si ninguna existe, devuelve la de MEIPASS/CWD por defecto.
    """
    bases = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass: bases.append(meipass)
    if getattr(sys, "frozen", False):
        bases.append(os.path.dirname(sys.executable))  # exe dir
    bases.append(os.path.abspath("."))  # cwd
    for b in bases:
        p = os.path.join(b, subdir)
        if os.path.exists(p):
            return p
    # fallback
    return os.path.join(meipass or os.path.abspath("."), subdir)

TEMPLATES_DIR = resource_path_multi("templates")
STATIC_DIR = resource_path_multi("static")
DATA_DIR = resource_path("data")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.wsgi_app = ProxyFix(app.wsgi_app)

def _import_dbfread():
    try:
        from dbfread import DBF  # type: ignore
        return DBF
    except Exception as e:
        raise RuntimeError("No se pudo importar 'dbfread'. Instala dependencias con 'pip install -r requirements.txt'.")

def read_dbf(file_path, encoding="latin-1", lower_names=True, limit=None):
    from dbfread import DBF  # lazy import para evitar fallo de import en tooling
    table = DBF(file_path, load=True, encoding=encoding, lowernames=lower_names)
    rows = [dict(r) for r in table]
    if limit is not None:
        rows = rows[:int(limit)]
    return rows

ENDPOINTS = {
    "tanques": "FFTANQ.DBF",
    "almacenes": "FFALMA.DBF",
    "articulos": "FFARTI.DBF",
    "calibraciones": "FFCALA.DBF",
}

# Alias de rutas -> clave canónica de ENDPOINTS
ALIASES = {
    "calados": "calibraciones",
    "lecturas": "calibraciones",
    "calibraciones": "calibraciones",
    "tanque": "tanques",
    "tanques": "tanques",
    "almacen": "almacenes",
    "almacenes": "almacenes",
    "articulo": "articulos",
    "articulos": "articulos",
}

def resolve_data_file(fname: str) -> str:
    """
    Busca el archivo de datos en varios lugares, en este orden:
    0) FUEL_DB_DIR si está definido en el entorno
    1) <MEIPASS>/data/fname  (recursos embebidos si existieran)
    2) <EXE_DIR>/data/fname  (carpeta 'data' junto al .exe)
    3) <EXE_DIR>/fname       (DBF directamente al lado del .exe)
    4) <CWD>/data/fname      (carpeta 'data' en el directorio actual)
    5) <CWD>/fname           (DBF directamente en el directorio actual)
    """
    env_dir = os.environ.get('FUEL_DB_DIR')
    if env_dir:
        p = os.path.join(env_dir, fname)
        if os.path.exists(p):
            return p
    candidate = os.path.join(DATA_DIR, fname)
    if os.path.exists(candidate):
        return candidate
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath('.')
    for p in (os.path.join(exe_dir, 'data', fname), os.path.join(exe_dir, fname)):
        if os.path.exists(p):
            return p
    cwd = os.getcwd()
    for p in (os.path.join(cwd, 'data', fname), os.path.join(cwd, fname)):
        if os.path.exists(p):
            return p
    return candidate

def filter_rows(rows, fields=None, q=None, where=None):
    if where:
        for k, v in where.items():
            rows = [r for r in rows if str(r.get(k, "")).strip() == v]
    if q:
        ql = q.lower()
        def match(r):
            for val in r.values():
                try:
                    if ql in str(val).lower():
                        return True
                except Exception:
                    pass
            return False
        rows = [r for r in rows if match(r)]
    if fields:
        rows = [{k: r.get(k) for k in fields} for r in rows]
    return rows

def color_decimal_to_hex(n, assume_bgr=True):
    try:
        n = int(n)
    except Exception:
        return None
    r = (n & 0xFF)
    g = (n >> 8) & 0xFF
    b = (n >> 16) & 0xFF
    if assume_bgr:
        r, b = b, r
    return f"#{r:02X}{g:02X}{b:02X}"

def _load_table_dict(dbf_name):
    path = resolve_data_file(dbf_name)
    rows = []
    if os.path.exists(path):
        rows = read_dbf(path)
        rows = [{(k.lower() if isinstance(k,str) else k): v for k,v in r.items()} for r in rows]
    return rows, path

def resolve_product_details(almacen_code, articulo_code):
    # 1) FFALMA por (almacen_code, articulo_code) si existiera
    alma_rows, _ = _load_table_dict(ENDPOINTS["almacenes"])
    if alma_rows:
        for r in alma_rows:
            if r.get("codigo") == almacen_code or r.get("almacen") == almacen_code:
                art = r.get("articulo") or r.get("codart") or r.get("producto") or None
                if art and str(art).strip() == str(articulo_code).strip():
                    name = r.get("descri") or r.get("nombre") or None
                    color_dec = r.get("colorprodu") or r.get("color") or None
                    color_hex = color_decimal_to_hex(color_dec) if color_dec is not None else None
                    if name or color_hex:
                        return {"product_name": name, "product_color_hex": color_hex}
    # 2) FFARTI por CODIGO
    arti_rows, _ = _load_table_dict(ENDPOINTS["articulos"])
    if arti_rows:
        for r in arti_rows:
            if str(r.get("codigo")).strip() == str(articulo_code).strip():
                name = r.get("descri") or r.get("nombre") or None
                color_dec = r.get("colorprodu") or r.get("color") or None
                color_hex = color_decimal_to_hex(color_dec) if color_dec is not None else None
                return {"product_name": name, "product_color_hex": color_hex}
    return {"product_name": None, "product_color_hex": None}

def _find_field(candidates, keys_lower):
    for c in candidates:
        if c in keys_lower:
            return c
    return None

def _to_datetime(row):
    keys = {k: v for k, v in row.items()}
    lower = {k.lower(): k for k in keys}
    fecha_k = _find_field(["fecha","fch","fec","fechahora","timestamp","ts","f_reg"], lower)
    hora_k = _find_field(["hora","hr"], lower)
    if fecha_k and lower.get(fecha_k) in keys:
        val = keys[lower[fecha_k]]
        if hora_k and lower.get(hora_k) in keys:
            hval = keys[lower[hora_k]]
            try:
                if isinstance(val, datetime):
                    base_dt = val
                else:
                    base_dt = datetime.fromisoformat(str(val).replace("Z","").replace("/", "-"))
                if isinstance(hval, datetime):
                    return hval
                parts = str(hval).split(":")
                hh, mm, ss = int(parts[0]), int(parts[1]) if len(parts)>1 else 0, int(parts[2]) if len(parts)>2 else 0
                return base_dt.replace(hour=hh, minute=mm, second=ss)
            except Exception:
                pass
        try:
            if isinstance(val, datetime):
                return val
            s = str(val).strip().replace("/", "-")
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y %H:%M:%S", "%d-%m-%Y"):
                try:
                    return datetime.strptime(s, fmt)
                except Exception:
                    continue
        except Exception:
            pass
    return None

def _infer_tanque_key(rows):
    if not rows:
        return None
    keys_lower = [k.lower() for k in rows[0].keys()]
    for cand in ["codtanque","idtanque","tanque","cod_tanque","id_tanque","ctanque","ctanq","tanq","nombre"]:
        if cand in keys_lower:
            return cand
    for k in keys_lower:
        if "tan" in k:
            return k
    return None

def _sort_by_dt(rows):
    decorated = []
    for r in rows:
        dt = _to_datetime(r)
        decorated.append((dt, r))
    decorated.sort(key=lambda x: (x[0] is None, x[0]))
    return [r for _, r in decorated]

def parse_tanque_selector(req):
    tid = req.args.get("tanque_id") or req.args.get("id") or None
    tanque = req.args.get("tanque")
    almacen = req.args.get("almacen")
    if tid and "-" in tid:
        a, c = tid.split("-", 1)
        return a.strip(), c.strip()
    if tanque and almacen:
        return str(almacen).strip(), str(tanque).strip()
    if tanque and "-" in tanque:
        a, c = tanque.split("-", 1)
        return a.strip(), c.strip()
    return None, None

@app.get("/api/tables")
def api_tables():
    return jsonify([{"name": k, "file": v} for k, v in ENDPOINTS.items()])

@app.get("/api/<name>")
def api_table(name):
    if name in ALIASES:
        name = ALIASES[name]
    if name not in ENDPOINTS:
        return jsonify({"error": f"Tabla '{name}' no está definida.", "available": list(ENDPOINTS.keys()), "aliases": list(ALIASES.keys())}), 404
    fname = ENDPOINTS[name]
    fpath = resolve_data_file(fname)
    exists = os.path.exists(fpath)
    if not exists:
        return jsonify({"error": f"No se encontró el archivo {fname}.", "resolved_path": fpath, "exists": False}), 404

    limit = request.args.get("limit", type=int)
    fields_param = request.args.get("fields")
    fields = [f.strip().lower() for f in fields_param.split(",")] if fields_param else None
    q = request.args.get("q")
    where_param = request.args.get("where")
    where = None
    if where_param:
        try:
            where = json.loads(where_param)
        except Exception:
            return jsonify({"error": "El parámetro 'where' debe ser JSON válido"}), 400

    try:
        rows = read_dbf(fpath, limit=limit)
        rows = [{(k.lower() if isinstance(k, str) else k): v for k, v in r.items()} for r in rows]
        rows = filter_rows(rows, fields=fields, q=q, where=where)
        return jsonify({"table": name, "file": fname, "resolved_path": fpath, "exists": True, "count": len(rows), "rows": rows})
    except Exception as e:
        return jsonify({"error": str(e), "resolved_path": fpath, "exists": True}), 500

@app.get("/api/tanques_norm")
def api_tanques_norm():
    fpath = resolve_data_file(ENDPOINTS["tanques"])
    if not os.path.exists(fpath):
        return jsonify({"error": "No se encontró FFTANQ.DBF", "resolved_path": fpath}), 404
    rows = read_dbf(fpath)
    rows = [{(k.lower() if isinstance(k,str) else k): v for k,v in r.items()} for r in rows]

    out = []
    for r in rows:
        alm = str(r.get("almacen") or r.get("codalmacen") or "").strip()
        cod = str(r.get("codigo") or r.get("codtanque") or r.get("tanques") or "").strip()
        if not alm or not cod:
            continue
        tanque_id = f"{alm}-{cod}"
        descri = r.get("descri") or r.get("descripcion") or None
        cap = r.get("capacidad")
        stock = r.get("stock")
        stock15 = r.get("stock15")
        art = r.get("articulo")
        tempult = r.get("tempult")

        prod = resolve_product_details(alm, art) if art is not None else {"product_name": None, "product_color_hex": None}

        out.append({
            "tanque_id": tanque_id,
            "almacen_id": alm,
            "tanque_codigo": cod,
            "descripcion": descri,
            "capacidad_l": cap,
            "stock_l": stock,
            "stock15_l": stock15,
            "producto_id": art,
            "producto_nombre": prod.get("product_name"),
            "producto_color": prod.get("product_color_hex"),
            "temp_ultima_c": tempult,
        })
    return jsonify({"table": "tanques", "file": ENDPOINTS["tanques"], "resolved_path": fpath, "count": len(out), "rows": out})

@app.get("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    n = request.args.get("n", default=10, type=int)
    almacen_code, tanque_code = parse_tanque_selector(request)
    if not tanque_code:
        legacy = request.args.get("tanque")
        if legacy:
            tanque_code = str(legacy).strip()

    fpath = resolve_data_file(ENDPOINTS["calibraciones"])
    if not os.path.exists(fpath):
        return jsonify({"error":"No se encontró FFCALA.DBF"}), 404

    rows = read_dbf(fpath)
    rows = [{(k.lower() if isinstance(k,str) else k): v for k,v in r.items()} for r in rows]
    tk_alm = "almacen"
    tk_tan = "tanques"
    if almacen_code:
        rows = [r for r in rows if str(r.get(tk_alm, "")).strip() == str(almacen_code)]
    if tanque_code:
        rows = [r for r in rows if str(r.get(tk_tan, "")).strip() == str(tanque_code)]

    rows = _sort_by_dt(rows)
    rows = rows[-int(n):] if n else rows
    last_dt = _to_datetime(rows[-1]) if rows else None
    last_ts = last_dt.strftime("%Y-%m-%d %H:%M") if last_dt else None

    return jsonify({
        "table":"calibraciones",
        "file": ENDPOINTS["calibraciones"],
        "resolved_path": fpath,
        "count": len(rows),
        "selector": {"almacen": almacen_code, "tanque": tanque_code},
        "last_ts": last_ts,
        "rows": rows
    })

@app.get("/api/stream/calibraciones")
def sse_calibraciones():
    tanque = request.args.get("tanque")
    n = request.args.get("n", default=10, type=int)
    interval = request.args.get("interval", default=2, type=int)
    fpath = resolve_data_file(ENDPOINTS["calibraciones"])
    if not os.path.exists(fpath):
        return jsonify({"error":"No se encontró FFCALA.DBF"}), 404

    def event_stream():
        last_mtime = None
        while True:
            try:
                mtime = os.path.getmtime(fpath)
                if (last_mtime is None) or (mtime != last_mtime):
                    rows = read_dbf(fpath)
                    rows = [{(k.lower() if isinstance(k,str) else k): v for k,v in r.items()} for r in rows]
                    rows = _sort_by_dt(rows)
                    rows = rows[-int(n):] if n else rows
                    last_dt = _to_datetime(rows[-1]) if rows else None
                    last_ts = last_dt.strftime("%Y-%m-%d %H:%M") if last_dt else None
                    payload = json.dumps({"count": len(rows), "last_ts": last_ts, "rows": rows}, ensure_ascii=False)
                    last_mtime = mtime
                    yield f"data: {payload}\n\n"
                time.sleep(max(1, interval))
            except GeneratorExit:
                break
            except Exception as e:
                err = json.dumps({"error": str(e)})
                yield f"data: {err}\n\n"
                time.sleep(max(1, interval))

    headers = {"Content-Type": "text/event-stream","Cache-Control": "no-cache","Connection": "keep-alive","X-Accel-Buffering": "no"}
    return Response(event_stream(), headers=headers)

@app.get('/favicon.ico')
def favicon():
    fav_path = os.path.join(STATIC_DIR, 'favicon.ico')
    if os.path.exists(fav_path):
        return send_from_directory(STATIC_DIR, 'favicon.ico')
    return ('', 204)

@app.get("/api/where")
def api_where():
    out = {"aliases": ALIASES}
    for key, fname in ENDPOINTS.items():
        path = resolve_data_file(fname)
        out[key] = {"file": fname,"resolved_path": path,"exists": os.path.exists(path),"size_bytes": (os.path.getsize(path) if os.path.exists(path) else 0)}
    return jsonify(out)

@app.get("/")
def index():
    return render_template("sondastanques_mod.html")

@app.get("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)

def open_browser_when_ready(port=5000):
    url = f"http://127.0.0.1:{port}/"
    def _open():
        try: webbrowser.open(url)
        except Exception: pass
    threading.Timer(0.8, _open).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    open_browser_when_ready(port)
    app.run(host="127.0.0.1", port=port, debug=False)


@app.get("/debug/static")
def debug_static():
    return jsonify({
        "templates_dir": TEMPLATES_DIR,
        "static_dir": STATIC_DIR,
        "exists_templates": os.path.exists(TEMPLATES_DIR),
        "exists_static": os.path.exists(STATIC_DIR),
        "ls_templates": (os.listdir(TEMPLATES_DIR) if os.path.exists(TEMPLATES_DIR) else []),
        "ls_static": (os.listdir(STATIC_DIR) if os.path.exists(STATIC_DIR) else []),
    })

@app.get("/health")
def health():
    return jsonify({"ok": True})

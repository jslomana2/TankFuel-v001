#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, threading, webbrowser, json, time
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory, render_template, Response
from werkzeug.middleware.proxy_fix import ProxyFix

def resource_path(*parts):
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base_path, *parts)

TEMPLATES_DIR = resource_path("templates")
STATIC_DIR = resource_path("static")
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
    DBF = _import_dbfread()
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

def available_tables():
    out = []
    for key, fname in ENDPOINTS.items():
        fpath = os.path.join(DATA_DIR, fname)
        out.append({
            "name": key,
            "file": fname,
            "exists": os.path.exists(fpath),
            "size_bytes": os.path.getsize(fpath) if os.path.exists(fpath) else 0
        })
    return out

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

@app.get("/api/tables")
def api_tables():
    return jsonify(available_tables())

@app.get("/api/<name>")
def api_table(name):
    if name not in ENDPOINTS:
        return jsonify({"error": f"Tabla '{name}' no está definida.", "available": list(ENDPOINTS.keys())}), 404
    fname = ENDPOINTS[name]
    fpath = os.path.join(DATA_DIR, fname)
    if not os.path.exists(fpath):
        return jsonify({"error": f"No se encontró el archivo {fname} en la carpeta 'data'."}), 404

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
        return jsonify({"table": name, "file": fname, "count": len(rows), "rows": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ---- Últimas lecturas y SSE ----
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

def read_last_readings_per_tank(dbf_path, tanque_value=None, n=10):
    rows = read_dbf(dbf_path)
    rows = [{(k.lower() if isinstance(k,str) else k): v for k,v in r.items()} for r in rows]
    tkey = _infer_tanque_key(rows)
    if tkey and tanque_value is not None:
        rows = [r for r in rows if str(r.get(tkey, "")).strip() == str(tanque_value).strip()]
    rows = _sort_by_dt(rows)
    if n is not None:
        rows = rows[-int(n):]
    # añade un campo last_ts formateado si es posible
    last_dt = _to_datetime(rows[-1]) if rows else None
    last_ts = last_dt.strftime("%Y-%m-%d %H:%M") if last_dt else None
    return rows, tkey, last_ts

@app.get("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    tanque = request.args.get("tanque")
    n = request.args.get("n", default=10, type=int)
    fpath = os.path.join(DATA_DIR, ENDPOINTS["calibraciones"])
    if not os.path.exists(fpath):
        return jsonify({"error":"No se encontró FFCALA.DBF"}), 404
    rows, tkey, last_ts = read_last_readings_per_tank(fpath, tanque_value=tanque, n=n)
    return jsonify({
        "table":"calibraciones",
        "file": ENDPOINTS["calibraciones"],
        "count": len(rows),
        "tanque_key": tkey,
        "last_ts": last_ts,
        "rows": rows
    })

@app.get("/api/stream/calibraciones")
def sse_calibraciones():
    tanque = request.args.get("tanque")
    n = request.args.get("n", default=10, type=int)
    interval = request.args.get("interval", default=2, type=int)
    fpath = os.path.join(DATA_DIR, ENDPOINTS["calibraciones"])
    if not os.path.exists(fpath):
        return jsonify({"error":"No se encontró FFCALA.DBF"}), 404

    def event_stream():
        last_mtime = None
        while True:
            try:
                mtime = os.path.getmtime(fpath)
                if (last_mtime is None) or (mtime != last_mtime):
                    rows, tkey, last_ts = read_last_readings_per_tank(fpath, tanque_value=tanque, n=n)
                    payload = json.dumps({"tanque_key": tkey, "count": len(rows), "last_ts": last_ts, "rows": rows}, ensure_ascii=False)
                    last_mtime = mtime
                    yield f"data: {payload}\n\n"
                time.sleep(max(1, interval))
            except GeneratorExit:
                break
            except Exception as e:
                err = json.dumps({"error": str(e)})
                yield f"data: {err}\n\n"
                time.sleep(max(1, interval))

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return Response(event_stream(), headers=headers)

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

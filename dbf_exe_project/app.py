#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, threading, webbrowser
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from dbfread import DBF, FieldParser

# ---- Patch: Safe parser para campos memo ----
class SafeFieldParser(FieldParser):
    def parseM(self, field, data):
        return None

def safe_json_val(v):
    if isinstance(v, bytes):
        try:
            return v.decode("latin-1").strip()
        except Exception:
            return v.hex()
    if isinstance(v, datetime):
        return v.isoformat()
    return v

def resource_path_multi(subdir: str) -> str:
    bases = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass: bases.append(meipass)
    if getattr(sys, "frozen", False):
        bases.append(os.path.dirname(sys.executable))
    bases.append(os.path.abspath("."))
    for b in bases:
        p = os.path.join(b, subdir)
        if os.path.exists(p):
            return p
    return os.path.join(meipass or os.path.abspath("."), subdir)

TEMPLATES_DIR = resource_path_multi("templates")
STATIC_DIR = resource_path_multi("static")
DATA_DIR = os.path.join(getattr(sys, "_MEIPASS", os.path.abspath(".")), "data")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.wsgi_app = ProxyFix(app.wsgi_app)

def read_dbf(file_path, encoding="latin-1", lower_names=True, limit=None):
    table = DBF(file_path,
                load=True,
                encoding=encoding,
                lowernames=lower_names,
                parserclass=SafeFieldParser,
                ignore_missing_memofile=True)
    rows = [dict(r) for r in table]
    if limit is not None:
        rows = rows[:int(limit)]
    # Sanear valores para JSON
    rows = [{(k.lower() if isinstance(k,str) else k): safe_json_val(v) for k,v in r.items()} for r in rows]
    return rows

ENDPOINTS = {
    "tanques": "FFTANQ.DBF",
    "almacenes": "FFALMA.DBF",
    "articulos": "FFARTI.DBF",
    "calibraciones": "FFCALA.DBF",
}

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
    env_dir = os.environ.get('FUEL_DB_DIR')
    if env_dir:
        p = os.path.join(env_dir, fname)
        if os.path.exists(p): return p
    candidate = os.path.join(DATA_DIR, fname)
    if os.path.exists(candidate): return candidate
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.abspath('.')
    for p in (os.path.join(exe_dir, 'data', fname), os.path.join(exe_dir, fname)):
        if os.path.exists(p): return p
    cwd = os.getcwd()
    for p in (os.path.join(cwd, 'data', fname), os.path.join(cwd, fname)):
        if os.path.exists(p): return p
    return candidate

@app.get("/api/where")
def api_where():
    out = {"aliases": list(ALIASES.keys())}
    for key, fname in ENDPOINTS.items():
        path = resolve_data_file(fname)
        out[key] = {"file": fname,"resolved_path": path,"exists": os.path.exists(path),"size_bytes": (os.path.getsize(path) if os.path.exists(path) else 0)}
    return jsonify(out)

@app.get("/")
def index():
    return render_template("sondastanques_mod.html")

@app.get("/sondastanques_mod.css")
def static_css_root():
    return send_from_directory(STATIC_DIR, "sondastanques_mod.css")

@app.get("/sondastanques_mod.js")
def static_js_root():
    return send_from_directory(STATIC_DIR, "sondastanques_mod.js")

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
    app.run(host="127.0.0.1", port=port, debug=True)

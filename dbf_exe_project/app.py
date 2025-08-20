#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys, threading, webbrowser, logging
from datetime import datetime
from flask import Flask, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from dbfread import FieldParser

# --- Logging ---
logfile = os.path.join(os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__), "debug.log")
logging.basicConfig(
    filename=logfile,
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def excepthook(exc_type, exc_value, tb):
    import traceback
    logging.error("".join(traceback.format_exception(exc_type, exc_value, tb)))
    sys.__excepthook__(exc_type, exc_value, tb)

sys.excepthook = excepthook

# --- Safe parser ---
class SafeFieldParser(FieldParser):
    def parseM(self, field, data):
        return None

def safe_json_val(v):
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

# --- Flask app ---
TEMPLATES_DIR = "templates"
STATIC_DIR = "static"
app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
app.wsgi_app = ProxyFix(app.wsgi_app)

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

@app.route("/api/test")
def api_test():
    return jsonify({"status":"ok","message":"Servidor levantado correctamente"})

if __name__ == "__main__":
    try:
        port = int(os.environ.get("PORT", "5000"))
        logging.info(f"Iniciando servidor en http://127.0.0.1:{port}")
        app.run(host="127.0.0.1", port=port, debug=True)
    except Exception as e:
        logging.exception("Fallo al iniciar la app")
        raise

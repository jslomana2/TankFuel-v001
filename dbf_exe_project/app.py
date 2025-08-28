import os
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

# --- API placeholders (keep routes expected by UI) ---
@app.route("/api/tanques_norm")
def api_tanques_norm():
    # Dev note: backend real reads DBFs; here we return empty list so UI loads.
    return jsonify([])

@app.route("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    return jsonify([])

@app.route("/api/almacenes")
def api_almacenes():
    return jsonify([])

@app.route("/api/articulos")
def api_articulos():
    return jsonify([])

if __name__ == "__main__":
    app.run(debug=True)
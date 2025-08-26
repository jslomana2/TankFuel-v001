
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, render_template, request, send_from_directory
from dbfread import DBF

APP_NAME = "PROCONSI – Tanques"
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
# When running as EXE, DBFs are next to the EXE; in dev, next to this file.
DATA_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(sys.executable).parent if getattr(sys, "frozen", False) else BASE_DIR

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"), static_folder=str(BASE_DIR / "static"))

def _first_key(d, *candidates):
    """Return first present key in dict `d` for any of the candidate names (case-insensitive)."""
    lower = {k.lower(): k for k in d.keys()}
    for cand in candidates:
        k = lower.get(cand.lower())
        if k is not None:
            return k
    return None

def load_table(name):
    """Load a DBF table from DATA_DIR with smart encoding fallback."""
    path = (DATA_DIR / f"{name}.DBF")
    if not path.exists():
        # also try uppercase/lowercase variants
        for alt in [name.upper(), name.lower(), name.capitalize()]:
            if (DATA_DIR / f"{alt}.DBF").exists():
                path = DATA_DIR / f"{alt}.DBF"
                break
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra {name}.DBF en {DATA_DIR}")
    # Try common encodings used in FoxPro DBFs in ES environments
    for enc in ("cp1252", "latin1", "cp850"):
        try:
            return list(DBF(str(path), encoding=enc, ignore_missing_memofile=True))
        except Exception:
            continue
    # last resort
    return list(DBF(str(path), encoding='latin1', ignore_missing_memofile=True))

def rows_by_key(rows):
    """Return lowercase-key dicts for case-insensitive access while keeping originals."""
    out = []
    for r in rows:
        out.append({k.lower(): v for k, v in r.items()})
    return out

@app.route("/")
def index():
    return render_template("sondastanques_mod.html", app_name=APP_NAME)

@app.route("/api/almacenes")
def api_almacenes():
    try:
        alms = rows_by_key(load_table("FFALMA"))
        # Guess field names
        result = []
        for r in alms:
            cod = r.get("codalm") or r.get("codigo") or r.get("id") or r.get("almacen") or r.get("cod_alm") or r.get("cod")
            nom = r.get("desalm") or r.get("nombre") or r.get("descripcion") or r.get("des_alm")
            if not cod:
                continue
            result.append({"codigo": str(cod).strip(), "nombre": (str(nom).strip() if nom else str(cod).strip())})
        result.sort(key=lambda x: x["codigo"])
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/articulos")
def api_articulos():
    try:
        arts = rows_by_key(load_table("FFARTI"))
        result = []
        for r in arts:
            cod = r.get("codart") or r.get("codigo") or r.get("id") or r.get("articulo") or r.get("cod_art") or r.get("cod")
            nom = r.get("desart") or r.get("nombre") or r.get("descripcion") or r.get("des_art")
            color = r.get("color") or r.get("colorrgb") or r.get("color_rgb") or "#4f8cc9"
            result.append({"codigo": str(cod).strip(), "nombre": (str(nom).strip() if nom else str(cod).strip()), "color": str(color).strip()})
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

def _flt(x):
    try:
        if x is None or (isinstance(x, str) and x.strip() == ""):
            return None
        return float(x)
    except Exception:
        return None

@app.route("/api/tanques_norm")
def api_tanques_norm():
    almacen = request.args.get("almacen")
    try:
        tanqs = rows_by_key(load_table("FFTANQ"))
        arts_index = { (r.get("codart") or r.get("codigo") or r.get("id")): r for r in rows_by_key(load_table("FFARTI")) }
        data = []
        for r in tanqs:
            alm = r.get("codalm") or r.get("almacen") or r.get("cod_alm")
            if almacen and str(alm).strip() != almacen:
                continue
            tid = r.get("idtanq") or r.get("id") or r.get("codtan") or r.get("tanque")
            art = r.get("codart") or r.get("articulo")
            nomtan = r.get("destanq") or r.get("descripcion") or f"Tanque {tid}"
            cap = _flt(r.get("capacidad") or r.get("capmax") or r.get("cap_nominal") or r.get("cap"))
            niv = _flt(r.get("nivel") or r.get("litros") or r.get("existencia") or r.get("existencias"))
            agua = _flt(r.get("agua") or r.get("h2o"))
            temp = _flt(r.get("temperatura") or r.get("temp"))
            pct = None
            if cap and niv is not None:
                try:
                    pct = max(0.0, min(100.0, (niv / cap) * 100.0))
                except Exception:
                    pct = None
            artname = None
            artcolor = "#4f8cc9"
            if art in arts_index:
                a = arts_index[art]
                artname = a.get("desart") or a.get("nombre")
                artcolor = a.get("colorrgb") or a.get("color") or artcolor
            data.append({
                "tanque_id": str(tid),
                "almacen": str(alm) if alm is not None else "",
                "articulo": str(art) if art is not None else "",
                "articulo_nombre": artname or "",
                "color": artcolor,
                "nombre": str(nomtan),
                "capacidad": cap,
                "litros": niv,
                "porcentaje": pct,
                "agua": agua,
                "temperatura": temp,
            })
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/calibraciones/ultimas")
def api_calibraciones():
    tanque_id = request.args.get("tanque_id")
    n = int(request.args.get("n", 120))
    try:
        cal = rows_by_key(load_table("FFCALA"))
        # Guess fields
        out = []
        for r in cal:
            tid = r.get("idtanq") or r.get("tanque") or r.get("id") or r.get("codtan")
            if tanque_id and str(tid).strip() != str(tanque_id).strip():
                continue
            fecha = r.get("fecha") or r.get("fec") or r.get("fch") or r.get("fechahora") or r.get("timestamp") or r.get("hora")
            litros = _flt(r.get("litros") or r.get("volumen") or r.get("nivel"))
            agua = _flt(r.get("agua") or r.get("h2o"))
            temp = _flt(r.get("temperatura") or r.get("temp"))
            out.append({
                "tanque_id": str(tid) if tid is not None else "",
                "fecha": str(fecha) if fecha is not None else "",
                "litros": litros,
                "agua": agua,
                "temperatura": temp
            })
        out = out[-n:] if n and len(out) > n else out
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/where")
def api_where():
    return jsonify({
        "ok": True,
        "cwd": str(os.getcwd()),
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "frozen": bool(getattr(sys, "frozen", False)),
        "files": [p for p in os.listdir(DATA_DIR) if p.lower().endswith(".dbf")]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"Iniciando servidor en http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)


import os, sys
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from dbfread import DBF

APP_NAME = "PROCONSI – Tanques"

FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

# Where are templates/static?
if FROZEN:
    tmpl_dir = BASE_DIR / "templates"
    static_dir = BASE_DIR / "static"
else:
    tmpl_dir = Path(__file__).resolve().parent / "templates"
    static_dir = Path(__file__).resolve().parent / "static"

app = Flask(__name__, template_folder=str(tmpl_dir), static_folder=str(static_dir))

# Data dir: when frozen, by defecto al lado del EXE; puedes pasar ruta como primer argumento
if len(sys.argv) > 1:
    DATA_DIR = Path(sys.argv[1])
elif FROZEN:
    DATA_DIR = Path(sys.executable).parent
else:
    DATA_DIR = Path(__file__).resolve().parent

def rows_by_key(rows):
    return [{k.lower(): v for k, v in r.items()} for r in rows]

def load_table(name):
    path = (DATA_DIR / f"{name}.DBF")
    if not path.exists():
        # probar variantes
        for alt in [name.upper(), name.lower(), name.capitalize()]:
            p = DATA_DIR / f"{alt}.DBF"
            if p.exists():
                path = p; break
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra {name}.DBF en {DATA_DIR}")
    for enc in ("cp1252","latin1","cp850"):
        try:
            return list(DBF(str(path), encoding=enc, ignore_missing_memofile=True))
        except Exception:
            continue
    return list(DBF(str(path), encoding="latin1", ignore_missing_memofile=True))

def _flt(x):
    try:
        if x is None or (isinstance(x, str) and x.strip() == ""):
            return None
        return float(x)
    except Exception:
        return None

@app.route("/")
def index():
    return render_template("sondastanques_mod.html", app_name=APP_NAME)

@app.route("/api/almacenes")
def api_almacenes():
    try:
        alms = rows_by_key(load_table("FFALMA"))
        out = []
        for r in alms:
            cod = r.get("codalm") or r.get("codigo") or r.get("id") or r.get("almacen") or r.get("cod_alm") or r.get("cod")
            nom = r.get("desalm") or r.get("nombre") or r.get("descripcion") or r.get("des_alm")
            if not cod: 
                continue
            out.append({"codigo": str(cod).strip(), "nombre": (str(nom).strip() if nom else str(cod).strip())})
        out.sort(key=lambda x: x["codigo"])
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/articulos")
def api_articulos():
    try:
        arts = rows_by_key(load_table("FFARTI"))
        data = []
        for r in arts:
            cod = r.get("codart") or r.get("codigo") or r.get("id") or r.get("articulo") or r.get("cod_art") or r.get("cod")
            nom = r.get("desart") or r.get("nombre") or r.get("descripcion") or r.get("des_art")
            color = r.get("color") or r.get("colorrgb") or r.get("color_rgb") or "#4f8cc9"
            data.append({"codigo": str(cod).strip(), "nombre": (str(nom).strip() if nom else str(cod).strip()), "color": str(color).strip()})
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

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
            artname = ""
            artcolor = "#4f8cc9"
            if art in arts_index:
                a = arts_index[art]
                artname = a.get("desart") or a.get("nombre") or ""
                artcolor = a.get("colorrgb") or a.get("color") or artcolor
            data.append({
                "tanque_id": str(tid),
                "almacen": str(alm) if alm is not None else "",
                "articulo": str(art) if art is not None else "",
                "articulo_nombre": artname,
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
        "frozen": FROZEN,
        "base_dir": str(BASE_DIR),
        "tmpl_dir": str(tmpl_dir),
        "static_dir": str(static_dir),
        "data_dir": str(DATA_DIR),
        "files": [p for p in os.listdir(DATA_DIR) if p.lower().endswith(".dbf")] if DATA_DIR.exists() else []
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "5000"))
    print(f"Iniciando servidor en http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)

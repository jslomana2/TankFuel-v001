
import os, sys
from pathlib import Path
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, redirect, url_for
from dbfread import DBF

APP_NAME = "Tanques – Vista avanzada"

FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
tmpl_dir = (BASE_DIR / "templates") if FROZEN else (Path(__file__).resolve().parent / "templates")
static_dir = (BASE_DIR / "static") if FROZEN else (Path(__file__).resolve().parent / "static")
app = Flask(__name__, template_folder=str(tmpl_dir), static_folder=str(static_dir))

# Data: arg > exe dir > script dir
if len(sys.argv) > 1:
    DATA_DIR = Path(sys.argv[1])
elif FROZEN:
    DATA_DIR = Path(sys.executable).parent
else:
    DATA_DIR = Path(__file__).resolve().parent

def _load(name):
    path = (DATA_DIR / f"{name}.DBF")
    if not path.exists():
        for alt in [name.upper(), name.lower(), name.capitalize()]:
            p = DATA_DIR / f"{alt}.DBF"
            if p.exists():
                path = p; break
    if not path.exists():
        raise FileNotFoundError(f"Falta {name}.DBF en {DATA_DIR}")
    for enc in ("cp1252","latin1","cp850"):
        try:
            return list(DBF(str(path), encoding=enc, ignore_missing_memofile=True))
        except Exception:
            continue
    return list(DBF(str(path), encoding="latin1", ignore_missing_memofile=True))

def _rows(rows):  # uppercase keys
    return [{k.upper(): v for k,v in r.items()} for r in rows]

def _flt(v):
    try:
        if v is None or (isinstance(v,str) and v.strip()==""): return None
        return float(v)
    except Exception:
        return None

def _colorref_bgr_to_hex(v, default="#4f8cc9"):
    try:
        n = int(v)
        r = n & 0xFF
        g = (n >> 8) & 0xFF
        b = (n >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return default

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/vista")
def index_view():
    return render_template("sondastanques_mod.html", app_name=APP_NAME)

@app.route("/api/almacenes")
def api_almacenes():
    """Only warehouses that have tanks; name from FFALMA.POBLACION (fallback NOMBRE, then code)."""
    try:
        tanqs = _rows(_load("FFTANQ"))
        present = sorted({str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip() for r in tanqs if (r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO"))})
        names = {}
        try:
            alms = _rows(_load("FFALMA"))
            for r in alms:
                code = str(r.get("CODIGO") or "").strip()
                name = str(r.get("POBLACION") or r.get("NOMBRE") or code).strip()
                if code:
                    names[code] = name
        except Exception:
            pass
        data = [{"codigo": c, "nombre": names.get(c, c)} for c in present]
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/tanques_norm")
def api_tanques_norm():
    """Return tanks list for UI: levels & temperature from latest FFCALA per tank."""
    alm_filter = request.args.get("almacen")
    try:
        tanqs = _rows(_load("FFTANQ"))
        # articles
        try:
            arts = _rows(_load("FFARTI"))
        except Exception:
            arts = []
        by_pair = {}
        by_code = {}
        for a in arts:
            cod = str(a.get("CODIGO") or "").strip()
            alm = str(a.get("ALMACEN") or "").strip()
            name = (a.get("DESCRI") or a.get("DESCRIPCION") or cod)
            color = _colorref_bgr_to_hex(a.get("COLORPRODU"))
            if cod:
                by_code[cod] = {"producto": str(name).strip(), "color": color}
                if alm:
                    by_pair[(alm, cod)] = {"producto": str(name).strip(), "color": color}

        # latest calibration readings
        last = {}
        try:
            cal = _rows(_load("FFCALA"))
            bucket = defaultdict(list)
            for r in cal:
                alm = str(r.get("ALMACEN") or "").strip()
                cod = str(r.get("CODIGO") or "").strip()
                if not alm or not cod: continue
                bucket[(alm,cod)].append(r)
            for k, rows in bucket.items():
                rr = rows[-1]
                last[k] = {
                    "volumen": _flt(rr.get("LITROS")),
                    "litros15": _flt(rr.get("LITROS15")),
                    "temperatura": _flt(rr.get("TEMPERA"))
                }
        except Exception:
            pass

        # map almacenes names
        almac_n = {}
        try:
            alms = _rows(_load("FFALMA"))
            for r in alms:
                c = str(r.get("CODIGO") or "").strip()
                n = str(r.get("POBLACION") or r.get("NOMBRE") or c).strip()
                if c: almac_n[c]=n
        except Exception:
            pass

        data = []
        for r in tanqs:
            alm = str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip()
            cod = str((r.get("CODIGO") or r.get("IDTANQ") or r.get("CODTAN") or "")).strip()
            if not alm or not cod: 
                continue
            if alm_filter and alm != alm_filter:
                continue
            tid = f"{alm}-{cod}"
            art = str((r.get("ARTICULO") or "")).strip()
            artinfo = by_pair.get((alm, art)) or by_code.get(art) or {"producto": art, "color": "#4f8cc9"}
            nombre = (r.get("DESCRI") or r.get("DESCRIPCION") or f"Tanque {cod}")
            capacidad = _flt(r.get("CAPACIDAD"))

            v = last.get((alm,cod), {})
            volumen = v.get("volumen")
            litros15 = v.get("litros15")
            temperatura = v.get("temperatura")

            # fallback to FFTANQ if FFCALA empty
            if volumen is None:
                volumen = _flt(r.get("STOCK"))
            if litros15 is None:
                litros15 = _flt(r.get("STOCK15"))

            porcentaje = None
            if capacidad and volumen is not None:
                try:
                    porcentaje = max(0.0, min(100.0, (volumen / capacidad) * 100.0))
                except Exception:
                    porcentaje = None

            data.append({
                "tanque_id": tid,
                "almacen": alm,
                "almacen_nombre": almac_n.get(alm, alm),
                "nombre": str(nombre),
                "producto": artinfo["producto"],
                "color": artinfo["color"],
                "capacidad": capacidad,
                "volumen": volumen,
                "litros15": litros15,
                "temperatura": temperatura,
                "porcentaje": porcentaje
            })
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/calibraciones/ultimas")
def api_calibraciones():
    tanque_id = request.args.get("tanque_id")
    n = int(request.args.get("n", 120))
    try:
        if not tanque_id or "-" not in tanque_id:
            return jsonify({"ok": True, "data": []})
        alm, cod = tanque_id.split("-",1)
        cal = _rows(_load("FFCALA"))
        out = []
        for r in cal:
            if str(r.get("ALMACEN") or "").strip()!=alm or str(r.get("CODIGO") or "").strip()!=cod:
                continue
            out.append({
                "tanque_id": tanque_id,
                "fecha": str(r.get("FECHA") or ""),
                "hora": str(r.get("HORA") or ""),
                "litros": _flt(r.get("LITROS")),
                "litros15": _flt(r.get("LITROS15")),
                "temperatura": _flt(r.get("TEMPERA"))
            })
        out = out[-n:] if n and len(out)>n else out
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/where")
def api_where():
    return jsonify({
        "ok": True, "frozen": FROZEN,
        "tmpl_dir": str(tmpl_dir), "static_dir": str(static_dir),
        "data_dir": str(DATA_DIR),
        "files": [p for p in os.listdir(DATA_DIR) if p.lower().endswith(".dbf")] if DATA_DIR.exists() else []
    })

if __name__=="__main__":
    port = int(os.environ.get("PORT","5000"))
    print(f"Run: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)

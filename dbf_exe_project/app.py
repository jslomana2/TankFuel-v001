import os, sys
from pathlib import Path
from collections import defaultdict, deque
from flask import Flask, jsonify, render_template, request
from dbfread import DBF

APP_NAME = "PROCONSI – Tanques"

FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

tmpl_dir = (BASE_DIR / "templates") if FROZEN else (Path(__file__).resolve().parent / "templates")
static_dir = (BASE_DIR / "static") if FROZEN else (Path(__file__).resolve().parent / "static")
app = Flask(__name__, template_folder=str(tmpl_dir), static_folder=str(static_dir))

if len(sys.argv) > 1:
    DATA_DIR = Path(sys.argv[1])
elif FROZEN:
    DATA_DIR = Path(sys.executable).parent
else:
    DATA_DIR = Path(__file__).resolve().parent

def load_dbf(name):
    path = (DATA_DIR / f"{name}.DBF")
    if not path.exists():
        for alt in (name.upper(), name.lower(), name.capitalize()):
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

def rows_upper(rows):
    return [{k.upper(): v for k,v in r.items()} for r in rows]

def _flt(x):
    try:
        if x is None or (isinstance(x, str) and x.strip()==""):
            return None
        return float(x)
    except Exception:
        return None

def color_dec_to_hex_bgr(v, default="#4f8cc9"):
    # FoxPro/VB COLORREF decimal 0x00BBGGRR -> #RRGGBB
    try:
        n = int(v)
        r = n & 0xFF
        g = (n >> 8) & 0xFF
        b = (n >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return default

@app.route("/")
def index():
    try:
        return render_template("sondastanques_mod.html", app_name=APP_NAME)
    except Exception:
        return render_template("sondastanques_compat.html", app_name=APP_NAME)

@app.route("/compat")
def compat():
    return render_template("sondastanques_compat.html", app_name=APP_NAME)

@app.route("/api/almacenes")
def api_almacenes():
    try:
        tanqs = rows_upper(load_dbf("FFTANQ"))
        present = sorted({ str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip()
                           for r in tanqs if (r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO")) })
        name_by_code = {}
        try:
            alms = rows_upper(load_dbf("FFALMA"))
            for r in alms:
                c = str(r.get("CODIGO") or "").strip()
                n = str(r.get("POBLACION") or r.get("NOMBRE") or c).strip()
                if c:
                    name_by_code[c] = n
        except Exception:
            pass
        return jsonify({"ok": True, "data": [{"codigo": c, "nombre": name_by_code.get(c, c)} for c in present]})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

def build_articles_indexes():
    try:
        arts = rows_upper(load_dbf("FFARTI"))
    except Exception:
        return {}, {}
    idx_by_pair, idx_by_code = {}, {}
    for a in arts:
        cod = str(a.get("CODIGO") or "").strip()
        alm = str(a.get("ALMACEN") or "").strip()
        color = color_dec_to_hex_bgr(a.get("COLORPRODU"))
        name = (a.get("DESCRI") or a.get("DESCRIPCION") or cod)
        if cod:
            idx_by_code[cod] = {"producto": str(name).strip(), "color": color}
        if alm and cod:
            idx_by_pair[(alm, cod)] = {"producto": str(name).strip(), "color": color}
    return idx_by_pair, idx_by_code

def last5_by_tank(almacen_filter=None, limit=5):
    buckets = defaultdict(lambda: {"litros": deque(maxlen=limit), "litros15": deque(maxlen=limit), "temp": deque(maxlen=limit)})
    try:
        cal = rows_upper(load_dbf("FFCALA"))
        for r in reversed(cal):
            alm = str(r.get("ALMACEN") or "").strip()
            cod = str(r.get("CODIGO") or "").strip()
            if not alm or not cod:
                continue
            if almacen_filter and alm != almacen_filter:
                continue
            key = f"{alm}-{cod}"
            b = buckets[key]
            b["litros"].appendleft(_flt(r.get("LITROS")))
            b["litros15"].appendleft(_flt(r.get("LITROS15")))
            b["temp"].appendleft(_flt(r.get("TEMPERA")))
    except Exception:
        pass
    return buckets

def last_non_null(seq):
    for v in reversed(seq):
        if v is not None:
            return v
    return None

@app.route("/api/tanques_norm")
def api_tanques_norm():
    almacen_filter = request.args.get("almacen", "").strip() or None
    n = int(request.args.get("n", 5))
    try:
        tanqs = rows_upper(load_dbf("FFTANQ"))
        idx_by_pair, idx_by_code = build_articles_indexes()

        name_by_code = {}
        try:
            alms = rows_upper(load_dbf("FFALMA"))
            for r in alms:
                c = str(r.get("CODIGO") or "").strip()
                nalm = str(r.get("POBLACION") or r.get("NOMBRE") or c).strip()
                if c:
                    name_by_code[c] = nalm
        except Exception:
            pass

        recent = last5_by_tank(almacen_filter=almacen_filter, limit=n)

        data = []
        for r in tanqs:
            alm = str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip()
            codtan = str((r.get("CODIGO") or r.get("IDTANQ") or r.get("CODTAN") or "")).strip()
            if not alm or not codtan:
                continue
            if almacen_filter and alm != almacen_filter:
                continue
            key = f"{alm}-{codtan}"

            art = str((r.get("ARTICULO") or "")).strip()
            artinfo = idx_by_pair.get((alm, art)) or idx_by_code.get(art) or {"producto": art, "color": "#4f8cc9"}

            capacidad = _flt(r.get("CAPACIDAD"))
            if key in recent and recent[key]["litros"]:
                litros = last_non_null(recent[key]["litros"])
                litros15 = last_non_null(recent[key]["litros15"])
                temperatura = last_non_null(recent[key]["temp"])
            else:
                litros = _flt(r.get("STOCK"))
                litros15 = _flt(r.get("STOCK15"))
                temperatura = None

            porcentaje = None
            if capacidad and litros is not None and capacidad > 0:
                try:
                    porcentaje = max(0.0, min(100.0, (litros / capacidad) * 100.0))
                except Exception:
                    porcentaje = None

            data.append({
                "tanque_id": key,
                "almacen": alm,
                "almacen_nombre": name_by_code.get(alm, alm),
                "producto": artinfo["producto"],
                "color": artinfo["color"],
                "nombre": str((r.get("DESCRI") or r.get("DESCRIPCION") or f"Tanque {codtan}")),
                "capacidad": capacidad,
                "volumen": litros,
                "litros15": litros15,
                "temperatura": temperatura,
                "porcentaje": porcentaje
            })
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/calibraciones/ultimas")
def api_calibraciones_ultimas():
    tanque_id = request.args.get("tanque_id")
    n = int(request.args.get("n", 5))
    try:
        if not tanque_id or "-" not in tanque_id:
            return jsonify({"ok": True, "data": []})
        alm, cod = tanque_id.split("-", 1)
        cal = rows_upper(load_dbf("FFCALA"))
        rows = []
        for r in reversed(cal):
            if str(r.get("ALMACEN") or "").strip() == alm and str(r.get("CODIGO") or "").strip() == cod:
                rows.append({
                    "tanque_id": tanque_id,
                    "fecha": str(r.get("FECHA") or ""),
                    "hora": str(r.get("HORA") or ""),
                    "litros": _flt(r.get("LITROS")),
                    "litros15": _flt(r.get("LITROS15")),
                    "temperatura": _flt(r.get("TEMPERA"))
                })
                if len(rows) >= n:
                    break
        rows.reverse()
        return jsonify({"ok": True, "data": rows})
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
    port = int(os.environ.get("PORT", "5000"))
    print(f"Iniciando servidor en http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)

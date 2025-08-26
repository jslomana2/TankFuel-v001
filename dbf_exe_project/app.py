
import os, sys
from collections import defaultdict
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from dbfread import DBF

APP_NAME = "PROCONSI – Tanques"

FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))

# Template/static resolution both in dev and frozen
tmpl_dir = (BASE_DIR / "templates") if FROZEN else (Path(__file__).resolve().parent / "templates")
static_dir = (BASE_DIR / "static") if FROZEN else (Path(__file__).resolve().parent / "static")
app = Flask(__name__, template_folder=str(tmpl_dir), static_folder=str(static_dir))

# Data path: arg > exe folder > script folder
if len(sys.argv) > 1:
    DATA_DIR = Path(sys.argv[1])
elif FROZEN:
    DATA_DIR = Path(sys.executable).parent
else:
    DATA_DIR = Path(__file__).resolve().parent

def load_table(name):
    path = (DATA_DIR / f"{name}.DBF")
    if not path.exists():
        for alt in [name.upper(), name.lower(), name.capitalize()]:
            p = DATA_DIR / f"{alt}.DBF"
            if p.exists():
                path = p; break
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra {name}.DBF en {DATA_DIR}")
    # encodings typical in ES FoxPro
    for enc in ("cp1252", "latin1", "cp850"):
        try:
            return list(DBF(str(path), encoding=enc, ignore_missing_memofile=True))
        except Exception:
            continue
    return list(DBF(str(path), encoding="latin1", ignore_missing_memofile=True))

def rows_ci(rows):
    return [{k.upper(): v for k, v in r.items()} for r in rows]

def _flt(x):
    try:
        if x is None or (isinstance(x, str) and x.strip() == ""):
            return None
        return float(x)
    except Exception:
        return None

def _dec_to_hex_color(v, default="#4f8cc9"):
    try:
        n = int(v)
        if n < 0: n = 0
        n = n & 0xFFFFFF
        return f"#{n:06X}"
    except Exception:
        return default

# ------------------ ROUTES ------------------

@app.route("/")
def index():
    return render_template("sondastanques_mod.html", app_name=APP_NAME)

@app.route("/api/almacenes")
def api_almacenes():
    try:
        alms = rows_ci(load_table("FFALMA"))
        out = []
        for r in alms:
            cod = r.get("CODIGO")
            nom = r.get("NOMBRE")
            if cod is None: 
                continue
            out.append({"codigo": str(cod).strip(), "nombre": (str(nom).strip() if nom else str(cod).strip())})
        out.sort(key=lambda x: x["codigo"])
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/articulos")
def api_articulos():
    try:
        arts = rows_ci(load_table("FFARTI"))
        data = []
        for r in arts:
            cod = r.get("CODIGO")
            nom = r.get("DESCRI") or r.get("DESCRIPCION")
            color_dec = r.get("COLORPRODU")
            color = _dec_to_hex_color(color_dec) if color_dec is not None else "#4f8cc9"
            data.append({"codigo": str(cod).strip(), "nombre": (str(nom).strip() if nom else str(cod).strip()), "color": color})
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/tanques_norm")
def api_tanques_norm():
    almacen_filtro = request.args.get("almacen")
    try:
        tanqs = rows_ci(load_table("FFTANQ"))
        arts = rows_ci(load_table("FFARTI"))
        # Artículo index
        art_idx = { (a.get("CODIGO")): a for a in arts }

        # Últimas lecturas de FFCALA por tanque (LITROS, LITROS15, TEMPERA)
        last = {}
        try:
            cal = rows_ci(load_table("FFCALA"))
            by = defaultdict(list)
            for r in cal:
                alm = str(r.get("ALMACEN") or "").strip()
                cod = str(r.get("CODIGO") or "").strip()
                if not alm or not cod:
                    continue
                tid = f"{alm}-{cod}"
                by[tid].append(r)
            for tid, rows in by.items():
                rr = rows[-1]
                last[tid] = {
                    "litros": _flt(rr.get("LITROS")),
                    "litros15": _flt(rr.get("LITROS15")),
                    "temperatura": _flt(rr.get("TEMPERA"))
                }
        except Exception:
            pass

        out = []
        for r in tanqs:
            alm = str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip()
            codtan = str((r.get("CODIGO") or r.get("IDTANQ") or r.get("CODTAN") or "")).strip()
            if not alm or not codtan:
                # si tu tabla usa otros nombres me lo dices y lo ajusto
                continue
            if almacen_filtro and alm != almacen_filtro:
                continue
            tanque_id = f"{alm}-{codtan}"
            art = (r.get("ARTICULO"))
            artrow = art_idx.get(art)
            artname = (artrow.get("DESCRI") if artrow else "") or (artrow.get("DESCRIPCION") if artrow else "") or ""
            color = _dec_to_hex_color(artrow.get("COLORPRODU")) if artrow and artrow.get("COLORPRODU") is not None else "#4f8cc9"

            nombre = (r.get("DESCRI") or r.get("DESCRIPCION") or f"Tanque {tanque_id}")
            capacidad = _flt(r.get("CAPACIDAD"))
            # Nivel preferente: STOCK (tanque), si no, última lectura de FFCALA
            litros = _flt(r.get("STOCK"))
            litros15 = _flt(r.get("STOCK15"))
            cal_last = last.get(tanque_id, {})
            if litros is None:
                litros = cal_last.get("litros")
            if litros15 is None:
                litros15 = cal_last.get("litros15")
            temperatura = cal_last.get("temperatura")

            porcentaje = None
            if capacidad and litros is not None:
                try:
                    porcentaje = max(0.0, min(100.0, (litros / capacidad) * 100.0))
                except Exception:
                    porcentaje = None

            out.append({
                "tanque_id": tanque_id,
                "almacen": alm,
                "articulo": str(art) if art is not None else "",
                "articulo_nombre": artname,
                "color": color,
                "nombre": str(nombre),
                "capacidad": capacidad,
                "litros": litros,
                "litros15": litros15,
                "porcentaje": porcentaje,
                "agua": None,            # de momento fuera
                "temperatura": temperatura
            })
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/calibraciones/ultimas")
def api_calibraciones():
    tanque_id = request.args.get("tanque_id")  # esperado formato ALMACEN-CODIGO
    n = int(request.args.get("n", 120))
    try:
        if not tanque_id or "-" not in tanque_id:
            return jsonify({"ok": True, "data": []})
        alm, cod = tanque_id.split("-", 1)
        cal = rows_ci(load_table("FFCALA"))
        out = []
        for r in cal:
            r_alm = str(r.get("ALMACEN") or "").strip()
            r_cod = str(r.get("CODIGO") or "").strip()
            if r_alm != alm or r_cod != cod:
                continue
            fecha = r.get("FECHA")
            hora = r.get("HORA")
            litros = _flt(r.get("LITROS"))
            litros15 = _flt(r.get("LITROS15"))
            temperatura = _flt(r.get("TEMPERA"))
            out.append({
                "tanque_id": tanque_id,
                "fecha": str(fecha) if fecha is not None else "",
                "hora": str(hora) if hora is not None else "",
                "litros": litros,
                "litros15": litros15,
                "temperatura": temperatura
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

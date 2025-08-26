
import os, sys
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from dbfread import DBF

APP_NAME = "PROCONSI – Tanques"

FROZEN = bool(getattr(sys, "frozen", False))
BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
tmpl_dir = (BASE_DIR / "templates") if FROZEN else (Path(__file__).resolve().parent / "templates")
static_dir = (BASE_DIR / "static") if FROZEN else (Path(__file__).resolve().parent / "static")
app = Flask(__name__, template_folder=str(tmpl_dir), static_folder=str(static_dir))

# Data path resolution
if len(sys.argv) > 1:
    DATA_DIR = Path(sys.argv[1])
elif FROZEN:
    DATA_DIR = Path(sys.executable).parent
else:
    DATA_DIR = Path(__file__).resolve().parent

def load_table(name):
    """Load DBF with typical ES encodings and case-insensitive filename."""
    path = (DATA_DIR / f"{name}.DBF")
    if not path.exists():
        for alt in [name.upper(), name.lower(), name.capitalize()]:
            p = DATA_DIR / f"{alt}.DBF"
            if p.exists():
                path = p; break
    if not path.exists():
        raise FileNotFoundError(f"No se encuentra {name}.DBF en {DATA_DIR}")
    for enc in ("cp1252", "latin1", "cp850"):
        try:
            return list(DBF(str(path), encoding=enc, ignore_missing_memofile=True))
        except Exception:
            continue
    return list(DBF(str(path), encoding="latin1", ignore_missing_memofile=True))

def rows_upper(rows):
    return [{k.upper(): v for k, v in r.items()} for r in rows]

def _flt(x):
    try:
        if x is None or (isinstance(x, str) and x.strip() == ""):
            return None
        return float(x)
    except Exception:
        return None

def color_dec_to_hex_bgr(v, default="#4f8cc9"):
    """Convert Windows COLORREF decimal (BGR order) to CSS #RRGGBB.

    In FoxPro/VB the decimal packs as 0x00BBGGRR; here we unpack as BGR -> RGB.

    """
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
    return render_template("sondastanques_mod.html", app_name=APP_NAME)

@app.route("/api/almacenes")
def api_almacenes():
    """Return only warehouses that have tanks in FFTANQ."""
    try:
        tanqs = rows_upper(load_table("FFTANQ"))
        present = sorted({str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip() for r in tanqs if (r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO"))})
        # Try to map names from FFALMA if available
        name_by_code = {}
        try:
            alms = rows_upper(load_table("FFALMA"))
            for r in alms:
                c = str(r.get("CODIGO") or "").strip()
                n = str(r.get("NOMBRE") or c).strip()
                if c:
                    name_by_code[c] = n
        except Exception:
            pass
        data = [{"codigo": c, "nombre": name_by_code.get(c, c)} for c in present]
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/articulos")
def api_articulos():
    """Return articles with color converted to HEX. If table has ALMACEN, key by (ALMACEN,CODIGO) as well."""
    try:
        arts = rows_upper(load_table("FFARTI"))
        out = []
        for r in arts:
            cod = str(r.get("CODIGO") or "").strip()
            nom = (r.get("DESCRI") or r.get("DESCRIPCION") or cod)
            color = color_dec_to_hex_bgr(r.get("COLORPRODU"))
            alm = str(r.get("ALMACEN") or "").strip()
            row = {"codigo": cod, "nombre": str(nom).strip(), "color": color}
            if alm:
                row["almacen"] = alm
            out.append(row)
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/tanques_norm")
def api_tanques_norm():
    """Fast tanks listing. No FFCALA scanning here (speed!)."""
    almacen_filter = request.args.get("almacen")  # show one warehouse when provided
    try:
        tanqs = rows_upper(load_table("FFTANQ"))
        # Build article index by (ALMACEN, CODIGO) first, then by CODIGO
        try:
            arts = rows_upper(load_table("FFARTI"))
        except Exception:
            arts = []
        idx_by_pair = {}
        idx_by_code = {}
        for a in arts:
            cod = str(a.get("CODIGO") or "").strip()
            alm = str(a.get("ALMACEN") or "").strip()
            color = color_dec_to_hex_bgr(a.get("COLORPRODU"))
            name = (a.get("DESCRI") or a.get("DESCRIPCION") or cod)
            if cod:
                idx_by_code[cod] = {"producto": str(name).strip(), "color": color}
            if alm and cod:
                idx_by_pair[(alm, cod)] = {"producto": str(name).strip(), "color": color}

        # Optional name map for warehouses
        name_by_code = {}
        try:
            alms = rows_upper(load_table("FFALMA"))
            for r in alms:
                c = str(r.get("CODIGO") or "").strip()
                n = str(r.get("NOMBRE") or c).strip()
                if c:
                    name_by_code[c] = n
        except Exception:
            pass

        data = []
        for r in tanqs:
            alm = str((r.get("ALMACEN") or r.get("CODALM") or r.get("CODIGO") or "")).strip()
            codtan = str((r.get("CODIGO") or r.get("IDTANQ") or r.get("CODTAN") or "")).strip()
            if not alm or not codtan:
                continue
            if almacen_filter and alm != almacen_filter:
                continue
            art = str((r.get("ARTICULO") or "")).strip()
            artinfo = idx_by_pair.get((alm, art)) or idx_by_code.get(art) or {"producto": art, "color": "#4f8cc9"}

            capacidad = _flt(r.get("CAPACIDAD"))
            volumen = _flt(r.get("STOCK"))
            litros15 = _flt(r.get("STOCK15"))
            porcentaje = None
            if capacidad and volumen is not None:
                try:
                    porcentaje = max(0.0, min(100.0, (volumen / capacidad) * 100.0))
                except Exception:
                    porcentaje = None

            data.append({
                "tanque_id": f"{alm}-{codtan}",
                "almacen": alm,
                "almacen_nombre": name_by_code.get(alm, alm),
                "producto": artinfo["producto"],
                "color": artinfo["color"],
                "nombre": str((r.get("DESCRI") or r.get("DESCRIPCION") or f"Tanque {codtan}")),
                "capacidad": capacidad,
                "volumen": volumen,
                "litros15": litros15,
                "porcentaje": porcentaje,
                "agua": None,
                "temperatura": None
            })
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/calibraciones/ultimas")
def api_calibraciones():
    tanque_id = request.args.get("tanque_id")  # esperado ALMACEN-CODIGO
    n = int(request.args.get("n", 200))
    try:
        if not tanque_id or "-" not in tanque_id:
            return jsonify({"ok": True, "data": []})
        alm, cod = tanque_id.split("-", 1)
        cal = rows_upper(load_table("FFCALA"))
        out = []
        for r in cal:
            r_alm = str(r.get("ALMACEN") or "").strip()
            r_cod = str(r.get("CODIGO") or "").strip()
            if r_alm != alm or r_cod != cod:
                continue
            out.append({
                "tanque_id": tanque_id,
                "fecha": str(r.get("FECHA") or ""),
                "hora": str(r.get("HORA") or ""),
                "litros": _flt(r.get("LITROS")),
                "litros15": _flt(r.get("LITROS15")),
                "temperatura": _flt(r.get("TEMPERA"))
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
    port = int(os.environ.get("PORT", "5000"))
    print(f"Iniciando servidor en http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)

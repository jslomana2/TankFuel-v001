import os, sys, json, logging
from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory, request

try:
    from dbfread import DBF
    HAVE_DBFREAD = True
except Exception:
    HAVE_DBFREAD = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("app")

app = Flask(__name__, template_folder="templates", static_folder="static")

def is_frozen():
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")

def exe_dir():
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def find_dbf_dir():
    # Priority: explicit env, alongside EXE, current dir, parent, "dbf" subdir
    cand = []
    env = os.environ.get("DBF_DIR")
    if env:
        cand.append(Path(env))
    exed = exe_dir()
    cand += [exed, Path.cwd(), exed.parent, exed / "dbf"]
    for c in cand:
        if c and c.exists():
            if (c / "FFALMA.DBF").exists():
                return c
    # fallback: return exe dir anyway
    return exed

DBF_DIR = find_dbf_dir()
log.info("Usando DBF_DIR: %s", DBF_DIR)

def read_dbf(name):
    p = Path(DBF_DIR) / name
    if not p.exists():
        log.warning("DBF no encontrado: %s", p)
        return []
    if not HAVE_DBFREAD:
        log.warning("dbfread no disponible; devolviendo vacío para %s", name)
        return []
    try:
        rows = []
        for rec in DBF(str(p), load=True, lowernames=False, encoding="latin-1"):
            # normalizamos claves a mayúsculas
            row = { (k.upper() if isinstance(k, str) else k): v for k, v in rec.items() }
            rows.append(row)
        return rows
    except Exception as e:
        log.exception("Error leyendo %s: %s", name, e)
        return []

def safe_num(v, default=0):
    try:
        if v is None: return default
        if isinstance(v, (int, float)): return float(v)
        s = str(v).strip().replace(",", ".")
        return float(s) if s else default
    except Exception:
        return default

def hex_color(v, fallback="#2aa8ff"):
    s = (str(v or "")).strip().lstrip("#")
    if len(s) in (3, 6):
        try:
            int(s, 16)
            return "#" + s
        except Exception:
            pass
    return fallback

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    alma = read_dbf("FFALMA.DBF")
    # Campos típicos: CODIALM / CODALMA / CODALM, NOMBRE / DESCRIP
    out = []
    for r in alma:
        cod = r.get("CODIALM") or r.get("CODALMA") or r.get("CODALM") or r.get("COD_ALM") or r.get("ALMACEN") or ""
        nom = r.get("NOMBRE") or r.get("DESCRIP") or r.get("DESCRIPCION") or str(cod)
        out.append({"codigo": str(cod).strip(), "nombre": str(nom).strip()})
    # orden por nombre
    out.sort(key=lambda x: (x["nombre"], x["codigo"]))
    # Resumen para header
    return jsonify({"almacenes": out})

def build_color_map():
    # FFARTI: COLORPRODU por CODIARTI / CODIGO / ARTICULO
    art = read_dbf("FFARTI.DBF")
    cmap = {}
    for r in art:
        code = r.get("CODIARTI") or r.get("CODIGO") or r.get("ARTICULO") or r.get("COD_ARTI")
        col  = r.get("COLORPRODU") or r.get("COLOR") or r.get("COLOR_PROD")
        if code:
            cmap[str(code).strip()] = hex_color(col, "#2aa8ff")
    return cmap

@app.route("/api/tanques_norm")
def api_tanques_norm():
    color_map = build_color_map()
    tanq = read_dbf("FFTANQ.DBF")
    alma = read_dbf("FFALMA.DBF")
    # mapa de almacenes
    aname = {}
    for r in alma:
        cod = r.get("CODIALM") or r.get("CODALMA") or r.get("CODALM") or r.get("ALMACEN")
        nom = r.get("NOMBRE") or r.get("DESCRIP") or r.get("DESCRIPCION") or str(cod)
        if cod:
            aname[str(cod).strip()] = str(nom).strip()

    out = []
    for r in tanq:
        # Campos posibles (ajustamos a tu DBF real)
        codalm = r.get("CODIALM") or r.get("CODALMA") or r.get("COD_ALM") or r.get("ALMACEN")
        codtan = r.get("CODITANQ") or r.get("TANQUE") or r.get("COD_TANQ")
        prod   = r.get("CODIARTI") or r.get("CODIGOARTI") or r.get("PRODUCTO") or r.get("COD_ARTI")
        # niveles
        cap    = safe_num(r.get("CAPACIDAD") or r.get("CAP") or r.get("CAP_TANQ"))
        medido = safe_num(r.get("NIVELMED") or r.get("MEDIDO") or r.get("NIVEL_ACT"))
        libro  = safe_num(r.get("NIVELLIB") or r.get("LIBRO")  or r.get("NIVEL_LIB"))
        agua   = safe_num(r.get("AGUA") or r.get("NIVEL_AGUA"))
        # %
        pct = 0.0
        if cap > 0:
            pct = max(0.0, min(100.0, (medido / cap) * 100.0))

        fill = color_map.get(str(prod).strip(), "#2aa8ff")

        item = {
            "almacen": str(codalm).strip() if codalm is not None else "",
            "almacenNombre": aname.get(str(codalm).strip(), str(codalm).strip() if codalm else ""),
            "tanque": str(codtan).strip() if codtan is not None else "",
            "producto": str(prod).strip() if prod is not None else "",
            "capacidad": cap,
            "medido": medido,
            "libro": libro,
            "agua": agua,
            "pct": round(pct, 2),
            "fill": fill  # color desde FFARTI.COLORPRODU
        }
        out.append(item)

    # respuesta simple (la UI ya soporta array plano o agrupado)
    return jsonify(out)

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, "favicon.ico", mimetype="image/vnd.microsoft.icon")

if __name__ == "__main__":
    # Permite host local y puerto configurable por env
    port = int(os.environ.get("PORT", "5000"))
    log.info("Iniciando servidor en http://127.0.0.1:%s", port)
    app.run(host="127.0.0.1", port=port, debug=False)
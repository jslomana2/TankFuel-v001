# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from flask import Flask, jsonify, render_template, request, Response

try:
    from dbfread import DBF
except Exception:
    DBF = None

app = Flask(__name__, static_folder="static", template_folder="templates")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("PROCONSI-Tanques")

def _find_field(fields: List[str], *candidates) -> Optional[str]:
    fields_lower = [f.lower() for f in fields]
    for cand in candidates:
        cand_lower = cand.lower()
        if cand_lower in fields_lower:
            return fields[fields_lower.index(cand_lower)]
        for f in fields:
            fl = f.lower()
            if fl.startswith(cand_lower) or cand_lower in fl:
                return f
    return None

def _to_datetime(rec: Dict[str, Any], fields: List[str]) -> Optional[datetime]:
    f_fecha = _find_field(fields, "FECHA", "FEC", "DATE", "F_ALTA", "DATETIME", "FCH")
    f_hora  = _find_field(fields, "HORA", "TIME", "HRA")
    try:
        if f_fecha and f_hora and rec.get(f_fecha) and rec.get(f_hora):
            fecha = rec[f_fecha]
            hora_val = rec[f_hora]
            if hasattr(fecha, "year"):
                y, m, d = fecha.year, fecha.month, fecha.day
            else:
                return None
            if isinstance(hora_val, (int, float)):
                hh = int(hora_val) // 10000
                mm = (int(hora_val) % 10000) // 100
                ss = int(hora_val) % 100
            else:
                s = str(hora_val).strip()
                if ":" in s:
                    parts = s.split(":")
                    hh, mm, ss = int(parts[0] or 0), int(parts[1] or 0), int(parts[2] or 0)
                else:
                    s = s.zfill(6)
                    hh, mm, ss = int(s[0:2]), int(s[2:4]), int(s[4:6])
            return datetime(y, m, d, hh, mm, ss)
        elif f_fecha and rec.get(f_fecha):
            fecha = rec[f_fecha]
            if isinstance(fecha, datetime):
                return fecha
            return datetime(fecha.year, fecha.month, fecha.day)
        else:
            f_dt = _find_field(fields, "DATETIME", "STAMP", "TS")
            if f_dt and rec.get(f_dt):
                val = rec[f_dt]
                if isinstance(val, datetime):
                    return val
    except Exception:
        pass
    return None

def _read_dbf(path: str) -> List[Dict[str, Any]]:
    if DBF is None:
        raise RuntimeError("Falta 'dbfread'. Instala dependencias con requirements.txt")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No se encuentra {path}")
    table = DBF(path, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore')
    return list(table)

def _normalize_float(v) -> Optional[float]:
    try:
        if v is None: return None
        s = str(v).strip().replace(",", ".")
        if s == "" or s.upper() == "NULL":
            return None
        return float(s)
    except Exception:
        return None

def _last_non_null(values: List[Any]) -> Optional[Any]:
    for v in values:
        if v is None: continue
        if isinstance(v, str) and v.strip() == "": continue
        return v
    return None

def _san(v):
    from datetime import date, datetime
    if isinstance(v, (int, float, bool)) or v is None:
        return v
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, bytes):
        try:
            return v.decode('latin-1')
        except Exception:
            return v.decode('utf-8', errors='ignore')
    return str(v)

def _san_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [{k: _san(v) for k, v in r.items()} for r in rows]

def load_maestros(base_dir: str):
    maestros = {"tanques": [], "almacenes": [], "articulos": []}
    try:
        maestros["tanques"] = _read_dbf(os.path.join(base_dir, "FFTANQ.DBF"))
    except Exception as e:
        log.warning(f"No se pudo leer FFTANQ: {e}")
    try:
        maestros["almacenes"] = _read_dbf(os.path.join(base_dir, "FFALMA.DBF"))
    except Exception as e:
        log.warning(f"No se pudo leer FFALMA: {e}")
    try:
        maestros["articulos"] = _read_dbf(os.path.join(base_dir, "FFARTI.DBF"))
    except Exception as e:
        log.warning(f"No se pudo leer FFARTI: {e}")
    return maestros

def build_tanque_key_fields(sample_fields: List[str]):
    f_idtanq = _find_field(sample_fields, "IDTANQ", "CODTANQ", "TANQUE", "ID_TANQ", "IDTANQUE")
    f_idalma = _find_field(sample_fields, "IDALMA", "CODALMA", "ALMACEN", "ID_ALMA")
    f_idarti = _find_field(sample_fields, "IDARTI", "CODARTI", "ARTICULO", "ID_ARTI", "PRODUCTO")
    return f_idtanq, f_idalma, f_idarti

def index_by_key(rows: List[Dict[str, Any]], key_field: Optional[str]) -> Dict[Any, Dict[str, Any]]:
    if not key_field: return {}
    return { r.get(key_field): r for r in rows }

def load_tanques_norm(base_dir: str, almacen_filter: Optional[str]=None, want_debug: bool=False) -> List[Dict[str, Any]]:
    maestros = load_maestros(base_dir)
    tanques = maestros["tanques"]
    f_idtanq=f_idalma=f_idarti=None
    if tanques:
        f_idtanq, f_idalma, f_idarti = build_tanque_key_fields(list(tanques[0].keys()))
    idx_alma = index_by_key(maestros["almacenes"], f_idalma) if maestros["almacenes"] else {}
    idx_arti = index_by_key(maestros["articulos"], f_idarti) if maestros["articulos"] else {}

    ffcala_path = os.path.join(base_dir, "FFCALA.DBF")
    try:
        calibras = _read_dbf(ffcala_path)
    except Exception as e:
        log.warning(f"No se pudo leer FFCALA: {e}")
        calibras = []

    f_fields = list(calibras[0].keys()) if calibras else []
    c_idtanq = _find_field(f_fields, "IDTANQ", "CODTANQ", "TANQUE", "ID_TANQ", "IDTANQUE")
    c_idalma = _find_field(f_fields, "IDALMA", "CODALMA", "ALMACEN", "ID_ALMA")
    c_litros = _find_field(f_fields, "LITROS", "VOL", "VOLUMEN", "LTS", "VOLUMEN_ACTUAL", "LECTURA_LTS")
    c_l15    = _find_field(f_fields, "LITROS15", "VOL15", "VOLUMEN15", "LTS15", "L15", "VOL_15")
    c_temp   = _find_field(f_fields, "TEMPERA", "TEMP", "TEMPERATURA", "TEMP_TQ", "TANQ_TEMP", "T")

    grouped = {}
    for rec in calibras:
        alma = rec.get(c_idalma) if c_idalma else None
        tanq = rec.get(c_idtanq) if c_idtanq else None
        if almacen_filter and str(alma) != str(almacen_filter):
            continue
        if alma is None or tanq is None:
            continue
        grouped.setdefault((str(alma), str(tanq)), []).append(rec)

    for key, rows in grouped.items():
        rows.sort(key=lambda r: (_to_datetime(r, list(r.keys())) or datetime.min), reverse=True)
        grouped[key] = rows[:5]

    salida = []
    filtered_reasons = []
    for t in tanques:
        alma = t.get(f_idalma) if f_idalma else None
        tanq = t.get(f_idtanq) if f_idtanq else None
        if almacen_filter and str(alma) != str(almacen_filter):
            continue
        if alma is None or tanq is None:
            continue
        bunch = grouped.get((str(alma), str(tanq)), [])
        if not bunch:
            if want_debug:
                filtered_reasons.append({"tanque": str(t.get(f_idtanq)), "motivo": "sin lecturas en FFCALA"})
            continue

        lit_vals  = [_normalize_float(r.get(c_litros)) if c_litros else None for r in bunch]
        l15_vals  = [_normalize_float(r.get(c_l15))    if c_l15    else None for r in bunch]
        tmp_vals  = [_normalize_float(r.get(c_temp))   if c_temp   else None for r in bunch]

        volumen     = _last_non_null(lit_vals)
        litros15    = _last_non_null(l15_vals)
        temperatura = _last_non_null(tmp_vals)

        if volumen is None or litros15 is None or temperatura is None:
            if want_debug:
                filtered_reasons.append({"tanque": str(t.get(f_idtanq)), "motivo": f"falta dato (volumen={volumen}, l15={litros15}, temp={temperatura}) en últimas 5"})
            continue

        f_cap = _find_field(list(t.keys()), "CAPACIDAD", "MAX", "MAXIMO", "CAPA")
        capacidad = None
        try:
            if f_cap:
                capacidad = float(str(t.get(f_cap)).replace(",", "."))
        except Exception:
            capacidad = None

        # Descripciones (sanitizadas)
        desc_alma = None
        arti = t.get(f_idarti) if f_idarti else None
        salida.append({
            "almacen_id": str(alma) if alma is not None else None,
            "almacen_desc": None,
            "tanque_id": str(tanq) if tanq is not None else None,
            "producto_id": str(arti) if arti is not None else None,
            "producto_desc": None,
            "volumen": volumen,
            "litros15": litros15,
            "temperatura": temperatura,
            "capacidad": capacidad,
        })

    return salida

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/favicon.ico")
def favicon():
    return Response(status=204)

@app.route("/api/tanques_norm")
def api_tanques_norm():
    almacen = request.args.get("almacen")
    dbg = request.args.get("debug") == "1"
    base_dir = os.getcwd()
    try:
        data = load_tanques_norm(base_dir, almacen_filter=almacen, want_debug=dbg)
        return jsonify({"ok": True, "count": len(data), "tanques": data})
    except Exception as e:
        log.exception("Error en /api/tanques_norm")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/almacenes")
def api_almacenes():
    base_dir = os.getcwd()
    maestros = load_maestros(base_dir)
    rows = maestros.get("almacenes", [])
    # Sanitize
    def san(v):
        from datetime import date, datetime
        if isinstance(v, (int, float, bool)) or v is None:
            return v
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, bytes):
            try:
                return v.decode('latin-1')
            except Exception:
                return v.decode('utf-8', errors='ignore')
        return str(v)
    rows = [{k: san(v) for k, v in r.items()} for r in rows]
    return jsonify({"ok": True, "count": len(rows), "almacenes": rows})

@app.route("/api/articulos")
def api_articulos():
    base_dir = os.getcwd()
    maestros = load_maestros(base_dir)
    rows = maestros.get("articulos", [])
    def san(v):
        from datetime import date, datetime
        if isinstance(v, (int, float, bool)) or v is None:
            return v
        if isinstance(v, (datetime, date)):
            return v.isoformat()
        if isinstance(v, bytes):
            try:
                return v.decode('latin-1')
            except Exception:
                return v.decode('utf-8', errors='ignore')
        return str(v)
    rows = [{k: san(v) for k, v in r.items()} for r in rows]
    return jsonify({"ok": True, "count": len(rows), "articulos": rows})

@app.route("/api/where")
def api_where():
    return jsonify({"cwd": os.getcwd(), "files": sorted(os.listdir(os.getcwd()))})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    log.info(f"Iniciando servidor en http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=True)


@app.route("/api/ffcala/campos")
def api_ffcala_campos():
    base_dir = os.getcwd()
    try:
        rows = _read_dbf(os.path.join(base_dir, "FFCALA.DBF"))
        fields = list(rows[0].keys()) if rows else []
        # sample first 3 records for inspection (sanitized)
        def _san(v):
            from datetime import date, datetime
            if isinstance(v, (int, float, bool)) or v is None:
                return v
            if isinstance(v, (datetime, date)):
                return v.isoformat()
            if isinstance(v, bytes):
                try:
                    return v.decode('latin-1')
                except Exception:
                    return v.decode('utf-8', errors='ignore')
            return str(v)
        sample = [{k:_san(r.get(k)) for k in r.keys()} for r in rows[:3]]
        return jsonify({"ok": True, "fields": fields, "sample": sample, "count": len(rows)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# -*- coding: utf-8 -*-
import os, sys, logging, re, threading, webbrowser, time, hashlib, json
from datetime import datetime, timedelta
from functools import lru_cache
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

app = Flask(__name__, static_folder="static", template_folder="templates")

# ⚡ LOGGING OPTIMIZADO - Menos verboso durante carga
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("PROCONSI-Tanques")

# ⚡ Reducir logs de DBF durante carga masiva
logging.getLogger("dbfread").setLevel(logging.WARNING)

N_LAST = 5  # cuántas lecturas considerar

# CACHE INTELIGENTE ULTRA-OPTIMIZADO
class IntelligentCache:
    def __init__(self):
        self.data = {}
        self.file_hashes = {}
        self.last_check = {}
        self.index_cache = {}  # Para búsquedas rápidas
        
    def get_file_hash(self, filepath):
        """Hash ultra-rápido del archivo"""
        try:
            stat = os.stat(filepath)
            # ⚡ Solo usar mtime para máxima velocidad
            return str(stat.st_mtime)
        except:
            return None
    
    def should_reload(self, cache_key, filepath, max_age_seconds=30):
        """Determina si necesita recargar - ULTRA OPTIMIZADO"""
        now = time.time()
        
        # ⚡ Cache hit directo
        if cache_key not in self.data:
            return True
            
        # ⚡ Verificar solo cada max_age_seconds
        last_check = self.last_check.get(cache_key, 0)
        if now - last_check < max_age_seconds:
            return False
            
        # ⚡ Verificación rápida de archivo
        current_hash = self.get_file_hash(filepath)
        old_hash = self.file_hashes.get(cache_key)
        
        self.last_check[cache_key] = now
        
        if current_hash != old_hash:
            log.info(f"🔄 Detectado cambio en {os.path.basename(filepath)}")
            return True
            
        return False
    
    def set(self, cache_key, filepath, data):
        """Guarda en cache"""
        self.data[cache_key] = data
        self.file_hashes[cache_key] = self.get_file_hash(filepath)
        self.last_check[cache_key] = time.time()
    
    def get(self, cache_key):
        """Obtiene del cache"""
        return self.data.get(cache_key)

# Cache global
cache = IntelligentCache()

def base_dir():
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()

def _f(x):
    try:
        if x is None: return None
        return float(str(x).replace(',','.'))
    except Exception:
        return None

def _dt(fecha, hora):
    try:
        if fecha is None or hora is None: return None
        y,m,d = fecha.year, fecha.month, fecha.day
        s = re.sub(r'\D','', str(hora))
        s = (s or "0").zfill(6)[-6:]
        h,mi,se = int(s[:2]), int(s[2:4]), int(s[4:6])
        return datetime(y,m,d,h,mi,se)
    except Exception:
        return None

def _format_datetime(dt):
    """Formatea fecha/hora para mostrar en UI"""
    if dt is None:
        return None
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return None

def _color_hex_from_colorref(n):
    try:
        v = int(float(n)) & 0xFFFFFF
        r = v & 0xFF
        g = (v >> 8) & 0xFF
        b = (v >> 16) & 0xFF
        return f"#{r:02X}{g:02X}{b:02X}"
    except Exception:
        return "#CCCCCC"

def _norm(s):
    s = ("" if s is None else str(s)).strip()
    s2 = s.lstrip("0")
    return s if s2=="" else s2

def _almacenes_all():
    """Carga almacenes con cache inteligente - ULTRA OPTIMIZADO"""
    filepath = os.path.join(base_dir(), "FFALMA.DBF")
    cache_key = "almacenes"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=300):  # 5 min cache
        return cache.get(cache_key)
    
    try:
        t0 = time.time()
        
        # ⚡ List comprehension más rápida que loop tradicional
        rows = [
            {
                "codigo": str(r.get("CODIGO")), 
                "key": _norm(str(r.get("CODIGO"))), 
                "nombre": str(r.get("POBLACION") or "")
            }
            for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore')
            if r.get("CODIGO")  # ⚡ Filtro temprano
        ]
        
        # ⚡ Sort in-place más eficiente
        rows.sort(key=lambda x: x["codigo"] or "")
        
        cache.set(cache_key, filepath, rows)
        log.info(f"⚡ Almacenes: {len(rows)} en {time.time()-t0:.3f}s")
        return rows
        
    except Exception as e:
        log.error(f"❌ Error cargando almacenes: {e}")
        return cache.get(cache_key, [])

def _articulos():
    """Carga artículos con cache inteligente - ULTRA OPTIMIZADO"""
    filepath = os.path.join(base_dir(), "FFARTI.DBF")
    cache_key = "articulos"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=300):  # 5 min cache
        return cache.get(cache_key)
    
    try:
        t0 = time.time()
        
        # ⚡ Dict comprehension más rápida
        out = {
            str(r.get("CODIGO")): {
                "nombre": str(r.get("DESCRI") or ""), 
                "color": _color_hex_from_colorref(r.get("COLORPRODU"))
            }
            for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore')
            if r.get("CODIGO")  # ⚡ Filtro temprano
        }
        
        cache.set(cache_key, filepath, out)
        log.info(f"⚡ Artículos: {len(out)} en {time.time()-t0:.3f}s")
        return out
        
    except Exception as e:
        log.error(f"❌ Error cargando artículos: {e}")
        return cache.get(cache_key, {})

def _tanques_all():
    """Carga tanques con cache inteligente - ULTRA OPTIMIZADO"""
    filepath = os.path.join(base_dir(), "FFTANQ.DBF")
    cache_key = "tanques"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=300):  # 5 min cache
        return cache.get(cache_key)
    
    try:
        t0 = time.time()
        
        # ⚡ Procesamiento optimizado
        rows = []
        for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'):
            alma = str(r.get("ALMACEN") or r.get("CODALMA") or r.get("IDALMA") or "")
            if not alma:  # ⚡ Filtro temprano
                continue
                
            rows.append({
                "almacen": alma,
                "almacen_key": _norm(alma),
                "tanque": str(r.get("CODIGO")),
                "articulo": str(r.get("ARTICULO")),
                "nombre": str(r.get("DESCRI") or ""),
                "capacidad": _f(r.get("CAPACIDAD")),
            })
        
        # ⚡ Sort optimizado
        def sort_key(t):
            try: 
                return (t["almacen_key"], float(t["tanque"]))
            except: 
                return (t["almacen_key"], t["tanque"])
        
        rows.sort(key=sort_key)
        
        cache.set(cache_key, filepath, rows)
        log.info(f"⚡ Tanques: {len(rows)} en {time.time()-t0:.3f}s")
        return rows
        
    except Exception as e:
        log.error(f"❌ Error cargando tanques: {e}")
        return cache.get(cache_key, [])

def _preload_latest():
    """Carga FFCALA ULTRA-OPTIMIZADA con filtrado temprano y fechas"""
    filepath = os.path.join(base_dir(), "FFCALA.DBF")
    cache_key = "ffcala_latest"
    
    if not cache.should_reload(cache_key, filepath):
        cached_data = cache.get(cache_key)
        if cached_data:
            return cached_data["latest"], cached_data["by_almacen"]
    
    t0 = time.time()
    
    # ⚡ OPTIMIZACIÓN 1: Solo leer registros de los últimos 30 días
    fecha_limite = datetime.now() - timedelta(days=30)
    
    # ⚡ OPTIMIZACIÓN 2: Usar estructuras de datos más eficientes
    buffers = defaultdict(list)  # Más eficiente que .setdefault()
    
    registros_procesados = 0
    registros_validos = 0
    
    try:
        log.info(f"⚡ Leyendo FFCALA desde {fecha_limite.strftime('%d/%m/%Y')}...")
        
        # ⚡ OPTIMIZACIÓN 3: Leer y filtrar en una sola pasada
        for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'):
            registros_procesados += 1
            
            # ⚡ OPTIMIZACIÓN 4: Filtro temprano de fecha
            fecha = r.get("FECHA")
            if fecha and fecha < fecha_limite.date():
                continue  # Saltar registros muy antiguos
            
            almaKey = _norm(str(r.get("ALMACEN")))
            tanq = str(r.get("TANQUE"))
            
            # ⚡ OPTIMIZACIÓN 5: Validación rápida
            if not almaKey or not tanq:
                continue
                
            dt = _dt(fecha, r.get("HORA"))
            if dt is None: 
                continue
                
            # ⚡ OPTIMIZACIÓN 6: Solo crear objetos necesarios
            registro = {
                "dt": dt,
                "fecha": fecha,
                "hora": r.get("HORA"),
                "litros": _f(r.get("LITROS")),
                "litros15": _f(r.get("LITROS15")),
                "temperatura": _f(r.get("TEMPERA")),
            }
            
            buffers[(almaKey, tanq)].append(registro)
            registros_validos += 1
        
        log.info(f"⚡ Registros: {registros_procesados} leídos, {registros_validos} válidos en {time.time()-t0:.2f}s")
        
        # ⚡ OPTIMIZACIÓN 7: Procesamiento final optimizado
        t1 = time.time()
        latest = {}
        by_alm = defaultdict(dict)
        
        for (almaKey, tanq), rows in buffers.items():
            if len(rows) == 0:
                continue
                
            # ⚡ OPTIMIZACIÓN 8: Sort + slice en una operación
            rows.sort(key=lambda x: x["dt"], reverse=True)
            recent_rows = rows[:N_LAST]
            
            # ⚡ OPTIMIZACIÓN 9: Búsqueda de último valor no nulo optimizada
            v = next((r["litros"] for r in recent_rows if r["litros"] is not None), None)
            l15 = next((r["litros15"] for r in recent_rows if r["litros15"] is not None), None)
            te = next((r["temperatura"] for r in recent_rows if r["temperatura"] is not None), None)
            
            if v is None or l15 is None or te is None:
                continue
                
            # Fecha formateada del registro más reciente
            fecha_formateada = _format_datetime(recent_rows[0]["dt"])
            
            d = {
                "volumen": round(v), 
                "litros15": round(l15), 
                "temperatura": te, 
                "dt": recent_rows[0]["dt"],
                "fecha_ultimo_calado": fecha_formateada
            }
            
            latest[(almaKey, tanq)] = d
            by_alm[almaKey][tanq] = d
        
        # Convertir defaultdict a dict normal para cache
        by_alm = dict(by_alm)
        
        cached_data = {"latest": latest, "by_almacen": by_alm}
        cache.set(cache_key, filepath, cached_data)
        
        log.info(f"⚡ FFCALA procesado: {len(latest)} tanques válidos en {time.time()-t0:.3f}s (lectura: {t1-t0:.2f}s, procesamiento: {time.time()-t1:.2f}s)")
        return latest, by_alm
        
    except Exception as e:
        log.error(f"❌ Error procesando FFCALA: {e}")
        cached_data = cache.get(cache_key, {"latest": {}, "by_almacen": {}})
        return cached_data["latest"], cached_data["by_almacen"]

def _ensure_preloaded():
    try:
        return _preload_latest()
    except Exception as e:
        log.exception(f"Error precargando FFCALA: {e}")
        return {}, {}

def _almacenes_validos():
    latest, by_almacen = _ensure_preloaded()
    alma = _almacenes_all()
    name_by_key = {a["key"]: a["nombre"] for a in alma}
    canon_by_key = {a["key"]: a["codigo"] for a in alma}
    keys = sorted(by_almacen.keys())
    out = []
    for k in keys:
        if by_almacen.get(k):
            canon = canon_by_key.get(k, k)
            out.append({"codigo": canon, "nombre": name_by_key.get(k, "")})
    return out

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes():
    """API compatible con frontend - devuelve almacenes con tanques incluidos"""
    try:
        latest, by_almacen = _ensure_preloaded()
        alma_all = _almacenes_all()
        name_by_key = {a["key"]: a["nombre"] for a in alma_all}
        canon_by_key = {a["key"]: a["codigo"] for a in alma_all}
        key_by_canon = {_norm(a["codigo"]): a["key"] for a in alma_all}
        
        art = _articulos()
        tanques = _tanques_all()
        
        result = []
        
        # Para cada almacén que tiene datos
        for alma_key, latest_map in by_almacen.items():
            if not latest_map:  # Skip almacenes sin datos
                continue
                
            canon = canon_by_key.get(alma_key, alma_key)
            nombre = name_by_key.get(alma_key, "")
            
            # Obtener tanques de este almacén
            tanques_almacen = []
            for t in tanques:
                if t["almacen_key"] != alma_key: 
                    continue
                    
                c = latest_map.get(t["tanque"])
                if not c:
                    continue
                    
                a = art.get(t["articulo"], {"nombre": None, "color": "#CCCCCC"})
                
                tanque_data = {
                    "almacen": canon,
                    "codigo": t["tanque"],
                    "id": t["tanque"],
                    "nombre": t["nombre"],
                    "articulo": t["articulo"],
                    "articulo_nombre": a["nombre"],
                    "capacidad": t["capacidad"],
                    "nivel": c["volumen"],  # Para compatibilidad con frontend
                    "volumen": c["volumen"],
                    "litros15": c["litros15"],
                    "temperatura": c["temperatura"],
                    "fecha_ultimo_calado": c["fecha_ultimo_calado"],
                    "status": "ok",
                    "spark": [c["volumen"]],
                    "color": a["color"],
                    "colorProducto": a["color"],
                    "colorRGB": a["color"]
                }
                tanques_almacen.append(tanque_data)
            
            if tanques_almacen:  # Solo incluir almacenes con tanques
                result.append({
                    "codigo": canon,
                    "id": canon, 
                    "nombre": f"{canon} – {nombre}",
                    "poblacion": nombre,
                    "tanques": tanques_almacen
                })
        
        log.info(f"API /api/almacenes: {len(result)} almacenes con tanques")
        return jsonify(result)
        
    except Exception as e:
        log.error(f"Error en API almacenes: {e}")
        return jsonify([])

@app.route("/api/tanques_norm")
def api_tanques_norm():
    sel = request.args.get("almacen","")
    alma_all = _almacenes_all()
    key_by_canon = {_norm(a["codigo"]): a["key"] for a in alma_all}
    canon_by_key = {a["key"]: a["codigo"] for a in alma_all}

    latest, by_almacen = _ensure_preloaded()
    valid = _almacenes_validos()
    if not valid:
        return jsonify({"ok": True, "almacenes": [], "tanques": [], "resumen_productos": []})

    alma_key = _norm(sel) if sel else _norm(valid[0]["codigo"])
    # si viene canon, pasa a key
    alma_key = key_by_canon.get(alma_key, alma_key)
    canon = canon_by_key.get(alma_key, sel)

    latest_map = by_almacen.get(alma_key, {})
    art = _articulos()
    tanques = _tanques_all()
    out = []
    
    for t in tanques:
        if t["almacen_key"] != alma_key: 
            continue
        c = latest_map.get(t["tanque"])
        if not c:
            continue
        a = art.get(t["articulo"], {"nombre": None, "color": "#CCCCCC"})
        out.append({
            "almacen": canon,
            "tanque": t["tanque"],
            "tanque_nombre": t["nombre"],
            "producto": t["articulo"],
            "producto_nombre": a["nombre"],
            "producto_color": a["color"],
            "capacidad": t["capacidad"],
            "volumen": c["volumen"],
            "litros15": c["litros15"],
            "temperatura": c["temperatura"],
            "fecha_ultimo_calado": c["fecha_ultimo_calado"],  # ¡NUEVO CAMPO!
        })
    
    total = sum((x["litros15"] or 0) for x in out) or 1.0
    resumen = {}
    for x in out:
        r = resumen.setdefault(x["producto"], {
            "producto": x["producto"], 
            "producto_nombre": x["producto_nombre"], 
            "color_hex": x["producto_color"], 
            "total_litros15": 0.0, 
            "num_tanques": 0
        })
        r["total_litros15"] += x["litros15"] or 0
        r["num_tanques"] += 1
    
    for r in resumen.values():
        r["porcentaje"] = round((r["total_litros15"]/total)*100, 1)

    return jsonify({
        "ok": True, 
        "almacen": canon, 
        "almacenes": valid, 
        "tanques": out, 
        "resumen_productos": sorted(resumen.values(), key=lambda x: -x["total_litros15"])
    })

@app.route("/api/refresh")
def api_refresh():
    """Fuerza recarga inteligente solo de datos cambiados"""
    t0 = time.time()
    
    # ⚡ Solo limpiar cache de FFCALA (el que cambia más frecuentemente)
    if "ffcala_latest" in cache.data:
        del cache.data["ffcala_latest"]
    if "ffcala_latest" in cache.file_hashes:
        del cache.file_hashes["ffcala_latest"]
    
    # ⚡ Recargar solo si es necesario
    _ensure_preloaded()
    
    elapsed = time.time() - t0
    log.info(f"🔄 Refresco manual completado en {elapsed:.3f}s")
    
    return jsonify({
        "ok": True, 
        "message": f"Datos actualizados en {elapsed:.3f}s"
    })

@app.route("/api/status")
def api_status():
    """Endpoint ULTRA-RÁPIDO para verificar cambios"""
    try:
        # ⚡ Solo verificar si el cache está cargado, no recargar datos
        cached_data = cache.get("ffcala_latest")
        total_tanques = len(cached_data.get("latest", {})) if cached_data else 0
        
        # ⚡ Verificación rápida de solo el archivo principal
        filepath = os.path.join(base_dir(), "FFCALA.DBF")
        changes_detected = cache.should_reload("ffcala_latest", filepath, max_age_seconds=5)
        
        return jsonify({
            "ok": True,
            "total_tanques": total_tanques,
            "changes_detected": changes_detected,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/api/where")
def api_where():
    b = base_dir()
    try:
        files = sorted(os.listdir(b))
    except Exception:
        files = []
    return jsonify({"base_dir": b, "files": files})

@app.route("/favicon.ico")
def ico():
    return Response(status=204)

def open_browser_once(url):
    try: webbrowser.open(url, new=1, autoraise=True)
    except Exception: pass

def _startup():
    """Precarga optimizada con carga en paralelo conceptual"""
    log.info("🚀 Iniciando precarga optimizada...")
    t0 = time.time()
    
    try:
        # ⚡ Precargar archivos menos dinámicos primero (cache largo)
        _almacenes_all()
        _articulos()
        _tanques_all()
        
        # ⚡ FFCALA al final (el más pesado)
        _ensure_preloaded()
        
        log.info(f"✅ Precarga completada en {time.time()-t0:.3f}s")
        
    except Exception as e:
        log.error(f"❌ Error en startup: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    _startup()
    threading.Timer(0.5, open_browser_once, args=(url,)).start()
    log.info(f"🌐 Servidor iniciado en {url}")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

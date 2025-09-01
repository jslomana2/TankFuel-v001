# -*- coding: utf-8 -*-
import os, sys, logging, re, threading, webbrowser, time, hashlib, json
from datetime import datetime, timedelta
from functools import lru_cache
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

app = Flask(__name__, static_folder="static", template_folder="templates")

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("PROCONSI-Tanques")
logging.getLogger("dbfread").setLevel(logging.WARNING)

N_LAST = 5

# CACHE ULTRA-OPTIMIZADO
class UltraCache:
    def __init__(self):
        self.data = {}
        self.file_hashes = {}
        self.last_check = {}
        
    def get_file_hash(self, filepath):
        try:
            return str(os.path.getmtime(filepath))
        except:
            return None
    
    def should_reload(self, cache_key, filepath, max_age_seconds=30):
        now = time.time()
        
        if cache_key not in self.data:
            return True
            
        last_check = self.last_check.get(cache_key, 0)
        if now - last_check < max_age_seconds:
            return False
            
        current_hash = self.get_file_hash(filepath)
        old_hash = self.file_hashes.get(cache_key)
        self.last_check[cache_key] = now
        
        if current_hash != old_hash:
            log.info(f"Detectado cambio en {os.path.basename(filepath)}")
            return True
            
        return False
    
    def set(self, cache_key, filepath, data):
        self.data[cache_key] = data
        self.file_hashes[cache_key] = self.get_file_hash(filepath)
        self.last_check[cache_key] = time.time()
    
    def get(self, cache_key):
        return self.data.get(cache_key)

cache = UltraCache()

def base_dir():
    return os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()

def _f(x):
    try:
        if x is None: return None
        return float(str(x).replace(',','.'))
    except:
        return None

def _dt(fecha, hora):
    try:
        if fecha is None or hora is None: return None
        y,m,d = fecha.year, fecha.month, fecha.day
        s = re.sub(r'\D','', str(hora))
        s = (s or "0").zfill(6)[-6:]
        h,mi,se = int(s[:2]), int(s[2:4]), int(s[4:6])
        return datetime(y,m,d,h,mi,se)
    except:
        return None

def _format_datetime(dt):
    if dt is None: return None
    try:
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return None

# FUNCIÓN CORREGIDA PARA COLORES NÍTIDOS
def _color_hex_from_colorref(n):
    try:
        v = int(float(n)) & 0xFFFFFF
        r = v & 0xFF
        g = (v >> 8) & 0xFF
        b = (v >> 16) & 0xFF
        
        # CORREGIDO: Evitar colores muy claros o grises que se ven borrosos
        if (r > 220 and g > 220 and b > 220) or (abs(r-g) < 30 and abs(g-b) < 30 and abs(r-b) < 30):
            # Si es muy claro o muy gris, usar un color más vibrante basado en el valor original
            if v < 5000000:  # Valores bajos -> azul
                return "#2563eb"
            elif v < 10000000:  # Valores medios -> verde
                return "#059669" 
            else:  # Valores altos -> naranja
                return "#ea580c"
        
        return f"#{r:02X}{g:02X}{b:02X}"
    except:
        return "#2563eb"  # Azul vibrante por defecto

def _norm(s):
    s = ("" if s is None else str(s)).strip()
    s2 = s.lstrip("0")
    return s if s2=="" else s2

def _almacenes_all():
    filepath = os.path.join(base_dir(), "FFALMA.DBF")
    cache_key = "almacenes"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=300):
        return cache.get(cache_key)
    
    try:
        t0 = time.time()
        rows = [
            {
                "codigo": str(r.get("CODIGO")), 
                "key": _norm(str(r.get("CODIGO"))), 
                "nombre": str(r.get("POBLACION") or "")
            }
            for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore')
            if r.get("CODIGO")
        ]
        rows.sort(key=lambda x: x["codigo"] or "")
        cache.set(cache_key, filepath, rows)
        log.info(f"Almacenes: {len(rows)} en {time.time()-t0:.3f}s")
        return rows
    except Exception as e:
        log.error(f"Error cargando almacenes: {e}")
        return (cache.get(cache_key) or [])

def _articulos():
    filepath = os.path.join(base_dir(), "FFARTI.DBF")
    cache_key = "articulos"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=300):
        return cache.get(cache_key)
    
    try:
        t0 = time.time()
        out = {
            str(r.get("CODIGO")): {
                "nombre": str(r.get("DESCRI") or ""), 
                "color": _normalize_color(r.get("COLORPRODU"))
            }
            for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore')
            if r.get("CODIGO")
        }
        
        # DEBUG: Mostrar algunos colores para verificar
        for codigo, data in list(out.items())[:5]:
            log.info(f"Artículo {codigo}: color={data['color']}, nombre={data['nombre']}")
            
        cache.set(cache_key, filepath, out)
        log.info(f"Artículos: {len(out)} en {time.time()-t0:.3f}s")
        return out
    except Exception as e:
        log.error(f"Error cargando artículos: {e}")
        return (cache.get(cache_key) or {})

def _tanques_all():
    filepath = os.path.join(base_dir(), "FFTANQ.DBF")
    cache_key = "tanques"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=300):
        return cache.get(cache_key)
    
    try:
        t0 = time.time()
        rows = []
        for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'):
            alma = str(r.get("ALMACEN") or r.get("CODALMA") or r.get("IDALMA") or "")
            if not alma:
                continue
                
            rows.append({
                "almacen": alma,
                "almacen_key": _norm(alma),
                "tanque": str(r.get("CODIGO")),
                "articulo": str(r.get("ARTICULO")),
                "nombre": str(r.get("DESCRI") or ""),
                "capacidad": _f(r.get("CAPACIDAD")),
            })
        
        def sort_key(t):
            try: 
                return (t["almacen_key"], float(t["tanque"]))
            except: 
                return (t["almacen_key"], t["tanque"])
        
        rows.sort(key=sort_key)
        cache.set(cache_key, filepath, rows)
        log.info(f"Tanques: {len(rows)} en {time.time()-t0:.3f}s")
        return rows
    except Exception as e:
        log.error(f"Error cargando tanques: {e}")
        return (cache.get(cache_key) or [])

def _preload_latest_only():
    """ULTRA-RÁPIDO OPTIMIZADO: Solo última lectura de cada tanque"""
    filepath = os.path.join(base_dir(), "FFCALA.DBF")
    cache_key = "ffcala_latest_only"
    
    if not cache.should_reload(cache_key, filepath, max_age_seconds=60):
        return cache.get(cache_key)
    
    t0 = time.time()
    
    try:
        log.info("ULTRA-RÁPIDO OPTIMIZADO: Solo últimas lecturas...")
        
        # OPTIMIZACIÓN: Solo 1 día en lugar de 7 para máxima velocidad
        fecha_limite = datetime.now() - timedelta(days=1)
        latest_by_tanque = {}
        registros_procesados = 0
        
        # OPTIMIZACIÓN: Leer en orden inverso (más recientes primero)
        dbf_records = list(DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'))
        
        for r in reversed(dbf_records):  # Empezar por los más recientes
            registros_procesados += 1
            
            # OPTIMIZACIÓN: Salir si ya tenemos todos los tanques únicos
            if len(latest_by_tanque) >= 50:  # Máximo realista
                break
                
            fecha = r.get("FECHA")
            if fecha and fecha < fecha_limite.date():
                continue
            
            almaKey = _norm(str(r.get("ALMACEN")))
            tanq = str(r.get("TANQUE"))
            
            if not almaKey or not tanq:
                continue
                
            tanque_key = f"{almaKey}_{tanq}"
            
            # OPTIMIZACIÓN CLAVE: Si ya tenemos este tanque, seguir al siguiente
            if tanque_key in latest_by_tanque:
                continue
                
            dt = _dt(fecha, r.get("HORA"))
            if dt is None: 
                continue
            
            litros = _f(r.get("LITROS"))
            litros15 = _f(r.get("LITROS15"))
            temperatura = _f(r.get("TEMPERA"))
            
            if litros is not None and litros15 is not None:
                latest_by_tanque[tanque_key] = {
                    "volumen": round(litros), 
                    "litros15": round(litros15), 
                    "temperatura": temperatura or 0, 
                    "dt": dt,
                    "fecha_ultimo_calado": _format_datetime(dt)
                }
        
        elapsed = time.time() - t0
        log.info(f"ULTRA-RÁPIDO OPTIMIZADO: {registros_procesados:,} procesados, {len(latest_by_tanque)} tanques únicos en {elapsed:.3f}s")
        
        cache.set(cache_key, filepath, latest_by_tanque)
        return latest_by_tanque
        
    except Exception as e:
        log.error(f"Error en carga optimizada: {e}")
        return (cache.get(cache_key) or {})

@app.route("/")
def home():
    return render_template("sondastanques_mod.html")

@app.route("/api/almacenes")
def api_almacenes_fast():
    """API ULTRA-RÁPIDA - Solo últimas lecturas"""
    try:
        t0 = time.time()
        
        # Cargar datos básicos
        latest_by_tanque = _preload_latest_only()  # Ultra-rápido
        alma_all = _almacenes_all()
        art = _articulos()
        tanques = _tanques_all()
        
        # Crear índices rápidos
        name_by_key = {a["key"]: a["nombre"] for a in alma_all}
        canon_by_key = {a["key"]: a["codigo"] for a in alma_all}
        
        # Agrupar tanques por almacén
        almacenes_data = defaultdict(list)
        
        for t in tanques:
            alma_key = t["almacen_key"]
            tanque_key = f"{alma_key}_{t['tanque']}"
            
            calado = latest_by_tanque.get(tanque_key)
            if not calado:
                calado = {
                    'volumen': 0.0,
                    'litros15': 0.0,
                    'temperatura': None,
                    'fecha_ultimo_calado': None
                }
                
            a = art.get(t["articulo"], {"nombre": None, "color": "#2563eb"})  # CORREGIDO: Color por defecto más vibrante
            
            tanque_data = {
                "almacen": canon_by_key.get(alma_key, alma_key),
                "codigo": t["tanque"],
                "id": t["tanque"],
                "nombre": t["nombre"],
                "articulo": t["articulo"],
                "articulo_nombre": a["nombre"],
                "capacidad": t["capacidad"],
                "nivel": calado["volumen"],
                "volumen": calado["volumen"],
                "litros15": calado["litros15"],
                "temperatura": calado["temperatura"],
                "fecha_ultimo_calado": calado["fecha_ultimo_calado"],
                "status": "ok",
                "spark": [calado["volumen"]],
                "color": a["color"],  # ESTE COLOR VIENE DEL CAMPO COLORPRODU
                "colorProducto": a["color"],
                "colorRGB": a["color"]
            }
            almacenes_data[alma_key].append(tanque_data)
        
        # Construir respuesta final
        result = []
        for alma_key, tanques_list in almacenes_data.items():
            if not tanques_list:
                continue
                
            canon = canon_by_key.get(alma_key, alma_key)
            nombre = name_by_key.get(alma_key, "")
            
            result.append({
                "codigo": canon,
                "id": canon, 
                "nombre": f"{canon} — {nombre}",
                "poblacion": nombre,
                "tanques": tanques_list
            })
        
        elapsed = time.time() - t0
        log.info(f"API ULTRA-RÁPIDA: {len(result)} almacenes en {elapsed:.3f}s")
        return jsonify(result)
        
    except Exception as e:
        log.error(f"Error en API ultra-rápida: {e}")
        return jsonify([])

@app.route("/api/tanque_historico")
def api_tanque_historico():
    """API para datos históricos de un tanque específico"""
    almacen = request.args.get("almacen", "")
    tanque = request.args.get("tanque", "")
    from_date = request.args.get("from", "")
    to_date = request.args.get("to", "")
    
    if not almacen or not tanque:
        return jsonify({"error": "Se requiere almacen y tanque"}), 400
    
    try:
        t0 = time.time()
        
        # Fechas de filtro
        if from_date:
            fecha_desde = datetime.strptime(from_date, "%Y-%m-%d")
        else:
            fecha_desde = datetime.now() - timedelta(days=30)
            
        if to_date:
            fecha_hasta = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        else:
            fecha_hasta = datetime.now()
        
        # Leer histórico del tanque específico
        filepath = os.path.join(base_dir(), "FFCALA.DBF")
        almaKey = _norm(almacen)
        
        registros = []
        
        for r in DBF(filepath, ignore_missing_memofile=True, recfactory=dict, char_decode_errors='ignore'):
            # Filtros rápidos
            if _norm(str(r.get("ALMACEN"))) != almaKey:
                continue
            if str(r.get("TANQUE")) != tanque:
                continue
                
            fecha = r.get("FECHA")
            if not fecha:
                continue
                
            dt = _dt(fecha, r.get("HORA"))
            if not dt or dt < fecha_desde or dt > fecha_hasta:
                continue
            
            litros = _f(r.get("LITROS"))
            litros15 = _f(r.get("LITROS15"))
            temperatura = _f(r.get("TEMPERA"))
            
            if litros is not None:
                registros.append({
                    "fecha": dt.strftime("%Y-%m-%d"),
                    "hora": dt.strftime("%H:%M"),
                    "timestamp": dt.isoformat(),
                    "volumen": round(litros),
                    "litros15": round(litros15 or 0),
                    "temperatura": round(temperatura or 0, 1)
                })
        
        # Ordenar por fecha más reciente primero
        registros.sort(key=lambda x: x["timestamp"], reverse=True)
        
        elapsed = time.time() - t0
        log.info(f"Histórico {almacen}/{tanque}: {len(registros)} registros en {elapsed:.3f}s")
        
        return jsonify({
            "almacen": almacen,
            "tanque": tanque,
            "registros": registros,
            "count": len(registros)
        })
        
    except Exception as e:
        log.error(f"Error en histórico: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/refresh")
def api_refresh():
    t0 = time.time()
    
    # Limpiar solo cache de lecturas
    if "ffcala_latest_only" in cache.data:
        del cache.data["ffcala_latest_only"]
    if "ffcala_latest_only" in cache.file_hashes:
        del cache.file_hashes["ffcala_latest_only"]
    
    _preload_latest_only()
    
    elapsed = time.time() - t0
    log.info(f"Refresco ultra-rápido completado en {elapsed:.3f}s")
    
    return jsonify({
        "ok": True, 
        "message": f"Datos actualizados en {elapsed:.3f}s"
    })

@app.route("/api/status")
def api_status():
    try:
        cached_data = cache.get("ffcala_latest_only")
        total_tanques = len(cached_data or {})
        
        filepath = os.path.join(base_dir(), "FFCALA.DBF")
        changes_detected = cache.should_reload("ffcala_latest_only", filepath, max_age_seconds=5)
        
        return jsonify({
            "ok": True,
            "total_tanques": total_tanques,
            "changes_detected": changes_detected,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

@app.route("/favicon.ico")
def ico():
    return Response(status=204)

def open_browser_once(url):
    try: 
        webbrowser.open(url, new=1, autoraise=True)
    except: 
        pass

def _startup():
    log.info("Iniciando sistema ultra-rápido...")
    t0 = time.time()
    
    try:
        _almacenes_all()
        _articulos()
        _tanques_all()
        _preload_latest_only()  # Solo últimas lecturas
        
        log.info(f"Sistema listo en {time.time()-t0:.3f}s")
    except Exception as e:
        log.error(f"Error en startup: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    url = f"http://127.0.0.1:{port}"
    _startup()
    threading.Timer(0.5, open_browser_once, args=(url,)).start()
    log.info(f"Servidor ultra-rápido iniciado en {url}")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

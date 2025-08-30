# -*- coding: utf-8 -*-
import os, sys, logging, re, threading, webbrowser, time, hashlib, json
from datetime import datetime, timedelta
from functools import lru_cache
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

# Configuración de logging optimizada para velocidad
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = Flask(__name__)

class UltraFastCache:
    """Cache ultra-optimizado con TTL variable por tipo de dato"""
    def __init__(self):
        self.data = {}
        self.timestamps = {}
        self.ttls = {
            'almacenes': 600,      # 10 minutos (raramente cambian)
            'articulos': 600,      # 10 minutos (raramente cambian)  
            'tanques': 600,        # 10 minutos (raramente cambian)
            'ffcala_latest': 300,  # 5 minutos (cambian frecuentemente)
            'file_mtime': 120      # 2 minutos para metadatos de archivo
        }
    
    def get(self, key, default=None):
        """Obtiene valor del cache si no ha expirado"""
        if key not in self.data:
            return default
            
        # Verificar TTL específico por tipo de dato
        cache_type = key.split('_')[0] if '_' in key else 'default'
        ttl = self.ttls.get(cache_type, 60)  # Default 1 minuto
        
        if time.time() - self.timestamps.get(key, 0) > ttl:
            # Expirado - limpiar
            self.data.pop(key, None)
            self.timestamps.pop(key, None)
            return default
            
        return self.data[key]
    
    def set(self, key, value):
        """Almacena valor en cache con timestamp"""
        self.data[key] = value
        self.timestamps[key] = time.time()
    
    def clear_type(self, cache_type):
        """Limpia solo un tipo de cache específico"""
        keys_to_remove = [k for k in self.data.keys() if k.startswith(cache_type)]
        for key in keys_to_remove:
            self.data.pop(key, None)
            self.timestamps.pop(key, None)

# Cache ultra-optimizado
cache = UltraFastCache()

def get_file_signature(filepath):
    """Obtiene signature ultra-rápida del archivo (solo mtime)"""
    try:
        cache_key = f"file_mtime_{filepath}"
        
        # Verificar cache de metadatos
        cached_mtime = cache.get(cache_key)
        current_mtime = os.path.getmtime(filepath)
        
        if cached_mtime == current_mtime:
            return cached_mtime  # No cambió
            
        # Actualizar cache de metadatos
        cache.set(cache_key, current_mtime)
        return current_mtime
        
    except Exception as e:
        logging.warning(f"Error obteniendo signature de {filepath}: {e}")
        return time.time()  # Fallback

def ultra_fast_dbf_read(filepath, **kwargs):
    """Lectura ultra-optimizada de DBF con parámetros de rendimiento"""
    try:
        # Parámetros optimizados para velocidad
        dbf_params = {
            'ignore_missing_memofile': True,  # Ignore memo files for speed
            'char_decode_errors': 'ignore',   # Skip decode errors
            'encoding': 'latin1',             # Fast encoding
            **kwargs
        }
        
        return DBF(filepath, **dbf_params)
    except Exception as e:
        logging.error(f"Error leyendo DBF {filepath}: {e}")
        return []

def _load_almacenes():
    """Carga ultra-rápida de almacenes con cache inteligente"""
    dbf_path = "FFALMA.DBF"
    if not os.path.exists(dbf_path):
        logging.warning(f"Archivo {dbf_path} no encontrado")
        return []
    
    # Verificar cache
    file_sig = get_file_signature(dbf_path)
    cache_key = f"almacenes_{file_sig}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    try:
        t0 = time.time()
        almacenes = []
        
        for record in ultra_fast_dbf_read(dbf_path):
            # Filtrado ultra-rápido con validación mínima
            codigo = (record.get('CODIGO') or '').strip()
            if not codigo:
                continue
                
            almacenes.append({
                'id': codigo,
                'codigo': codigo,
                'nombre': (record.get('NOMBRE') or '').strip(),
                'poblacion': (record.get('POBLACION') or '').strip(),
                'tanques': []
            })
        
        elapsed = time.time() - t0
        cache.set(cache_key, almacenes)
        logging.info(f"⚡ Almacenes: {len(almacenes)} en {elapsed:.3f}s")
        return almacenes
        
    except Exception as e:
        logging.error(f"Error cargando almacenes: {e}")
        return []

def _load_articulos():
    """Carga ultra-rápida de artículos con cache inteligente"""
    dbf_path = "FFARTI.DBF"
    if not os.path.exists(dbf_path):
        logging.warning(f"Archivo {dbf_path} no encontrado")
        return {}
    
    # Verificar cache
    file_sig = get_file_signature(dbf_path)
    cache_key = f"articulos_{file_sig}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    try:
        t0 = time.time()
        articulos = {}
        
        for record in ultra_fast_dbf_read(dbf_path):
            # Procesamiento ultra-rápido
            codigo = (record.get('CODIGO') or '').strip()
            if codigo:
                articulos[codigo] = (record.get('NOMBRE') or '').strip()
        
        elapsed = time.time() - t0
        cache.set(cache_key, articulos)
        logging.info(f"⚡ Artículos: {len(articulos)} en {elapsed:.3f}s")
        return articulos
        
    except Exception as e:
        logging.error(f"Error cargando artículos: {e}")
        return {}

def _load_tanques():
    """Carga ultra-rápida de tanques con cache inteligente"""
    dbf_path = "FFTANQ.DBF"
    if not os.path.exists(dbf_path):
        logging.warning(f"Archivo {dbf_path} no encontrado")
        return {}
    
    # Verificar cache
    file_sig = get_file_signature(dbf_path)
    cache_key = f"tanques_{file_sig}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    try:
        t0 = time.time()
        tanques = {}
        
        for record in ultra_fast_dbf_read(dbf_path):
            # Validación y procesamiento ultra-rápido
            codigo = (record.get('CODIGO') or '').strip()
            almacen = (record.get('ALMACEN') or '').strip()
            
            if not codigo or not almacen:
                continue
                
            tanque_info = {
                'id': codigo,
                'codigo': codigo,
                'almacen': almacen,
                'nombre': (record.get('NOMBRE') or '').strip(),
                'articulo': (record.get('ARTICULO') or '').strip(),
                'capacidad': float(record.get('CAPACIDAD') or 0),
                'nivel_min': float(record.get('NIVEL_MIN') or 0),
                'nivel_max': float(record.get('NIVEL_MAX') or 0),
                'diametro': float(record.get('DIAMETRO') or 0)
            }
            
            if almacen not in tanques:
                tanques[almacen] = []
            tanques[almacen].append(tanque_info)
        
        elapsed = time.time() - t0
        cache.set(cache_key, tanques)
        logging.info(f"⚡ Tanques: {sum(len(v) for v in tanques.values())} en {elapsed:.3f}s")
        return tanques
        
    except Exception as e:
        logging.error(f"Error cargando tanques: {e}")
        return {}

def _preload_latest_ultra():
    """Precarga ULTRA-OPTIMIZADA de últimos calados (solo 15 días)"""
    dbf_path = "FFCALA.DBF"
    if not os.path.exists(dbf_path):
        logging.warning(f"Archivo {dbf_path} no encontrado")
        return {}
    
    # Verificar cache
    file_sig = get_file_signature(dbf_path)
    cache_key = f"ffcala_latest_{file_sig}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    try:
        # OPTIMIZACIÓN CLAVE: Solo últimos 15 días (en lugar de 30)
        cutoff_date = datetime.now() - timedelta(days=15)
        cutoff_str = cutoff_date.strftime('%d/%m/%Y')
        
        t0 = time.time()
        logging.info(f"⚡ Leyendo FFCALA desde {cutoff_str}... (ULTRA-RÁPIDO)")
        
        # Contadores para estadísticas
        total_records = 0
        valid_records = 0
        data_by_tanque = defaultdict(list)
        
        # Lectura ultra-optimizada con early filtering
        for record in ultra_fast_dbf_read(dbf_path):
            total_records += 1
            
            # FILTRO TEMPRANO ULTRA-RÁPIDO: Fecha
            fecha = record.get('FECHA')
            if not fecha or fecha < cutoff_date:
                continue
            
            # FILTRO TEMPRANO: Campos obligatorios
            almacen = (record.get('ALMACEN') or '').strip()
            tanque = (record.get('TANQUE') or '').strip()
            
            if not almacen or not tanque:
                continue
            
            # VALIDACIÓN ULTRA-RÁPIDA de datos numéricos
            try:
                nivel = float(record.get('NIVEL') or 0)
                if nivel < 0:
                    continue
            except (ValueError, TypeError):
                continue
            
            valid_records += 1
            
            # Crear registro ultra-compacto
            tanque_key = f"{almacen}_{tanque}"
            hora = record.get('HORA') or datetime.min.time()
            
            calado_data = {
                'fecha': fecha,
                'hora': hora,
                'nivel': nivel,
                'temperatura': float(record.get('TEMPERATURA') or 0),
                'densidad': float(record.get('DENSIDAD') or 0),
                'volumen': float(record.get('VOLUMEN') or 0),
                'masa': float(record.get('MASA') or 0),
                'agua': float(record.get('AGUA') or 0),
                'timestamp': datetime.combine(fecha, hora)
            }
            
            data_by_tanque[tanque_key].append(calado_data)
        
        read_time = time.time() - t0
        
        # PROCESAMIENTO ULTRA-RÁPIDO: Solo el último calado por tanque
        t1 = time.time()
        latest_by_tanque = {}
        
        for tanque_key, calados in data_by_tanque.items():
            if calados:
                # Obtener el más reciente (ya ordenado por iteración)
                latest = max(calados, key=lambda x: x['timestamp'])
                
                # Formatear fecha para mostrar
                latest['fecha_formatted'] = latest['fecha'].strftime('%d/%m/%Y')
                latest['hora_formatted'] = latest['hora'].strftime('%H:%M')
                latest['fecha_ultimo_calado'] = f"{latest['fecha_formatted']} {latest['hora_formatted']}"
                
                latest_by_tanque[tanque_key] = latest
        
        process_time = time.time() - t1
        total_time = time.time() - t0
        
        # Estadísticas de rendimiento
        logging.info(f"⚡ Registros: {total_records} leídos, {valid_records} válidos en {read_time:.2f}s")
        logging.info(f"⚡ FFCALA procesado: {len(latest_by_tanque)} tanques válidos en {total_time:.3f}s (lectura: {read_time:.2f}s, procesamiento: {process_time:.3f}s)")
        
        # Cache con TTL extendido para FFCALA
        cache.set(cache_key, latest_by_tanque)
        return latest_by_tanque
        
    except Exception as e:
        logging.error(f"Error en precarga ultra-rápida: {e}")
        return {}

def _startup_preload():
    """Precarga inicial ultra-optimizada al startup"""
    logging.info("🚀 Iniciando precarga ultra-optimizada...")
    start_time = time.time()
    
    # Cargar en paralelo conceptual (secuencial pero optimizado)
    almacenes = _load_almacenes()
    articulos = _load_articulos()  
    tanques_by_almacen = _load_tanques()
    latest_calados = _preload_latest_ultra()
    
    # Ensamblar datos ultra-rápido
    almacenes_dict = {a['codigo']: a for a in almacenes}
    
    for almacen_code, tanque_list in tanques_by_almacen.items():
        if almacen_code not in almacenes_dict:
            continue
            
        almacen_obj = almacenes_dict[almacen_code]
        
        for tanque in tanque_list:
            tanque_key = f"{almacen_code}_{tanque['codigo']}"
            
            # Datos del último calado
            ultimo_calado = latest_calados.get(tanque_key, {})
            
            # Ensamblar tanque completo
            tanque.update({
                'nivel': ultimo_calado.get('nivel', 0),
                'volumen': ultimo_calado.get('volumen', 0),
                'temperatura': ultimo_calado.get('temperatura', 0),
                'densidad': ultimo_calado.get('densidad', 0),
                'masa': ultimo_calado.get('masa', 0),
                'agua': ultimo_calado.get('agua', 0),
                'fecha_ultimo_calado': ultimo_calado.get('fecha_ultimo_calado', 'Sin datos'),
                'status': 'ok',
                'spark': [ultimo_calado.get('nivel', 0)] if ultimo_calado else []
            })
            
            # Nombre del artículo
            if tanque['articulo'] in articulos:
                tanque['articulo_nombre'] = articulos[tanque['articulo']]
        
        almacen_obj['tanques'] = tanque_list
    
    # Solo almacenes con tanques
    almacenes_final = [a for a in almacenes if a['tanques']]
    
    total_time = time.time() - start_time
    logging.info(f"✅ Precarga ultra-optimizada completada en {total_time:.3f}s")
    
    return almacenes_final

# Variables globales
ALMACENES_DATA = []

def init_data():
    """Inicialización de datos al arranque"""
    global ALMACENES_DATA
    ALMACENES_DATA = _startup_preload()

# BACKGROUND REFRESH SYSTEM
class BackgroundRefresher:
    """Sistema de refresco en background ultra-inteligente"""
    def __init__(self):
        self.thread = None
        self.running = False
        self.last_refresh = time.time()
    
    def start(self):
        """Inicia el refresco en background"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.thread.start()
        logging.info("🔄 Background refresh activado")
    
    def _refresh_loop(self):
        """Loop de refresco inteligente cada 3 minutos"""
        while self.running:
            try:
                time.sleep(180)  # 3 minutos
                
                # Solo refrescar FFCALA (los otros rara vez cambian)
                logging.info("🔄 Background refresh: Verificando FFCALA...")
                
                # Verificar si cambió el archivo
                dbf_path = "FFCALA.DBF"
                if os.path.exists(dbf_path):
                    current_mtime = os.path.getmtime(dbf_path)
                    cached_mtime = cache.get(f"file_mtime_{dbf_path}")
                    
                    if cached_mtime != current_mtime:
                        logging.info("🔄 FFCALA cambió, actualizando cache...")
                        cache.clear_type('ffcala')
                        _preload_latest_ultra()  # Recargar solo FFCALA
                        logging.info("✅ Background refresh completado")
                    else:
                        logging.info("🔄 FFCALA sin cambios")
                        
            except Exception as e:
                logging.error(f"Error en background refresh: {e}")

# Instancia global del refresher
bg_refresher = BackgroundRefresher()

# ================== ROUTES ==================

@app.route('/')
def index():
    return render_template('sondastanques_mod.html')

@app.route('/api/almacenes')
def api_almacenes():
    """API ultra-rápida para almacenes"""
    try:
        return jsonify(ALMACENES_DATA)
    except Exception as e:
        logging.error(f"Error en API almacenes: {e}")
        return jsonify([])

@app.route("/api/status")
def api_status():
    """Endpoint ultra-rápido para verificar cambios (solo metadatos)"""
    try:
        status = {
            'timestamp': int(time.time() * 1000),
            'cache_info': {
                'almacenes': len(cache.get('almacenes', [])),
                'ffcala_cached': 'ffcala_latest' in cache.data,
                'last_refresh': bg_refresher.last_refresh
            }
        }
        
        # Verificar rápidamente si FFCALA cambió
        dbf_path = "FFCALA.DBF"
        if os.path.exists(dbf_path):
            current_mtime = os.path.getmtime(dbf_path)
            cached_mtime = cache.get(f"file_mtime_{dbf_path}")
            status['ffcala_changed'] = (cached_mtime != current_mtime)
        
        return jsonify(status)
        
    except Exception as e:
        logging.error(f"Error en API status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/refresh")
def api_refresh():
    """Fuerza recarga ultra-inteligente solo de datos cambiados"""
    global ALMACENES_DATA
    
    try:
        t0 = time.time()
        
        # ⚡ Limpiar solo cache de FFCALA (el más volátil)
        cache.clear_type('ffcala')
        
        # Recargar datos completos
        ALMACENES_DATA = _startup_preload()
        
        elapsed = time.time() - t0
        
        return jsonify({
            'success': True,
            'message': f'Datos refrescados en {elapsed:.2f}s',
            'almacenes_count': len(ALMACENES_DATA),
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logging.error(f"Error en refresh: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ================== STARTUP ==================

if __name__ == '__main__':
    # Inicialización ultra-optimizada
    init_data()
    
    # Activar background refresh
    bg_refresher.start()
    
    # Abrir navegador automáticamente
    threading.Timer(1.0, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    
    logging.info("🌐 Servidor ultra-optimizado iniciado en http://127.0.0.1:5000")
    
    # Ejecutar con Waitress (más rápido que el dev server de Flask)
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        # Fallback a Flask dev server
        app.run(host='127.0.0.1', port=5000, debug=False)

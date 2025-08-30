# -*- coding: utf-8 -*-
import os, sys, logging, re, threading, webbrowser, time, hashlib, json
from datetime import datetime, timedelta
from functools import lru_cache
from collections import defaultdict
from flask import Flask, jsonify, render_template, request, Response
from dbfread import DBF

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = Flask(__name__)

# Cache simple pero efectivo
CACHE = {}
CACHE_TTL = {}

def simple_cache_get(key, ttl_seconds=300):
    """Cache simple con TTL"""
    if key in CACHE:
        if time.time() - CACHE_TTL.get(key, 0) < ttl_seconds:
            return CACHE[key]
        else:
            # Expirado
            CACHE.pop(key, None)
            CACHE_TTL.pop(key, None)
    return None

def simple_cache_set(key, value):
    """Guardar en cache"""
    CACHE[key] = value
    CACHE_TTL[key] = time.time()

def load_almacenes():
    """Carga almacenes con cache"""
    cached = simple_cache_get('almacenes', 600)  # 10 min
    if cached is not None:
        logging.info("Cache hit: almacenes")
        return cached
    
    dbf_path = "FFALMA.DBF"
    if not os.path.exists(dbf_path):
        logging.error(f"Archivo {dbf_path} no encontrado")
        return []
    
    try:
        t0 = time.time()
        almacenes = []
        
        for record in DBF(dbf_path, ignore_missing_memofile=True):
            codigo = (record.get('CODIGO') or '').strip()
            if codigo:
                almacenes.append({
                    'id': codigo,
                    'codigo': codigo,
                    'nombre': (record.get('NOMBRE') or '').strip(),
                    'poblacion': (record.get('POBLACION') or '').strip(),
                    'tanques': []
                })
        
        elapsed = time.time() - t0
        simple_cache_set('almacenes', almacenes)
        logging.info(f"Almacenes: {len(almacenes)} cargados en {elapsed:.3f}s")
        return almacenes
        
    except Exception as e:
        logging.error(f"Error cargando almacenes: {e}")
        return []

def load_articulos():
    """Carga artículos con cache"""
    cached = simple_cache_get('articulos', 600)  # 10 min
    if cached is not None:
        logging.info("Cache hit: articulos")
        return cached
    
    dbf_path = "FFARTI.DBF"
    if not os.path.exists(dbf_path):
        logging.error(f"Archivo {dbf_path} no encontrado")
        return {}
    
    try:
        t0 = time.time()
        articulos = {}
        
        for record in DBF(dbf_path, ignore_missing_memofile=True):
            codigo = (record.get('CODIGO') or '').strip()
            nombre = (record.get('NOMBRE') or '').strip()
            if codigo:
                articulos[codigo] = nombre
        
        elapsed = time.time() - t0
        simple_cache_set('articulos', articulos)
        logging.info(f"Artículos: {len(articulos)} cargados en {elapsed:.3f}s")
        return articulos
        
    except Exception as e:
        logging.error(f"Error cargando artículos: {e}")
        return {}

def load_tanques():
    """Carga tanques con cache"""
    cached = simple_cache_get('tanques', 600)  # 10 min
    if cached is not None:
        logging.info("Cache hit: tanques")
        return cached
    
    dbf_path = "FFTANQ.DBF"
    if not os.path.exists(dbf_path):
        logging.error(f"Archivo {dbf_path} no encontrado")
        return {}
    
    try:
        t0 = time.time()
        tanques = {}
        
        for record in DBF(dbf_path, ignore_missing_memofile=True):
            codigo = (record.get('CODIGO') or '').strip()
            almacen = (record.get('ALMACEN') or '').strip()
            
            if codigo and almacen:
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
        total = sum(len(v) for v in tanques.values())
        simple_cache_set('tanques', tanques)
        logging.info(f"Tanques: {total} cargados en {elapsed:.3f}s")
        return tanques
        
    except Exception as e:
        logging.error(f"Error cargando tanques: {e}")
        return {}

def load_calados():
    """Carga calados (últimos 15 días) con cache"""
    cached = simple_cache_get('calados', 300)  # 5 min
    if cached is not None:
        logging.info("Cache hit: calados")
        return cached
    
    dbf_path = "FFCALA.DBF"
    if not os.path.exists(dbf_path):
        logging.error(f"Archivo {dbf_path} no encontrado")
        return {}
    
    try:
        cutoff_date = datetime.now() - timedelta(days=15)
        logging.info(f"Cargando calados desde {cutoff_date.strftime('%d/%m/%Y')}")
        
        t0 = time.time()
        data_by_tanque = defaultdict(list)
        total_records = 0
        valid_records = 0
        
        for record in DBF(dbf_path, ignore_missing_memofile=True):
            total_records += 1
            
            # Progress cada 50k registros
            if total_records % 50000 == 0:
                logging.info(f"Procesando... {total_records:,} registros")
            
            # Validar fecha
            fecha = record.get('FECHA')
            if not fecha:
                continue
            
            # Convertir fecha a date para comparar
            try:
                if isinstance(fecha, datetime):
                    fecha_date = fecha.date()
                elif isinstance(fecha, str):
                    fecha_date = datetime.strptime(fecha, '%d/%m/%Y').date()
                else:
                    fecha_date = fecha
            except:
                continue
                
            if fecha_date < cutoff_date.date():
                continue
            
            # Validar campos básicos
            almacen = (record.get('ALMACEN') or '').strip()
            tanque = (record.get('TANQUE') or '').strip()
            
            if not almacen or not tanque:
                continue
            
            try:
                nivel = float(record.get('NIVEL') or 0)
                if nivel < 0:
                    continue
            except:
                continue
            
            valid_records += 1
            
            # Procesar hora
            hora_raw = record.get('HORA')
            try:
                if isinstance(hora_raw, str):
                    if ':' in hora_raw:
                        hora = datetime.strptime(hora_raw, '%H:%M:%S').time()
                    else:
                        hora = datetime.min.time()
                elif hasattr(hora_raw, 'time'):
                    hora = hora_raw.time()
                else:
                    hora = datetime.min.time()
            except:
                hora = datetime.min.time()
            
            # Debug: mostrar algunos registros para diagnóstico
            if valid_records <= 5:
                logging.info(f"Debug registro {valid_records}: Almacén={almacen}, Tanque={tanque}, Fecha={fecha_date}, Hora={hora}")
                logging.info(f"  VOLUMEN raw: '{record.get('VOLUMEN')}', NIVEL raw: '{record.get('NIVEL')}'")
                logging.info(f"  TEMPERATURA raw: '{record.get('TEMPERATURA')}', Todos los campos: {list(record.keys())[:10]}")
            
            # Procesar campos numéricos con mejor manejo
            try:
                volumen = float(record.get('VOLUMEN') or record.get('Litros') or record.get('LITROS') or 0)
            except:
                volumen = 0.0
                
            try:
                temperatura = float(record.get('TEMPERATURA') or record.get('Tempera') or 0)
            except:
                temperatura = 0.0
            
            # Crear registro
            tanque_key = f"{almacen}_{tanque}"
            timestamp = datetime.combine(fecha_date, hora)
            
            calado_data = {
                'fecha': fecha_date,
                'hora': hora,
                'nivel': nivel,
                'volumen': volumen,
                'temperatura': temperatura,
                'timestamp': timestamp,
                'fecha_ultimo_calado': f"{fecha_date.strftime('%d/%m/%Y')} {hora.strftime('%H:%M')}"
            }
            
            if valid_records <= 5:
                logging.info(f"  Calado procesado: Volumen={volumen}, Nivel={nivel}, Temp={temperatura}")
            
            data_by_tanque[tanque_key].append(calado_data)
        
        # Obtener solo el último calado por tanque
        latest_by_tanque = {}
        for tanque_key, calados in data_by_tanque.items():
            if calados:
                latest = max(calados, key=lambda x: x['timestamp'])
                latest_by_tanque[tanque_key] = latest
        
        elapsed = time.time() - t0
        logging.info(f"Calados: {total_records:,} registros leídos, {valid_records:,} válidos, {len(latest_by_tanque)} tanques procesados en {elapsed:.2f}s")
        
        simple_cache_set('calados', latest_by_tanque)
        return latest_by_tanque
        
    except Exception as e:
        logging.error(f"Error cargando calados: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return {}

def build_full_data():
    """Construye la estructura completa de datos"""
    logging.info("🔄 Construyendo estructura de datos...")
    
    # Cargar todos los datos
    almacenes = load_almacenes()
    articulos = load_articulos()
    tanques_by_almacen = load_tanques()
    calados = load_calados()
    
    # Ensamblar datos
    almacenes_dict = {a['codigo']: a for a in almacenes}
    logging.info(f"Almacenes dict creado: {list(almacenes_dict.keys())}")
    logging.info(f"Tanques por almacén: {list(tanques_by_almacen.keys())}")
    
    for almacen_code, tanque_list in tanques_by_almacen.items():
        logging.info(f"Procesando almacén: {almacen_code} con {len(tanque_list)} tanques")
        
        if almacen_code not in almacenes_dict:
            logging.warning(f"Almacén {almacen_code} no encontrado en lista de almacenes")
            continue
        
        almacen_obj = almacenes_dict[almacen_code]
        
        for tanque in tanque_list:
            tanque_key = f"{almacen_code}_{tanque['codigo']}"
            calado = calados.get(tanque_key, {})
            
            # Enriquecer tanque con datos de calado
            tanque.update({
                'nivel': calado.get('nivel', 0),
                'volumen': calado.get('volumen', 0),
                'temperatura': calado.get('temperatura', 0),
                'fecha_ultimo_calado': calado.get('fecha_ultimo_calado', 'Sin datos'),
                'status': 'ok',
                'spark': [calado.get('nivel', 0)] if calado else []
            })
            
            # Nombre del artículo
            if tanque['articulo'] in articulos:
                tanque['articulo_nombre'] = articulos[tanque['articulo']]
        
        almacen_obj['tanques'] = tanque_list
        logging.info(f"Almacén {almacen_code} configurado con {len(tanque_list)} tanques")
    
    # Solo almacenes con tanques
    result = [a for a in almacenes if a['tanques']]
    logging.info(f"Almacenes finales con tanques: {len(result)}")
    
    # Debug: mostrar detalles de cada almacén
    for alm in result:
        logging.info(f"Almacén final: {alm['codigo']} - {len(alm['tanques'])} tanques")
    
    logging.info(f"✅ Estructura completa: {len(result)} almacenes con tanques")
    return result

# Variable global para almacenar datos
DATA = []

def init_data():
    """Inicializar datos al arranque"""
    global DATA
    logging.info("🚀 Inicializando datos del sistema...")
    DATA = build_full_data()
    logging.info(f"✅ Inicialización completa: {len(DATA)} almacenes")

# ================== ROUTES ==================

@app.route('/')
def index():
    """Página principal"""
    return render_template('sondastanques_mod.html')

@app.route('/api/almacenes')
def api_almacenes():
    """API de almacenes"""
    try:
        logging.info(f"API /api/almacenes llamada - Devolviendo {len(DATA)} almacenes")
        
        # Debug: mostrar el primer almacén
        if DATA:
            first_alm = DATA[0]
            logging.info(f"Primer almacén: {first_alm['codigo']} - {first_alm['nombre']} - {len(first_alm['tanques'])} tanques")
            if first_alm['tanques']:
                first_tank = first_alm['tanques'][0]
                logging.info(f"Primer tanque: {first_tank['codigo']} - Nivel: {first_tank.get('nivel', 0)}")
        
        return jsonify(DATA)
        
    except Exception as e:
        logging.error(f"Error en API almacenes: {e}")
        import traceback
        logging.error(traceback.format_exc())
        return jsonify([])

@app.route('/api/status')
def api_status():
    """Status del sistema"""
    try:
        return jsonify({
            'timestamp': int(time.time() * 1000),
            'almacenes_count': len(DATA),
            'cache_size': len(CACHE),
            'status': 'ok'
        })
    except Exception as e:
        logging.error(f"Error en status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh')
def api_refresh():
    """Forzar recarga de datos"""
    global DATA
    try:
        logging.info("🔄 Recarga manual solicitada")
        
        # Limpiar cache
        CACHE.clear()
        CACHE_TTL.clear()
        
        # Recargar datos
        DATA = build_full_data()
        
        return jsonify({
            'success': True,
            'message': f'Datos recargados: {len(DATA)} almacenes',
            'timestamp': int(time.time() * 1000)
        })
        
    except Exception as e:
        logging.error(f"Error en refresh: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ================== STARTUP ==================

def open_browser():
    """Abre el navegador (solo una vez)"""
    try:
        webbrowser.open('http://127.0.0.1:5000')
        logging.info("🌐 Navegador abierto")
    except:
        pass

if __name__ == '__main__':
    # Inicializar datos
    init_data()
    
    # Abrir navegador SOLO UNA VEZ después de 2 segundos
    threading.Timer(2.0, open_browser).start()
    
    logging.info("🌐 Servidor iniciado en http://127.0.0.1:5000")
    
    # Ejecutar servidor
    try:
        from waitress import serve
        serve(app, host='127.0.0.1', port=5000, threads=4)
    except ImportError:
        app.run(host='127.0.0.1', port=5000, debug=False)

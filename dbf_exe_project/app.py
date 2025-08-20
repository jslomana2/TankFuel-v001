import os, logging
from flask import Flask, jsonify, render_template, request
from dbfread import DBF

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DBF_DIR = os.path.join(BASE_DIR, "FUEL_001")  # Ajusta si necesario

def read_dbf(name):
    path = os.path.join(DBF_DIR, name)
    if not os.path.exists(path):
        return []
    try:
        return [dict(r) for r in DBF(path, load=True, ignore_missing_memofile=True)]
    except Exception as e:
        logging.error(f"Error leyendo {name}: {e}")
        return []

@app.route('/')
def index():
    return render_template('sondastanques_mod.html')

@app.route('/api/where')
def api_where():
    files = ['FFALMA.DBF','FFARTI.DBF','FFCALA.DBF','FFTANQ.DBF']
    result = {}
    for f in files:
        p = os.path.join(DBF_DIR, f)
        result[f.lower()] = {
            "exists": os.path.exists(p),
            "file": f,
            "resolved_path": p,
            "size_bytes": os.path.getsize(p) if os.path.exists(p) else None
        }
    return jsonify(result)

@app.route('/api/tanques_norm')
def api_tanques_norm():
    tanques = read_dbf('FFTANQ.DBF')
    almacenes = {a['CODIGO']:a for a in read_dbf('FFALMA.DBF')}
    articulos = {a['CODIGO']:a for a in read_dbf('FFARTI.DBF')}
    rows = []
    for t in tanques:
        tid = f"{t.get('ALMACEN')}-{t.get('CODIGO')}"
        art = articulos.get(t.get('ARTICULO'))
        alm = almacenes.get(t.get('ALMACEN'))
        rows.append({
            "tanque_id": tid,
            "descripcion": t.get("DESCRI"),
            "capacidad_l": t.get("CAPACIDAD"),
            "stock_l": t.get("STOCK"),
            "stock15_l": t.get("STOCK15"),
            "producto_id": t.get("ARTICULO"),
            "almacen_id": t.get("ALMACEN"),
            "temp_ultima_c": t.get("TEMPULT"),
            "producto_nombre": art.get("DESCRI") if art else None,
            "almacen_nombre": alm.get("NOMBRE") if alm else None
        })
    return jsonify({"rows": rows})

@app.route('/api/articulos')
def api_articulos():
    return jsonify({"rows": read_dbf("FFARTI.DBF")})

@app.route('/api/almacenes')
def api_almacenes():
    return jsonify({"rows": read_dbf("FFALMA.DBF")})

@app.route('/api/calibraciones/ultimas')
def api_calibraciones_ultimas():
    tanque_id = request.args.get("tanque_id")
    n = int(request.args.get("n", 10))
    data = read_dbf("FFCALA.DBF")
    if tanque_id:
        data = [r for r in data if f"{r.get('ALMACEN')}-{r.get('TANQUES')}" == tanque_id]
    data = sorted(data, key=lambda x: (x.get("FECHA"), x.get("HORA")), reverse=True)[:n]
    return jsonify({"rows": data})

if __name__ == '__main__':
    logging.info("Iniciando servidor en http://127.0.0.1:5000")
    app.run(debug=True)

import threading, webbrowser, os
from flask import Flask, render_template, after_this_request

app = Flask(__name__, template_folder="templates", static_folder="static")

# --- Desactivar caché de estáticos en desarrollo ---
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
@app.after_request
def add_header(resp):
    resp.headers['Cache-Control'] = 'no-store'
    return resp

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

def _open_browser():
    try:
        webbrowser.open_new("http://127.0.0.1:5000/")
    except Exception:
        pass

if __name__ == "__main__":
    # Abrir navegador automáticamente 0.6s después de arrancar
    threading.Timer(0.6, _open_browser).start()
    print("Iniciando servidor en http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)
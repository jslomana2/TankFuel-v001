import os, threading, webbrowser
from flask import Flask, render_template

app = Flask(__name__, template_folder="templates", static_folder="static")

@app.route("/")
def index():
    return render_template("sondastanques_mod.html")

def _open_browser():
    try:
        webbrowser.open_new("http://127.0.0.1:5000/")
    except Exception:
        pass

if __name__ == "__main__":
    # Abrir solo una vez (evita doble ventana con el reloader de Flask)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(0.6, _open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=True)
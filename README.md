# PROCONSI · Tanques (Vista avanzada)

Aplicación local (Flask + PyInstaller) que lee **DBF** (FFALMA, FFARTI, FFTANQ, FFCALA) y muestra:
- Tarjetas de tanques por almacén
- Color del producto desde **FFARTI.COLORPRODU** (fiel a especificación)
- Barra de nivel con estados (Normal/Atención/Alarma)
- Selector de almacén y botón **Refrescar**
- Panel histórico al hacer clic en un tanque

## Estructura
```
dbf_exe_project/
  ├─ app.py
  ├─ requirements.txt
  ├─ templates/sondastanques_mod.html
  └─ static/
      ├─ sondastanques_mod.css
      ├─ sondastanques_mod.js
      └─ favicon.ico
.github/workflows/build-windows-exe.yml
```

## Ejecución en desarrollo
```bash
cd dbf_exe_project
pip install -r requirements.txt
set FLASK_ENV=development
python app.py
# Abre http://127.0.0.1:5000/
```
> Coloca **FFALMA.DBF**, **FFARTI.DBF**, **FFTANQ.DBF**, **FFCALA.DBF** en la misma carpeta que `app.py` (o usa `DBF_DIR` para apuntar a otra ruta).

## Variables
- `DBF_DIR` (opcional): carpeta donde están los DBF. Por defecto, la misma que el EXE/app.
- `FFALMA`, `FFARTI`, `FFTANQ`, `FFCALA`: nombres de los ficheros. Por defecto `*.DBF`.

## Build EXE (local)
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --add-data "templates;templates" --add-data "static;static" app.py
# El EXE sale en dist/app.exe (renómbralo si quieres).
```

## GitHub Actions
El workflow `build-windows-exe.yml` compila en Windows y adjunta el artefacto `PROCONSI-Tanques.exe`.
Coloca tus DBF **junto al EXE** al desplegarlo.


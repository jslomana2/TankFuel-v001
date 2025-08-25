# PROCONSI – Tanques (Vista avanzada)

Este paquete contiene una versión funcional del proyecto **dbf_exe_project**.

## Estructura
```
dbf_exe_project/
 ├─ app.py
 ├─ requirements.txt
 ├─ run.bat
 ├─ FFALMA.DBF / FFARTI.DBF / FFTANQ.DBF / (FFCALA.DBF opcional)
 ├─ templates/
 │   └─ sondastanques_mod.html
 └─ static/
     ├─ sondastanques_mod.css
     ├─ sondastanques_mod.js
     └─ favicon.ico
```

## Cómo ejecutar (local)
1. Instala dependencias: `pip install -r requirements.txt`
2. Ejecuta: `python app.py` (o `run.bat` en Windows)
3. Abre: http://127.0.0.1:5000

## Empaquetar EXE con PyInstaller (local)
```
pyinstaller --noconfirm --onefile --add-data "templates;templates" --add-data "static;static" --icon static\favicon.ico --name "PROCONSI-Tanques" app.py
```
**Coloca los DBF en la misma carpeta donde queda el exe.**

## Notas
- El color de producto sale de `FFARTI.DBF` en el campo `COLORPRODU` (si no existe, intenta `COLORPRODUCTO`/`COLOR`).
- El servidor busca los DBF en el mismo directorio del exe/app.py (`DBF_DIR`). Puedes forzarlo con la variable de entorno `DBF_DIR`.

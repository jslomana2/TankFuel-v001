# PROCONSI – Tanques (DBF → EXE)

Este paquete contiene el **backend Flask** y la **vista modernizada** para mostrar tanques a partir de ficheros DBF.

## Estructura
```
dbf_exe_project/
├─ app.py
├─ requirements.txt
├─ templates/
│  └─ sondastanques_mod.html
└─ static/
   ├─ sondastanques_mod.css
   ├─ sondastanques_mod.js
   └─ (opcional) favicon.ico
```
> **Los DBF NO se incluyen**. Deben estar **en la misma carpeta** que el EXE o junto a `app.py` durante desarrollo.

## Ejecución local
1. Python 3.10+
2. `pip install -r requirements.txt`
3. `python app.py`
4. Abra: http://127.0.0.1:5000

## Dónde colocar los DBF
Coloque junto al EXE (o junto a `app.py`) estos ficheros:
- `FFALMA.DBF`
- `FFARTI.DBF`
- `FFTANQ.DBF`
- `FFCALA.DBF` (para el histórico)

El programa buscará en este orden:
- Directorio de trabajo actual
- Directorio del ejecutable (si está congelado con PyInstaller)
- `dist/` bajo el ejecutable
- `dbf_exe_project/` bajo el ejecutable

## Color de producto (IMPORTANTE)
El color de cada tanque **ahora se toma de `FFARTI.COLORPRODU`** (no de `FFALMA.COLORFONDO`). En backend se convierte a `#RRGGBB`.

## Empaquetado (PyInstaller)
Ejemplo de comando local:
```
pyinstaller --noconfirm --onefile --name "PROCONSI-Tanques" app.py
```
- Si quiere icono: añada `--icon static/favicon.ico`
- Tras compilar, copie los DBF a la **misma carpeta** que `PROCONSI-Tanques.exe`.

## Troubleshooting
- `DBF no encontrado`: confirme que los `.DBF` están junto al EXE. El log muestra rutas probadas.
- `ERR_CONNECTION_REFUSED`: el EXE cerró sin error. Ejecútelo desde **CMD** para ver el log. Asegúrese de que no hay otro proceso usando el puerto 5000.
- Pantalla en blanco: ver consola del navegador (F12). Asegúrese de que `/api/tanques_norm` devuelve filas.

*Generado: 2025-08-25*

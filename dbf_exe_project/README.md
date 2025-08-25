# PROCONSI · Tanques (Vista avanzada)

## Estructura
```
dbf_exe_project/
├─ app.py
├─ templates/
│  └─ sondastanques_mod.html
└─ static/
   ├─ sondastanques_mod.css
   └─ sondastanques_mod.js
```

Coloca **FFALMA.DBF**, **FFARTI.DBF**, **FFTANQ.DBF** y **FFCALA.DBF** en esta misma carpeta junto al `app.py` / `app.exe`.

## Ejecutar en local (modo desarrollo)
1. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   ```
2. Lanza:
   ```bash
   python app.py
   ```
3. Abre: http://127.0.0.1:5000

## Empaquetar a EXE (PyInstaller)
```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --add-data "templates;templates" --add-data "static;static" app.py -n "PROCONSI-Tanques"
```
El ejecutable quedará en `dist/PROCONSI-Tanques.exe`. Copia ese exe **junto a los DBF**.

> **Importante (colores):** los colores de producto ahora se toman de **FFARTI.COLORPRODU** (no de FFALMA). Si ese campo no existe o está 0, se aplica un color por defecto según el producto.

## Funciones clave
- **/api/tanques_norm** → filas normalizadas con `color_hex` calculado desde FFARTI.COLORPRODU.
- **Selector de almacenes** + **Ver todos** (intercept en el HTML) para aplanar vista.
- **Refrescar** datos sin recargar la página.
- **Panel de histórico** (estructura preparada; puedes engancharlo a `/api/calibraciones/ultimas`).

## Problemas comunes
- **Se cierra el EXE al abrir** → crea un `run.bat` (incluido) y ejecútalo para ver el log; si falta un DBF o una DLL, saldrá el error.
- **127.0.0.1 rechazó la conexión** → el servidor no arrancó. Ejecuta `run.bat` o `python app.py` y revisa mensajes.
- **Estilos no aplican** → comprueba que la página apunte a `/static/sondastanques_mod.css` y `/static/sondastanques_mod.js` (ya configurado).

## Licencia
Interno PROCONSI.

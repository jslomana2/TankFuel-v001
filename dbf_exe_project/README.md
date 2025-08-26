
# PROCONSI – SondaTanques (Flask + DBF)

## Uso en desarrollo
```bash
python -m venv .venv
. .venv/Scripts/activate  # en Windows
pip install -r requirements.txt
# Copia tus DBF (FFALMA.DBF, FFARTI.DBF, FFTANQ.DBF, FFCALA.DBF) junto a app.py
python app.py
# abre http://127.0.0.1:5000
```

## Uso del EXE
El EXE busca los DBF **en la misma carpeta que el EXE**. También puedes pasar la carpeta de datos como primer argumento:
```
PROCONSI-Tanques.exe "C:\RUTA\A\DBF"
```

## Endpoints
- `/api/tanques_norm?almacen=...`
- `/api/calibraciones/ultimas?tanque_id=&n=`
- `/api/almacenes`
- `/api/articulos`
- `/api/where`

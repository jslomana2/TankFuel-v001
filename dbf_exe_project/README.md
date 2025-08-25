# PROCONSI · Tanques (dbf_exe_project)

## Cómo ejecutar en local
1. Instala dependencias:
   ```bash
   pip install flask dbfread
   ```
2. Coloca los DBF **FFALMA.DBF**, **FFARTI.DBF**, **FFTANQ.DBF** (y **FFCALA.DBF** si aplica) **en la misma carpeta** que `app.py` o define la variable de entorno `DBF_DIR` apuntando a la carpeta donde están.
3. Ejecuta:
   ```bash
   python app.py
   ```
4. Abre `http://127.0.0.1:5000`

## Build del EXE (PyInstaller)
```bash
pyinstaller -y app.py ^
  --name "PROCONSI-Tanques" ^
  --add-data "templates;templates" ^
  --add-data "static;static"
```
Copia los DBF **al lado del EXE** (o expón `DBF_DIR`) para que no aparezca el aviso "DBF no encontrado".

## Endpoints principales
- `/` → UI
- `/api/almacenes` → lista de almacenes (FFALMA)
- `/api/tanques_norm` → tanques normalizados con color del producto desde `FFARTI.COLORPRODU`

## Notas
- El backend normaliza nombres de campos a mayúsculas y es tolerante con variantes comunes: `CODIALM/CODALMA/ALMACEN`, `CODIARTI/CODIGO/ARTICULO`, etc.
- El color del producto se toma de **FFARTI.COLORPRODU** (si falta, se usa `#2aa8ff`).
# PROCONSI · Tanques (DBF → Web/EXE)

## Cómo ejecutar (desarrollo)
1. Coloca `FFALMA.DBF`, `FFARTI.DBF`, `FFTANQ.DBF`, `FFCALA.DBF` en la misma carpeta que `app.py`.
2. Instala dependencias:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
3. Abre `http://127.0.0.1:5000/`

## Cómo compilar EXE (Windows)
1. Ejecuta `build_exe_win.bat` o lanza el workflow de GitHub Actions **Build EXE (Windows)**.
2. Copia los DBF a la misma carpeta que el EXE resultante.
3. Doble clic al EXE. Abre `http://127.0.0.1:5000/`.

## Notas
- El **color del producto** se toma de `FFARTI.COLORPRODU` (decimal) → `#RRGGBB`.
- Endpoints: `/api/where`, `/api/almacenes`, `/api/articulos`, `/api/tanques_norm?almacen=XXXX`, `/api/calibraciones/ultimas?...`.

# Tanques DBF – Ejecutable local

## ⚙️ Qué hace
- Lee `FFALMA.DBF`, `FFARTI.DBF`, `FFTANQ.DBF`, `FFCALA.DBF` **desde la MISMA carpeta** donde dejas el `app.exe`.
- Sirve una web con tus estilos y JS (`/templates` y `/static`).
- Endpoints:
  - `/api/where` – comprueba rutas de DBFs
  - `/api/tanques_norm` – tanques normalizados + producto/almacén
  - `/api/calibraciones/ultimas?tanque_id=ALM-COD&n=10` – últimas lecturas
  - `/api/articulos`, `/api/almacenes`

## 🧩 Estructura para el .exe
Copia **estos 3 elementos** en la misma carpeta donde están los DBFs:
```
app.exe
templates/
static/
FFALMA.DBF  FFARTI.DBF  FFTANQ.DBF  FFCALA.DBF
```
> No es necesario subir los DBFs a GitHub.

## ▶️ Ejecutar
- Doble clic en `app.exe` y abre `http://127.0.0.1:5000/`
- Si no abre, ve tú mismo al navegador con esa URL.

## 🔍 Diagnóstico rápido
- `http://127.0.0.1:5000/api/where` → ¿detecta los DBFs?
- `http://127.0.0.1:5000/api/tanques_norm` → ¿devuelve JSON?
- Si algo falla, revisa la consola o crea un `debug.log` con configuración de logging.

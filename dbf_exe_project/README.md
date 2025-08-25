# PROCONSI · SondasTanques (DBF → Flask → EXE)

**Objetivo:** ejecutar una app local (doble clic) que lee tus DBF (`FFALMA.DBF`, `FFARTI.DBF`, `FFTANQ.DBF`, `FFCALA.DBF`) desde **la misma carpeta** donde está el `exe`, pinta los **tanques** con tu **estilo**, usa **el color del producto** desde `FFARTI.COLORPRODU`, y muestra **histórico** al hacer clic.

---

## Carpetas / ficheros

```
dbf_exe_project/
├─ app.py
├─ requirements.txt
├─ templates/
│  └─ sondastanques_mod.html
└─ static/
   ├─ sondastanques_mod.css
   └─ sondastanques_mod.js
```

> **Importante:** El frontend carga los assets con `url_for('static',...)` para evitar el problema de “solo veo texto plano”.

---

## Cómo ejecutarlo en local (sin EXE)

1. Instala Python 3.10+ en Windows.
2. Abre una consola en `dbf_exe_project`.
3. Instala dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Copia **tus DBF** (`FFALMA.DBF`, `FFARTI.DBF`, `FFTANQ.DBF`, `FFCALA.DBF`) en **esta misma carpeta**.
5. Lanza la app:

   ```bash
   python app.py
   ```

6. Se abre el navegador en `http://127.0.0.1:5000`.

---

## Cómo generar el EXE (PyInstaller)

> Consejo: primero genera **consola** (sin `--noconsole`) para ver errores si algo falla. Cuando todo funcione, puedes ocultar la consola con `--noconsole`.

```bash
pip install pyinstaller
pyinstaller --onefile --name "PROCONSI-Tanques" app.py
```

- El ejecutable quedará en `dist/PROCONSI-Tanques.exe`.
- Copia **el EXE** y **los DBF** a la misma carpeta en tu servidor/local.
- Doble clic al EXE → abre `http://127.0.0.1:5000`.

**Icono / nombre:** cuando esté listo, añade `--icon assets/proconsi.ico` y cambia `--name` al definitivo.

---

## Endpoints claves

- `GET /api/tanques_norm` → lista de tanques **normalizados**:
  - `color_hex` **sale de `FFARTI.COLORPRODU`** (no del `COLORFONDO` del almacén).
- `GET /api/calibraciones/ultimas?tanque_id=ALM-TANQUE&n=20`
- `GET /api/almacenes`
- `GET /api/articulos`

> El backend intenta detectar nombres de campos típicos (`ALMACEN`, `TANQUE`, `ARTICULO`, `CAPACIDAD`, `STOCK`, `TEMPERA`, etc.) y es tolerante a variantes.

---

## Problemas frecuentes (y solución)

- **Se cierra el EXE nada más abrir.**
  - Genera primero con consola: `pyinstaller --onefile app.py` y ejecuta desde CMD para ver el error.
  - Revisa `app.log` / `error.log` en la misma carpeta.
  - Verifica que los 4 DBF existen y **no están bloqueados** por otro proceso.

- **Veo la página sin estilos.**
  - Comprueba que el HTML usa `{{ url_for('static', filename='...') }}` (ya aplicado en este proyecto).
  - No abras el HTML directamente con doble clic; **siempre** vía `http://127.0.0.1:5000`.

- **Colores incorrectos.**
  - Ahora se toma de `FFARTI.COLORPRODU`. Si ese campo no existe o es 0, el backend aplica un color por defecto según producto.

- **Filtrar por almacén.**
  - Usa el selector de la cabecera o llama a `/api/tanques_norm?almacen=0001`.

---

## Presentación rápida
- Panel de tanques con aro de capacidad y porcentaje.
- Clic en un tanque → tabla **Histórico** (últimos movimientos en `FFCALA`).
- Selector de **Almacén** y botón **Refrescar**.
- Leyenda de estados: OK (≥50%), Advertencia (≥20%), Bajo (<20%).

---

## Seguridad y firma de código (cuando proceda)
Para evitar avisos de Windows SmartScreen al distribuir el EXE:
- Firma el ejecutable con un **certificado de firma de código** (Standard/Ev Code Signing).
- Opcionalmente, crea un **instalador MSI** firmado en lugar de suelto.

---

© PROCONSI

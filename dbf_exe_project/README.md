# Proyecto


### Dónde poner los DBF al ejecutar el `.exe`
El programa buscará tus datos en este orden:
1. `data/` embebido (si lo incluyes con PyInstaller)
2. **Junto al `app.exe` en `data/`**
3. **Directamente al lado del `app.exe` (misma carpeta)** ← recomendado
4. `data/` en el directorio actual
5. En el directorio actual

> Recomendación: deja `app.exe` y, a su lado, los `*.DBF` (y sus `.FPT/.DBT` si aplican). No hace falta crear `data/`.


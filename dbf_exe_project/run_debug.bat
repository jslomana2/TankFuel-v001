@echo off
setlocal
python -V || (echo Python no encontrado & pause & exit /b 1)
python app.py
echo.
echo (Pulsa una tecla para cerrar)
pause >nul

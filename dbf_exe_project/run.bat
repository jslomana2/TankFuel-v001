@echo off
setlocal
REM Arranca el servidor en local (usa Python si es script, o el EXE si está empaquetado)
echo Iniciando PROCONSI Tanques (Flask) en http://127.0.0.1:5000
python app.py
pause

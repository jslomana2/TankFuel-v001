@echo off
REM Genera EXE con consola para depurar
pyinstaller --onefile --name "PROCONSI-Tanques" app.py
echo Listo en .\dist\PROCONSI-Tanques.exe
pause
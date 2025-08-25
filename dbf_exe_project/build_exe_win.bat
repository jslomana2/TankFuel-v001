@echo off
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --onefile --name "PROCONSI-Tanques" --add-data "templates;templates" --add-data "static;static" app.py
echo.
echo EXE en .\dist\PROCONSI-Tanques.exe
pause

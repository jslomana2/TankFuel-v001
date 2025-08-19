\
@echo off
setlocal
if not exist .venv python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --noconfirm --clean --name app --onefile ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  app.py
echo Listo: dist\app.exe
pause

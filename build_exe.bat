@echo off
cd /d %~dp0

if not exist .venv (
    py -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt pyinstaller

pyinstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name RocoAutoCoin ^
  --add-data "images;images" ^
  gui_launcher.py

echo.
echo 打包完成，exe 位于 dist\RocoAutoCoin\ 目录。
pause

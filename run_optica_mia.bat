@echo off
setlocal

REM Ir a la carpeta del proyecto (donde está este .bat)
cd /d %~dp0

echo === Óptica Mia: Iniciando entorno ===

REM Crear venv si no existe
if not exist .venv (
  echo Creando entorno virtual .venv...
  py -3 -m venv .venv
)

REM Activar venv
call .venv\Scripts\activate.bat

REM Actualizar pip e instalar dependencias
python -m pip install --upgrade pip >nul 2>&1
if exist requirements.txt (
  echo Instalando dependencias...
  python -m pip install -r requirements.txt
)

REM Variables de entorno básicas
set FLASK_ENV=production
set PYTHONUTF8=1

echo === Óptica Mia: Levantando servidor ===
start "Óptica Mia" http://127.0.0.1:5000/

REM Ejecutar la app
python app.py

echo.
echo Servidor detenido. Presione una tecla para salir.
pause >nul



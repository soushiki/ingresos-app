@echo off
rem Instala Indra OCR en indra_venv\ (Python 3.14). Se puede correr varias veces: lo que ya esta no se rehace.
setlocal
cd /d "%~dp0"
set "VENV=%~dp0indra_venv"
set "PY=%VENV%\Scripts\python.exe"
set "MODELOS=%VENV%\modelos"

py -3.14 --version >nul 2>&1
if errorlevel 1 goto sinpython

if not exist "%PY%" (
  echo Creando indra_venv...
  py -3.14 -m venv "%VENV%"
  if errorlevel 1 goto fallo
)

echo Instalando requisitos...
"%PY%" -m pip install -q --disable-pip-version-check --only-binary=:all: -r indra_requisitos.txt
if errorlevel 1 goto fallo

if not exist "%MODELOS%\det.onnx" (
  echo Bajando modelos una sola vez ^(76 MB^)...
  "%PY%" -I -c "import shutil, indra_ocr; shutil.copytree(indra_ocr.model_dir(), r'%MODELOS%', dirs_exist_ok=True)"
  if errorlevel 1 goto fallo
)

set "HF_HUB_OFFLINE=1"
set "INDRA_OCR_MODEL_DIR=%MODELOS%"
"%PY%" -I -c "import numpy, indra_ocr; indra_ocr.OrtOCR(indra_ocr.model_dir(), threads=2)(numpy.full((64, 256), 255, numpy.uint8), turn=False); print('Indra listo')"
if errorlevel 1 goto fallo
exit /b 0

:sinpython
echo No se encontro Python 3.14. Instalalo con:  winget install Python.Python.3.14
exit /b 1

:fallo
echo Fallo la instalacion de Indra. Revisa los mensajes de arriba.
exit /b 1

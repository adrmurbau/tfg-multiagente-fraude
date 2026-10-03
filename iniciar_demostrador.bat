@echo off
setlocal
cd /d "%~dp0"
title Demostrador antifraude - TFG

echo.
echo  ================================================
echo   DEMOSTRADOR ANTIFRAUDE - TFG
echo  ================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
  echo  ERROR: no encuentro el entorno virtual en .venv
  echo  Crealo con:  python -m venv .venv
  echo.
  pause
  exit /b 1
)

call ".venv\Scripts\activate.bat"

echo  Comprobando Ollama...
curl -s -o nul -m 3 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
  echo    AVISO: Ollama no responde en el puerto 11434.
  echo    Las pantallas de Turno y Caso funcionaran igual,
  echo    pero Investigacion e Informe necesitan Ollama abierto.
) else (
  echo    Ollama OK.
)
echo.

echo  Arrancando el servidor...
echo.
echo    Abre esto en el navegador:   http://127.0.0.1:8000
echo.
echo    Deja esta ventana abierta mientras grabas.
echo    Para parar el servidor: Ctrl+C
echo.

python -m uvicorn src.web.app:app --host 127.0.0.1 --port 8000

echo.
echo  El servidor se ha detenido.
pause

@echo off
setlocal
cd /d "%~dp0"
title Preparar Ollama - TFG

echo.
echo  ================================================
echo   PREPARAR OLLAMA PARA EL DEMOSTRADOR
echo  ================================================
echo.

echo  1) Comprobando que Ollama responde...
curl -s -o nul -m 5 http://127.0.0.1:11434/api/tags
if errorlevel 1 (
  echo.
  echo     Ollama NO responde en el puerto 11434.
  echo     Abre la aplicacion Ollama ^(icono de la bandeja^) y vuelve a
  echo     ejecutar este fichero.
  echo.
  pause
  exit /b 1
)
echo     Ollama OK.
echo.

echo  2) Modelos que hay ahora mismo:
echo.
ollama list
echo.

echo  3) Descargando los modelos base que falten.
echo     Si ya estan, no se descarga nada.
echo     qwen2.5:14b ocupa unos 9 GB y llama3.1:8b unos 5 GB.
echo.
ollama pull qwen2.5:14b
ollama pull llama3.1:8b
echo.

echo  4) Creando las variantes de contexto ampliado ^(-ctx16k^).
echo     Hacen falta para el informe completo: sin ellas Ollama
echo     trunca el expediente por el principio y en silencio.
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "ollama\crear_variantes.ps1"
echo.

echo  ================================================
echo   LISTO. Refresca el demostrador con F5.
echo  ================================================
echo.
pause

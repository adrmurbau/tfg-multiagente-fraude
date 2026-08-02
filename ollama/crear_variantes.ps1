# Crea las variantes de contexto ampliado de cada modelo.
#
# Por que hace falta: Ollama usa num_ctx = 4096 por defecto y trunca por el
# principio, en silencio, cuando el prompt lo excede. Con expedientes de 30 a
# 55 casos eso corta el inicio del expediente sin dejar rastro. Ver README.md.
#
# CrewAI rechaza num_ctx como argumento del LLM (TypeError), de modo que la
# unica via es declararlo en el propio modelo mediante un Modelfile.
#
# Uso:
#     cd ollama
#     .\crear_variantes.ps1
#
# Solo hay que ejecutarlo una vez por maquina. Las variantes quedan
# registradas en Ollama con el sufijo -ctx16k.

$modelos = @(
    @{ base = "qwen2.5:14b";                variante = "qwen2.5-14b-ctx16k"    },
    @{ base = "gpt-oss:20b";                variante = "gpt-oss-20b-ctx16k"    },
    @{ base = "llama3.1:8b";                variante = "llama3.1-8b-ctx16k"    },
    @{ base = "qwen3:14b";                  variante = "qwen3-14b-ctx16k"      },
    @{ base = "qwen2.5:14b-instruct-q6_K";  variante = "qwen2.5-14b-q6-ctx16k" }
)

# `ollama list` devuelve los nombres con el sufijo ':latest' cuando no se
# indico etiqueta al crearlos. Se normaliza para poder comparar.
$instalados = @(ollama list | Select-Object -Skip 1 | ForEach-Object {
    $n = ($_ -split "\s+")[0]
    if ($n) { $n -replace ':latest$', '' }
})

Write-Host ""
Write-Host "Modelos instalados en Ollama:" -ForegroundColor Cyan
$instalados | ForEach-Object { Write-Host "  $_" }
Write-Host ""

foreach ($m in $modelos) {
    if ($instalados -contains $m.variante) {
        Write-Host "[ya existe ] $($m.variante)" -ForegroundColor DarkGray
        continue
    }
    if ($instalados -notcontains $m.base) {
        Write-Host "[falta base] $($m.base) no esta instalado. " -ForegroundColor Yellow -NoNewline
        Write-Host "Descargalo con: ollama pull $($m.base)"
        continue
    }

    # El Modelfile se escribe junto al script y NO en $env:TEMP: con nombres de
    # usuario acentuados, $env:TEMP se expande a una ruta corta del tipo
    # C:\Users\ADRIN~1 que PowerShell no siempre resuelve.
    $tmp = Join-Path $PSScriptRoot "Modelfile.tmp"
    "FROM $($m.base)`nPARAMETER num_ctx 16384" | Set-Content -Path $tmp -Encoding ASCII

    Write-Host "[creando   ] $($m.variante) desde $($m.base)..." -ForegroundColor Green
    try {
        ollama create $m.variante -f $tmp
    } catch {
        Write-Host "[ERROR     ] no se pudo crear $($m.variante): $_" -ForegroundColor Red
    }
    # Un fallo al borrar el temporal no debe abortar el resto de variantes.
    try { Remove-Item -LiteralPath $tmp -Force } catch { }
}

Write-Host ""
Write-Host "Variantes con contexto ampliado disponibles:" -ForegroundColor Cyan
ollama list | Select-String "ctx16k"
Write-Host ""
Write-Host "Cada variante ocupa espacio adicional en disco." -ForegroundColor DarkGray

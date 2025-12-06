# Script para subir el proyecto a GitHub
# Coloca este archivo en la carpeta de tu proyecto y ejécutalo.
Write-Host "--- Asistente de Subida a GitHub ---" -ForegroundColor Cyan
Write-Host "Asegúrate de haber creado un repositorio VACÍO en GitHub primero." -ForegroundColor Yellow
$repoUrl = Read-Host "Por favor, pega la URL de tu repositorio de GitHub (ej: https://github.com/tu_usuario/tu_repo.git)"
if (-not $repoUrl) {
    Write-Error "No se ingresó ninguna URL. Abortando."
    exit 1
}
# Nos aseguramos de estar en el directorio del script
Set-Location $PSScriptRoot
# Verificar si git está inicializado
if (-not (Test-Path ".git")) {
    Write-Host "Inicializando repositorio git..."
    git init
    git add .
    git commit -m "Commit inicial automático"
} else {
    # Asegurar que todo esté commiteado
    if (git status --porcelain) {
        Write-Host "Guardando cambios pendientes..."
        git add .
        git commit -m "Guardando cambios antes de subir"
    }
}
# Configurar el remoto
$remotes = git remote
if ($remotes -contains "origin") {
    Write-Host "El remoto 'origin' ya existe. Actualizando URL..."
    git remote set-url origin $repoUrl
} else {
    Write-Host "Agregando remoto 'origin'..."
    git remote add origin $repoUrl
}
# Subir
Write-Host "Subiendo archivos a la rama 'main'..." -ForegroundColor Cyan
git branch -M main
try {
    git push -u origin main
    Write-Host "✅ ¡Subida exitosa!" -ForegroundColor Green
} catch {
    Write-Error "Hubo un error al subir. Verifica tus credenciales o si la URL es correcta."
}
Read-Host "Presiona Enter para salir"

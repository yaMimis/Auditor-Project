@echo off
rem Clique duplo para subir o Auditor de Preco Justo (banco, API e painel).
rem Mesmo efeito de .\iniciar.ps1; repassa opcoes, ex.: iniciar.bat -Build
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0iniciar.ps1" %*
pause

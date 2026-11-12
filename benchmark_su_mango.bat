@echo off
rem Revisione R10 - 12/11/2026 - indirizzo predefinito del Mango 192.168.1.1
rem Esegue sul Mango (via SSH) la prova di velocita' e salva il risultato in misure\benchmark_mango.txt
rem Richiede il client SSH di Windows 10/11 e l'accesso root al Mango (password del pannello GL.iNet).
setlocal
cd /d "%~dp0"
set "IP=192.168.1.1"
set /p IP=Indirizzo del Mango [192.168.1.1]: 
if not exist misure mkdir misure
echo.
echo Copio il programma in /tmp del Mango ed eseguo la prova (ti verra' chiesta la password)...
tar -cf - -C mango . | ssh -o StrictHostKeyChecking=accept-new root@%IP% "rm -rf /tmp/emsb; mkdir -p /tmp/emsb; tar -xf - -C /tmp/emsb; cd /tmp/emsb; lua benchmark_mango.lua; rm -rf /tmp/emsb" > misure\benchmark_mango.txt
type misure\benchmark_mango.txt
echo.
echo Se sopra compare "BENCHMARK totale ...", carica misure\benchmark_mango.txt nel repository GitHub
echo (cartella misure, pulsante Add file - Upload files).
pause
endlocal

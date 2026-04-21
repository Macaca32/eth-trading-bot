@echo off
REM Auto-open browser when Next.js dashboard is ready at http://localhost:3000
REM This runs hidden in the background and exits after opening the browser.
powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 3; $c=0; while($c -lt 90){try{(Invoke-WebRequest -Uri http://localhost:3000 -UseBasicParsing -TimeoutSec 2)|Out-Null; Start-Process 'http://localhost:3000'; exit}catch{Start-Sleep -Seconds 1; $c++}}"

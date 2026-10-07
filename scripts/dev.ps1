# Starts API and frontend in two windows. Run from the repo root: .\scripts\dev.ps1
if (-not $env:SEC_USER_AGENT) { Write-Host 'Set SEC_USER_AGENT first, e.g. $env:SEC_USER_AGENT = "PrecedentFinder Your Name you@email.com"'; exit 1 }
$root = Split-Path $PSScriptRoot -Parent
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --port 8000"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root\frontend'; npm run dev"

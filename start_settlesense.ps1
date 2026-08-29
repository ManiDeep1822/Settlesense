Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Starting SettleSense (FastAPI Backend + React Vite UI)     " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Start FastAPI backend in a separate background PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python run_backend.py"

# Start Vite React Frontend
cd frontend
npm run dev

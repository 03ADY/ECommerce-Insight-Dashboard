$Root = Split-Path $PSScriptRoot -Parent
$Py = Join-Path $Root "venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { python -m venv (Join-Path $Root "venv"); & (Join-Path $Root "venv\Scripts\pip.exe") install -r (Join-Path $Root "requirements.txt") }
Start-Process "http://127.0.0.1:8503"
& $Py -m streamlit run (Join-Path $Root "app.py") --server.port 8503

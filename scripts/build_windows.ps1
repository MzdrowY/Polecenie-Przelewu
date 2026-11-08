$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
py -3.12 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m PyInstaller --clean --noconfirm --windowed --name 'Druki Pocztowe' --add-data 'assets/template.pdf:assets' main.py
Write-Host 'Zbudowano aplikację w katalogu dist/ (tylko Windows).'

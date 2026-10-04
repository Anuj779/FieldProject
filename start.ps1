$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    throw 'Run the installation steps in README.md first.'
}
& '.\.venv\Scripts\python.exe' app.py

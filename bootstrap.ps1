param(
  [ValidateSet('quick','full','build-only','test')]
  [string]$Mode = 'quick'
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw 'Python 3.11+ is required and was not found in PATH.'
}
if (-not (Test-Path '.venv')) {
  python -m venv .venv
}
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt

if ($Mode -ne 'test' -and -not $env:SEC_USER_AGENT) {
  $contact = Read-Host 'SEC contact email (required by SEC fair-access policy)'
  if (-not $contact.Contains('@')) { throw 'A valid contact email is required.' }
  $env:SEC_USER_AGENT = "Edward Gani $contact"
}

& $python run_pipeline.py --mode $Mode
if ($LASTEXITCODE -ne 0) { throw "Pipeline failed with exit code $LASTEXITCODE" }

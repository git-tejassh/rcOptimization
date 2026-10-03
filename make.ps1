# PowerShell mirror of the Makefile.  Usage:  .\make.ps1 <target>   e.g.  .\make.ps1 all
param([Parameter(Position = 0)][string]$Target = "all")
$ErrorActionPreference = "Stop"
$py = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { ".venv/bin/python" }

function Run([string]$cmd) { Write-Host ">> $cmd"; Invoke-Expression $cmd; if ($LASTEXITCODE) { throw "failed: $cmd" } }

switch ($Target) {
  "setup"     { Run "python -m venv .venv"; Run "$py -m pip install -r requirements.txt"; Run "$py -m pip install -e . --no-deps"; Push-Location web; Run "npm install"; Pop-Location }
  "audit"     { Write-Host "Legacy audit: see docs/LEGACY_AUDIT.md" }
  "phase0"    { Run "$py -m rcopt.cli phase0" }
  "phase0b"   { Run "$py -m rcopt.cli phase0b" }
  "phase1"    { Run "$py -m rcopt.cli phase1" }
  "phase2"    { Run "$py -m rcopt.cli phase2" }
  "phase3"    { Run "$py -m rcopt.cli phase3" }
  "phase4"    { Run "$py -m rcopt.cli phase4" }
  "phase5"    { Run "$py -m rcopt.cli phase5" }
  "export"    { Run "$py -m rcopt.cli export" }
  "all"       { foreach ($t in "phase0","phase0b","phase1","phase2","phase3","phase4","phase5","export") { & $PSCommandPath $t } }
  "test"      { Run "$py -m pytest -m 'not slow'" }
  "test-slow" { Run "$py -m pytest" }
  "lint"      { Run "$py -m ruff check ." }
  "web-dev"   { Push-Location web; Run "npm run dev"; Pop-Location }
  "web-build" { Push-Location web; Run "npm run build"; Pop-Location }
  "api"       { Run "$py -m uvicorn api.main:app --reload" }
  "clean"     { "data/processed","data/results","models","web/dist" | ForEach-Object { if (Test-Path $_) { Remove-Item -Recurse -Force $_ } } }
  default     { throw "unknown target '$Target'" }
}

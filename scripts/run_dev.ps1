$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
uvicorn tax_agent.api.main:app --reload --port 8011

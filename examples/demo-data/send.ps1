<#
.SYNOPSIS
  Sends ToolBridge demo MCP requests (examples/demo-data/requests/*.json) and prints PASS/FAIL.
.EXAMPLE
  .\send.ps1                 # all requests
  .\send.ps1 -Filter "E0*"   # only error requests
  .\send.ps1 -Filter 04_csv_cafe_orders -ShowBody
.NOTES
  Normal requests (01-12) should succeed; error requests (E01-E10) should be rejected.
  08-10 need internet, 11-12 need an enabled LLM provider key (otherwise they show NEEDS-SETUP).
  If TOOLBRIDGE_MCP_AUTH_TOKEN is set (env var or .env) it is sent as a Bearer token. It is never printed.
#>
param(
    [string]$BaseUrl = "http://127.0.0.1:8000/mcp/",
    [string]$Filter = "*",
    [switch]$ShowBody
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$token = $env:TOOLBRIDGE_MCP_AUTH_TOKEN
if (-not $token) {
    $envFile = Join-Path $here "..\..\.env"
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match '^\s*TOOLBRIDGE_MCP_AUTH_TOKEN\s*=' } | Select-Object -First 1
        if ($line) { $token = ($line -split '=', 2)[1].Trim().Trim('"').Trim("'") }
    }
}
$headers = @{ "Accept" = "application/json, text/event-stream" }
if ($token) { $headers["Authorization"] = "Bearer $token" }
$networkOrLlm = @("08_stock_price", "09_currency_usd_to_inr_eur", "10_website_reader", "11_llm_analyze_feedback", "12_llm_summarize_notes")
$pass = 0; $fail = 0; $setup = 0
foreach ($file in Get-ChildItem (Join-Path $here "requests") -Filter "$Filter.json" | Sort-Object Name) {
    $name = $file.BaseName
    $expectError = $name.StartsWith("E")
    $body = [System.IO.File]::ReadAllText($file.FullName)
    $isError = $false; $detail = ""
    try {
        $resp = Invoke-WebRequest -Uri $BaseUrl -Method Post -Headers $headers -ContentType "application/json" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -UseBasicParsing
        $text = $resp.Content
        if ($text -match '^\s*(event:|data:)') { $text = (($text -split "`n") | Where-Object { $_ -like 'data:*' } | ForEach-Object { $_.Substring(5) }) -join "" }
        $json = $text | ConvertFrom-Json
        if ($json.error) { $isError = $true; $detail = $json.error.message }
        elseif ($json.result.isError) { $isError = $true; $detail = ($json.result.content | Select-Object -First 1).text }
        else { $detail = "ok" }
    } catch {
        $isError = $true; $detail = "HTTP error: $($_.Exception.Message)"
    }
    if ($detail.Length -gt 140) { $detail = $detail.Substring(0, 140) + "..." }
    if ($isError -eq $expectError) { $status = "PASS"; $pass++ }
    elseif (-not $expectError -and $networkOrLlm -contains $name) { $status = "NEEDS-SETUP"; $setup++ }
    else { $status = "FAIL"; $fail++ }
    "{0,-12} {1,-32} {2}" -f $status, $name, $detail
    if ($ShowBody -and $json) { $json | ConvertTo-Json -Depth 20 }
}
""
"PASS: $pass  FAIL: $fail  NEEDS-SETUP (internet / LLM key): $setup"

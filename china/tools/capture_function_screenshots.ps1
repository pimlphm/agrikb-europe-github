param(
  [string]$OutputDir = "",
  [string]$ChromePath = "",
  [string]$AppUrl = "http://127.0.0.1:8010/ui/?fresh=function-screenshots",
  [int]$DebugPort = 9444
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $OutputDir) {
  $OutputDir = Join-Path $RootDir "outputs\manual-20260523-agrikb-function-screenshots\presentations\agrikb-function-screenshots\assets\function-screenshots"
}
if (-not $ChromePath) {
  $chromeCandidates = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
  )
  $ChromePath = ($chromeCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1)
  if (-not $ChromePath) {
    $cmd = Get-Command chrome, msedge -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cmd) { $ChromePath = $cmd.Source }
  }
}
if (-not $ChromePath) { throw "Chrome or Edge was not found. Pass -ChromePath explicitly." }

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Get-ChildItem -LiteralPath $OutputDir -Filter "*.png" -File -ErrorAction SilentlyContinue | Remove-Item -Force
Remove-Item -LiteralPath (Join-Path $OutputDir "manifest.json") -Force -ErrorAction SilentlyContinue
$assetRoot = Split-Path -Parent $OutputDir
$legacyProfileDir = Join-Path $OutputDir "chrome-profile"
$profileDir = Join-Path $assetRoot "chrome-profile"
foreach ($dirToClean in @($legacyProfileDir, $profileDir)) {
  $resolvedProfile = [System.IO.Path]::GetFullPath($dirToClean)
  $resolvedRoot = [System.IO.Path]::GetFullPath($assetRoot)
  if ($resolvedProfile.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $dirToClean)) {
    Remove-Item -LiteralPath $dirToClean -Recurse -Force -ErrorAction SilentlyContinue
  }
}
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

$features = @(
  @{ id = "digital"; label = "Digital Intelligence"; note = "RAG, knowledge graph, live data and model decisioning" },
  @{ id = "new_farmer"; label = "New Farmer Workbench"; note = "operation judgement, harvest, sales and policy filing" },
  @{ id = "bureau"; label = "Agriculture Bureau"; note = "data governance, industry support and training reports" },
  @{ id = "company"; label = "Agribusiness"; note = "traceability, market, supply chain and ecommerce channels" },
  @{ id = "farmer_today"; label = "Farmer: Today"; note = "one-tap daily work plan for farmers" },
  @{ id = "farmer_sell"; label = "Farmer: Sell"; note = "who to sell to, pricing and channel suggestions" },
  @{ id = "farmer_subsidy"; label = "Farmer: Subsidy"; note = "plain-language policy and subsidy matching" },
  @{ id = "farmer_risk"; label = "Farmer: Risk"; note = "weather and field risk in three actions" },
  @{ id = "policy"; label = "New Farmer Policy"; note = "policy filing, training subsidy and startup support" },
  @{ id = "platform"; label = "Digital Platform"; note = "knowledge base, model, evidence chain and PWA deployment" },
  @{ id = "intelligence"; label = "Information Aggregation"; note = "policy news, weather warnings, market signals and advisory aggregation" },
  @{ id = "benchmark"; label = "Competitive Benchmark"; note = "benchmarking against leading agriculture apps and platforms" },
  @{ id = "competition"; label = "Startup Competition"; note = "pitch points, scoring highlights and demo path" },
  @{ id = "market"; label = "Market Intelligence"; note = "purchase channels, ecommerce assistance and operation judgement" },
  @{ id = "weather"; label = "Agri Weather"; note = "local weather, environment, harvest and pest risk" },
  @{ id = "traceability"; label = "Quality Traceability"; note = "operator, plot, batch, certification and QR code" },
  @{ id = "crop"; label = "Crop Ontology"; note = "AGROVOC, Crop Ontology and trait relationships" }
)

Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" |
  Where-Object { $_.CommandLine -like "*--remote-debugging-port=$DebugPort*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Process -FilePath $ChromePath -ArgumentList @(
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--hide-scrollbars",
  "--remote-debugging-port=$DebugPort",
  "--window-size=1440,900",
  "--user-data-dir=$profileDir",
  $AppUrl
) -WindowStyle Hidden

Start-Sleep -Seconds 2

function Get-PageTarget {
  $targets = Invoke-RestMethod -Uri "http://127.0.0.1:$DebugPort/json/list"
  $page = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1
  if (-not $page) { throw "No Chrome page target found." }
  return $page
}

$page = Get-PageTarget
$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$ct = [System.Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]$page.webSocketDebuggerUrl, $ct).Wait()
$script:cdpId = 0

function Send-Cdp {
  param([string]$Method, [hashtable]$Params = @{})
  $script:cdpId += 1
  $payload = @{ id = $script:cdpId; method = $Method; params = $Params } | ConvertTo-Json -Depth 20 -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
  $ws.SendAsync([ArraySegment[byte]]::new($bytes), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct).Wait()
  while ($true) {
    $buffer = New-Object byte[] 4194304
    $stream = [System.IO.MemoryStream]::new()
    do {
      $result = $ws.ReceiveAsync([ArraySegment[byte]]::new($buffer), $ct).Result
      $stream.Write($buffer, 0, $result.Count)
    } while (-not $result.EndOfMessage)
    $text = [System.Text.Encoding]::UTF8.GetString($stream.ToArray())
    $message = $text | ConvertFrom-Json
    if ($message.id -eq $script:cdpId) { return $message }
  }
}

function Escape-JsString {
  param([string]$Value)
  return ($Value -replace "\\", "\\\\" -replace "'", "\'" -replace "`r", "" -replace "`n", "\n")
}

Send-Cdp -Method "Runtime.enable" | Out-Null
Send-Cdp -Method "Page.enable" | Out-Null
Send-Cdp -Method "Emulation.setDeviceMetricsOverride" -Params @{
  width = 1440
  height = 900
  deviceScaleFactor = 1
  mobile = $false
} | Out-Null

Send-Cdp -Method "Page.navigate" -Params @{ url = $AppUrl } | Out-Null
Start-Sleep -Milliseconds 1500
$clearExpression = @"
(async () => {
  try {
    const response = await fetch('/api/sessions?limit=500');
    const payload = await response.json();
    for (const item of (payload.sessions || [])) {
      if (item.session_id) await fetch('/api/session/' + encodeURIComponent(item.session_id), { method: 'DELETE' });
    }
  } catch (error) {}
  try { localStorage.removeItem('aerokb.sessionId'); } catch (error) {}
  return 'cleared';
})()
"@
Send-Cdp -Method "Runtime.evaluate" -Params @{ expression = $clearExpression; awaitPromise = $true; returnByValue = $true } | Out-Null

$manifest = @()

foreach ($feature in $features) {
  $id = $feature.id
  $label = $feature.label
  $note = $feature.note
  Send-Cdp -Method "Page.navigate" -Params @{ url = "$AppUrl&feature=$id" } | Out-Null
  Start-Sleep -Milliseconds 1500

  $safeLabel = Escape-JsString $label
  $safeNote = Escape-JsString $note
  $expression = @"
(async () => {
  const label = '$safeLabel';
  const note = '$safeNote';
  const selector = '[data-feature="$id"]';
  const realFetch = window.fetch.bind(window);
  window.__agriFeatureTest = { feature: '$id', label, requests: [] };
  window.fetch = async (input, init = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    if (String(url).includes('/api/query')) {
      const body = JSON.parse(init.body || '{}');
      window.__agriFeatureTest.requests.push({ url: String(url), body });
      const answer = [
        'Function entry test passed: ' + label,
        '',
        'The button click entered the Q&A area and triggered /api/query.',
        'Scenario: ' + note + '.',
        'Request params: web_search=' + body.web_search + ', regional_intelligence=' + body.regional_intelligence + ', top_k=' + body.top_k + ', model=' + (body.model || 'default backend') + '.',
        'Delivery meaning: this entry is not a static label; users can click in and receive scene-specific information.'
      ].join('\n');
      return new Response(JSON.stringify({
        answer,
        selected_model: 'moonshot-v1-8k',
        session_id: 'pptx_feature_test_' + '$id',
        evidence: [],
        evidence_graph: { nodes: [], edges: [] },
        session_evidence_graph: {}
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }
    return realFetch(input, init);
  };
  const button = document.querySelector(selector);
  button.scrollIntoView({ block: 'center', inline: 'nearest' });
  button.style.outline = '3px solid #2F7D52';
  button.style.boxShadow = '0 0 0 6px rgba(47,125,82,0.18)';
  button.click();
  await new Promise((resolve) => setTimeout(resolve, 900));
  document.querySelector('#messages')?.scrollTo({ top: 9999 });
  return JSON.stringify({
    feature: '$id',
    label,
    request: window.__agriFeatureTest.requests[0],
    rendered: Array.from(document.querySelectorAll('#messages .message.assistant')).pop()?.outerHTML.includes('Function entry test passed') || false
  });
})()
"@

  $result = Send-Cdp -Method "Runtime.evaluate" -Params @{ expression = $expression; awaitPromise = $true; returnByValue = $true }
  if (-not $result.result.result.value) {
    throw "Feature $id evaluation failed: $($result | ConvertTo-Json -Depth 20)"
  }
  $info = $result.result.result.value | ConvertFrom-Json
  if (-not $info.rendered) { throw "Feature $id did not render its test answer." }

  Start-Sleep -Milliseconds 400
  $screenshot = Send-Cdp -Method "Page.captureScreenshot" -Params @{ format = "png"; fromSurface = $true }
  $fileName = "{0:D2}_{1}.png" -f ($manifest.Count + 1), $id
  $path = Join-Path $OutputDir $fileName
  [System.IO.File]::WriteAllBytes($path, [Convert]::FromBase64String($screenshot.result.data))
  $manifest += [pscustomobject]@{
    id = $id
    label = $label
    note = $note
    path = $path
    request = $info.request
  }
}

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", $ct).Wait()

Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" |
  Where-Object { $_.CommandLine -like "*--remote-debugging-port=$DebugPort*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

$manifestPath = Join-Path $OutputDir "manifest.json"
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
Write-Output $manifestPath

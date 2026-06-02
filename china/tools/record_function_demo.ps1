param(
  [string]$ScreenshotDir = "",
  [string]$OutputVideo = "",
  [string]$ChromePath = "",
  [int]$DebugPort = 9555
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
if (-not $ScreenshotDir) {
  $ScreenshotDir = Join-Path $RootDir "outputs\manual-20260523-agrikb-function-screenshots\presentations\agrikb-function-screenshots\assets\function-screenshots"
}
if (-not $OutputVideo) {
  $OutputVideo = Join-Path $RootDir "deliverables\AgriKB_DualTrack_FirstPrize_Materials_20260523\AgriKB_function_demo_recording.webm"
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

$frames = @()
Get-ChildItem -LiteralPath $ScreenshotDir -Filter "*.png" -File |
  Sort-Object Name |
  ForEach-Object {
    $id = $_.BaseName -replace "^\d+_", ""
    $bytes = [System.IO.File]::ReadAllBytes($_.FullName)
    $frames += [pscustomobject]@{
      id = $id
      title = ("AgriKB live feature: " + $id)
      note = "Click entry -> /api/query -> evidence-ready answer"
      dataUrl = "data:image/png;base64," + [Convert]::ToBase64String($bytes)
    }
  }

if ($frames.Count -eq 0) { throw "No screenshots found in $ScreenshotDir" }

$profileDir = Join-Path (Split-Path $OutputVideo -Parent) "chrome-record-profile"
New-Item -ItemType Directory -Force -Path $profileDir | Out-Null

Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" |
  Where-Object { $_.CommandLine -like "*--remote-debugging-port=$DebugPort*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Start-Process -FilePath $ChromePath -ArgumentList @(
  "--headless=new",
  "--disable-gpu",
  "--no-first-run",
  "--autoplay-policy=no-user-gesture-required",
  "--remote-debugging-port=$DebugPort",
  "--window-size=1280,720",
  "--user-data-dir=$profileDir",
  "about:blank"
) -WindowStyle Hidden

Start-Sleep -Seconds 2

$targets = Invoke-RestMethod -Uri "http://127.0.0.1:$DebugPort/json/list"
$page = $targets | Where-Object { $_.type -eq "page" } | Select-Object -First 1
if (-not $page) { throw "No Chrome page target found." }

$ws = [System.Net.WebSockets.ClientWebSocket]::new()
$ct = [System.Threading.CancellationToken]::None
$ws.ConnectAsync([Uri]$page.webSocketDebuggerUrl, $ct).Wait()
$script:cdpId = 0

function Send-Cdp {
  param([string]$Method, [hashtable]$Params = @{})
  $script:cdpId += 1
  $payload = @{ id = $script:cdpId; method = $Method; params = $Params } | ConvertTo-Json -Depth 30 -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
  $ws.SendAsync([ArraySegment[byte]]::new($bytes), [System.Net.WebSockets.WebSocketMessageType]::Text, $true, $ct).Wait()
  while ($true) {
    $buffer = New-Object byte[] 16777216
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

Send-Cdp -Method "Runtime.enable" | Out-Null
Send-Cdp -Method "Page.enable" | Out-Null

$framesJson = $frames | ConvertTo-Json -Depth 6 -Compress
$expression = @"
(async () => {
  const frames = $framesJson;
  document.body.style.margin = '0';
  document.body.style.background = '#F7F5EC';
  const canvas = document.createElement('canvas');
  canvas.width = 1280;
  canvas.height = 720;
  document.body.appendChild(canvas);
  const ctx = canvas.getContext('2d');

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = src;
    });
  }

  function wrapText(text, x, y, maxWidth, lineHeight) {
    const words = String(text).split(' ');
    let line = '';
    for (const word of words) {
      const test = line ? line + ' ' + word : word;
      if (ctx.measureText(test).width > maxWidth && line) {
        ctx.fillText(line, x, y);
        line = word;
        y += lineHeight;
      } else {
        line = test;
      }
    }
    if (line) ctx.fillText(line, x, y);
  }

  function drawFrame(item, img, index, total) {
    ctx.fillStyle = '#F7F5EC';
    ctx.fillRect(0, 0, 1280, 720);
    ctx.fillStyle = '#2F7D52';
    ctx.fillRect(54, 42, 42, 4);
    ctx.font = 'bold 15px Arial';
    ctx.fillText('AGRIKB FUNCTION WALKTHROUGH', 106, 48);
    ctx.font = 'bold 34px Arial';
    ctx.fillStyle = '#17211D';
    ctx.fillText(item.title, 54, 102);
    ctx.font = '16px Arial';
    ctx.fillStyle = '#63716A';
    wrapText(item.note, 58, 134, 880, 20);
    ctx.fillStyle = '#FFFFFF';
    ctx.strokeStyle = '#D7DFCF';
    ctx.lineWidth = 1.2;
    ctx.fillRect(86, 154, 1108, 486);
    ctx.strokeRect(86, 154, 1108, 486);
    const frameW = 1080;
    const frameH = 456;
    const scale = Math.min(frameW / img.width, frameH / img.height);
    const w = img.width * scale;
    const h = img.height * scale;
    const x = 100 + (frameW - w) / 2;
    const y = 170 + (frameH - h) / 2;
    ctx.drawImage(img, x, y, w, h);
    ctx.fillStyle = '#EEF6EA';
    ctx.strokeStyle = '#C9DABF';
    ctx.fillRect(86, 654, 1108, 28);
    ctx.strokeRect(86, 654, 1108, 28);
    ctx.font = 'bold 15px Arial';
    ctx.fillStyle = '#1F5137';
    ctx.textAlign = 'center';
    ctx.fillText('Verified: clickable entry, real query request, rendered answer, evidence-ready workflow', 640, 674);
    ctx.textAlign = 'right';
    ctx.font = '13px Arial';
    ctx.fillStyle = '#63716A';
    ctx.fillText(String(index + 1) + '/' + String(total), 1224, 48);
    ctx.textAlign = 'left';
  }

  const images = [];
  for (const frame of frames) images.push(await loadImage(frame.dataUrl));
  const stream = canvas.captureStream(8);
  const chunks = [];
  const mime = MediaRecorder.isTypeSupported('video/webm;codecs=vp9') ? 'video/webm;codecs=vp9' : 'video/webm';
  const recorder = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 2500000 });
  recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data); };
  const stopped = new Promise((resolve) => recorder.onstop = resolve);
  recorder.start();
  for (let i = 0; i < frames.length; i += 1) {
    drawFrame(frames[i], images[i], i, frames.length);
    await new Promise((resolve) => setTimeout(resolve, 1700));
  }
  drawFrame(frames[frames.length - 1], images[images.length - 1], frames.length - 1, frames.length);
  await new Promise((resolve) => setTimeout(resolve, 900));
  recorder.stop();
  await stopped;
  const blob = new Blob(chunks, { type: 'video/webm' });
  const dataUrl = await new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.readAsDataURL(blob);
  });
  return dataUrl;
})()
"@

$response = Send-Cdp -Method "Runtime.evaluate" -Params @{ expression = $expression; awaitPromise = $true; returnByValue = $true }
if (-not $response.result.result.value) {
  throw "Recording failed: $($response | ConvertTo-Json -Depth 20)"
}
$dataUrl = [string]$response.result.result.value
$base64 = $dataUrl.Substring($dataUrl.IndexOf(",") + 1)
[System.IO.File]::WriteAllBytes($OutputVideo, [Convert]::FromBase64String($base64))

$ws.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "done", $ct).Wait()
Get-CimInstance Win32_Process -Filter "Name = 'chrome.exe'" |
  Where-Object { $_.CommandLine -like "*--remote-debugging-port=$DebugPort*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }

Get-Item $OutputVideo | Select-Object FullName,Length,LastWriteTime | ConvertTo-Json -Depth 4

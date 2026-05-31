# JatayuCore MT5 Deployment — Windows VPS
# Run this PowerShell script AS ADMINISTRATOR on your Windows VPS.
# It installs everything needed and creates a scheduled task for 24/7 trading.

param(
    [string]$Tickers = "EURUSD,GBPUSD",
    [int]$Interval = 3,
    [string]$Broker = "mt5"
)

$ErrorActionPreference = "Stop"
$repoUrl = "https://github.com/komelImoet/JatayuCore.git"
$repoDir = "$env:USERPROFILE\JatayuCore"
$taskName = "JatayuCore-Trading"
$pythonVersion = "3.11"

Write-Host "=== JatayuCore MT5 Deployment ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $py = (Get-Command python -ErrorAction Stop).Source
    Write-Host "✅ Python: $py" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Install Python $pythonVersion from https://python.org" -ForegroundColor Red
    Write-Host "   Make sure to check 'Add Python to PATH' during installation."
    exit 1
}

# 2. Git clone / pull
if (Test-Path $repoDir) {
    Write-Host "📂 Repo exists, pulling latest..."
    Set-Location $repoDir
    git pull
} else {
    Write-Host "📂 Cloning repo..."
    git clone $repoUrl $repoDir
    Set-Location $repoDir
}
Write-Host "✅ Repo ready at $repoDir" -ForegroundColor Green

# 3. Install Python dependencies
Write-Host "📦 Installing dependencies..."
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q
pip install MetaTrader5 -q
Write-Host "✅ Dependencies installed" -ForegroundColor Green

# 4. Create .env if not exists
$envFile = "$repoDir\.env"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "⚠️  .env file not found. Creating template..." -ForegroundColor Yellow
@"
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DEEPSEEK_API_KEY=
MT5_LOGIN=
MT5_PASSWORD=
MT5_SERVER=
"@ | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "❌ EDIT $envFile with your credentials before running!" -ForegroundColor Red
    notepad $envFile
} else {
    Write-Host "✅ .env exists" -ForegroundColor Green
}

# 5. Create scheduled task for auto-start
$pythonExe = (Get-Command python).Source
$scriptPath = "$repoDir\run_jatayu.bat"

@"
@echo off
cd /d "$repoDir"
$pythonExe main.py schedule --tickers $Tickers --interval $Interval --broker $Broker
"@ | Out-File -FilePath $scriptPath -Encoding ascii

$action = New-ScheduledTaskAction -Execute $scriptPath
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Days 365)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force

Write-Host ""
Write-Host "=== ✅ DEPLOYMENT COMPLETE ===" -ForegroundColor Cyan
Write-Host "📌 Task '$taskName' created — bot auto-starts on boot" -ForegroundColor Green
Write-Host ""
Write-Host "MANUAL STEPS:" -ForegroundColor Yellow
Write-Host "1. Install MetaTrader 5 on this VPS" -ForegroundColor Yellow
Write-Host "2. Login to your broker in MT5 (File → Login to Trade Account)" -ForegroundColor Yellow
Write-Host "3. Fill .env file: $envFile" -ForegroundColor Yellow
Write-Host "4. Test run: python main.py schedule --broker mt5 --tickers $Tickers" -ForegroundColor Yellow
Write-Host "5. Reboot VPS to verify auto-start, or run task manually in Task Scheduler" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press Enter to open Task Scheduler..." -ForegroundColor Gray
Read-Host
taskschd.msc

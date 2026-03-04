Write-Host "=== Nanobot 安全检查 ===" -ForegroundColor Cyan

# 1. 检查配置文件权限
$configPath = "$env:USERPROFILE\.nanobot\config.json"
if (Test-Path $configPath) {
    $acl = Get-Acl $configPath
    $hasOtherAccess = $acl.Access | Where-Object { 
        $_.IdentityReference -notmatch $env:USERNAME -and 
        $_.IdentityReference -notmatch "SYSTEM" -and
        $_.IdentityReference -notmatch "BUILTIN\\Administrators"
    }
    if ($hasOtherAccess) {
        Write-Host "❌ 配置文件权限不安全：存在其他用户访问权限" -ForegroundColor Red
    } else {
        Write-Host "✅ 配置文件权限安全" -ForegroundColor Green
    }
} else {
    Write-Host "⚠️  配置文件不存在" -ForegroundColor Yellow
}

# 2. 检查工作区限制
if (Test-Path $configPath) {
    $config = Get-Content $configPath | ConvertFrom-Json
    if ($config.tools.restrictToWorkspace) {
        Write-Host "✅ 工作区限制已启用" -ForegroundColor Green
    } else {
        Write-Host "⚠️  工作区限制未启用（建议启用）" -ForegroundColor Yellow
    }
}

# 3. 检查依赖更新
Write-Host "`n检查依赖安全更新..." -ForegroundColor Cyan
pip list --outdated --format=json | ConvertFrom-Json | Where-Object { 
    $_.name -match "(litellm|httpx|botpy)" 
} | ForEach-Object {
    Write-Host "⚠️  $($_.name): $($_.version) -> $($_.latest_version)" -ForegroundColor Yellow
}

# 4. 检查日志文件大小
$logPath = "$env:USERPROFILE\.nanobot\logs\nanobot.log"
if (Test-Path $logPath) {
    $logSize = (Get-Item $logPath).Length / 1MB
    if ($logSize -gt 10) {
        Write-Host "⚠️  日志文件过大：$([math]::Round($logSize, 2)) MB" -ForegroundColor Yellow
    } else {
        Write-Host "✅ 日志文件大小正常" -ForegroundColor Green
    }
}

Write-Host "`n=== 检查完成 ===" -ForegroundColor Cyan
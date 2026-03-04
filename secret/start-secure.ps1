# 安全启动脚本
$ErrorActionPreference = "Stop"

# 检查配置文件权限
$configPath = "$env:USERPROFILE\.nanobot\config.json"
if (Test-Path $configPath) {
    $acl = Get-Acl $configPath
    $access = $acl.Access | Where-Object { $_.IdentityReference -eq $env:USERNAME }
    if ($access.FileSystemRights -notlike "*FullControl*") {
        Write-Warning "配置文件权限不安全，正在修复..."
        # 设置权限代码（同上）
    }
}

# 检查工作区限制
$config = Get-Content $configPath | ConvertFrom-Json
if (-not $config.tools.restrictToWorkspace) {
    Write-Warning "建议启用 restrictToWorkspace 以增强安全性"
}

# 启动 nanobot
Write-Host "启动 nanobot（安全模式）..." -ForegroundColor Green
python -m nanobot
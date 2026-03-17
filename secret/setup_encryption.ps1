#Requires -Version 5.1
<#
.SYNOPSIS
    nanobot加密密钥生成和管理脚本

.DESCRIPTION
    此脚本用于生成安全的加密密钥并配置到环境变量中
    支持Windows系统的环境变量设置

.EXAMPLE
    .\setup_encryption.ps1
    运行配置向导

.EXAMPLE
    .\setup_encryption.ps1 -GenerateOnly
    仅生成密钥，不设置环境变量

.EXAMPLE
    .\setup_encryption.ps1 -Backup
    备份现有密钥
#>

[CmdletBinding()]
param(
    [switch]$GenerateOnly,
    [switch]$Backup,
    [switch]$Force
)

# 生成随机密钥的函数
function New-EncryptionKey {
    <#
    .SYNOPSIS
        生成新的加密密钥
    #>
    param(
        [int]$Length = 32
    )

    $chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*'
    $key = -join ((1..$Length) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
    return $key
}

# 设置环境变量的函数
function Set-EncryptionEnvironment {
    <#
    .SYNOPSIS
        设置加密环境变量
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$SessionKey,

        [Parameter(Mandatory=$false)]
        [string]$TransportKey,

        [Parameter(Mandatory=$false)]
        [ValidateSet("User", "Machine")]
        [string]$Scope = "User"
    )

    try {
        # 设置会话加密密钥
        [Environment]::SetEnvironmentVariable("NANOBOT_ENCRYPTION_KEY", $SessionKey, $Scope)

        # 设置传输加密密钥
        if (-not $TransportKey) {
            $TransportKey = New-EncryptionKey -Length 32
        }
        [Environment]::SetEnvironmentVariable("NANOBOT_TRANSPORT_KEY", $TransportKey, $Scope)

        # 同时设置当前会话的环境变量
        $env:NANOBOT_ENCRYPTION_KEY = $SessionKey
        $env:NANOBOT_TRANSPORT_KEY = $TransportKey

        Write-Host "✓ 加密密钥已成功设置到环境变量" -ForegroundColor Green
        Write-Host "  作用域: $Scope" -ForegroundColor Cyan
        Write-Host ""

        return $true
    }
    catch {
        Write-Host "✗ 设置环境变量失败: $_" -ForegroundColor Red
        return $false
    }
}

# 备份密钥的函数
function Backup-EncryptionKeys {
    <#
    .SYNOPSIS
        备份加密密钥到安全文件
    #>
    param(
        [string]$BackupPath = "$env:USERPROFILE\.nanobot\keys_backup.txt"
    )

    $encryptionKey = [Environment]::GetEnvironmentVariable("NANOBOT_ENCRYPTION_KEY", "User")
    $transportKey = [Environment]::GetEnvironmentVariable("NANOBOT_TRANSPORT_KEY", "User")

    if (-not $encryptionKey -and -not $transportKey) {
        Write-Host "⚠ 未找到现有密钥，无需备份" -ForegroundColor Yellow
        return $false
    }

    $backupContent = @"
# nanobot加密密钥备份
# 生成时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# ⚠️  请妥善保管此文件，不要分享给他人！
# ============================================

会话加密密钥 (NANOBOT_ENCRYPTION_KEY):
$encryptionKey

传输加密密钥 (NANOBOT_TRANSPORT_KEY):
$transportKey

# 恢复说明:
# 1. 以管理员身份运行PowerShell
# 2. 执行以下命令:
#    [Environment]::SetEnvironmentVariable("NANOBOT_ENCRYPTION_KEY", "$encryptionKey", "User")
#    [Environment]::SetEnvironmentVariable("NANOBOT_TRANSPORT_KEY", "$transportKey", "User")
"@

    try {
        # 确保目录存在
        $backupDir = Split-Path -Parent $BackupPath
        if (-not (Test-Path $backupDir)) {
            New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        }

        # 写入备份文件
        $backupContent | Out-File -FilePath $BackupPath -Encoding UTF8 -Force

        # 设置文件权限（仅当前用户可访问）
        $acl = Get-Acl $BackupPath
        $acl.SetAccessRuleProtection($true, $false)

        # 移除所有现有权限
        $acl.Access | ForEach-Object { $acl.RemoveAccessRule($_) | Out-Null }

        # 添加当前用户权限
        $userRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $env:USERNAME,
            "FullControl",
            "Allow"
        )
        $acl.SetAccessRule($userRule)
        Set-Acl $BackupPath $acl

        Write-Host "✓ 密钥已备份到: $BackupPath" -ForegroundColor Green
        Write-Host "  文件权限已设置为仅当前用户可访问" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "✗ 备份失败: $_" -ForegroundColor Red
        return $false
    }
}

# 显示当前状态
function Show-CurrentStatus {
    $sessionKey = [Environment]::GetEnvironmentVariable("NANOBOT_ENCRYPTION_KEY", "User")
    $transportKey = [Environment]::GetEnvironmentVariable("NANOBOT_TRANSPORT_KEY", "User")

    Write-Host ""
    Write-Host "当前加密配置状态:" -ForegroundColor Cyan
    Write-Host "----------------------------------------" -ForegroundColor Gray

    if ($sessionKey) {
        $maskedKey = $sessionKey.Substring(0, [Math]::Min(8, $sessionKey.Length)) + "***"
        Write-Host "  会话加密密钥: 已设置 ($maskedKey)" -ForegroundColor Green
    }
    else {
        Write-Host "  会话加密密钥: 未设置" -ForegroundColor Red
    }

    if ($transportKey) {
        $maskedKey = $transportKey.Substring(0, [Math]::Min(8, $transportKey.Length)) + "***"
        Write-Host "  传输加密密钥: 已设置 ($maskedKey)" -ForegroundColor Green
    }
    else {
        Write-Host "  传输加密密钥: 未设置" -ForegroundColor Red
    }

    Write-Host "----------------------------------------" -ForegroundColor Gray
    Write-Host ""
}

# 主配置向导
function Start-ConfigurationWizard {
    Clear-Host
    Write-Host "🔐 nanobot安全配置向导" -ForegroundColor Cyan
    Write-Host "======================================" -ForegroundColor Cyan
    Write-Host ""

    Show-CurrentStatus

    # 检查是否已有密钥
    $existingSessionKey = [Environment]::GetEnvironmentVariable("NANOBOT_ENCRYPTION_KEY", "User")
    if ($existingSessionKey -and -not $Force) {
        Write-Host "⚠️ 检测到已有加密密钥配置" -ForegroundColor Yellow
        $overwrite = Read-Host "是否覆盖现有密钥? (y/N)"
        if ($overwrite -ne 'y') {
            Write-Host "操作已取消" -ForegroundColor Yellow
            return
        }

        # 先备份
        Write-Host ""
        Write-Host "正在备份现有密钥..." -ForegroundColor Cyan
        Backup-EncryptionKeys
        Write-Host ""
    }

    # 生成新密钥
    Write-Host "正在生成新的加密密钥..." -ForegroundColor Cyan
    $sessionKey = New-EncryptionKey -Length 32
    $transportKey = New-EncryptionKey -Length 32

    Write-Host "✓ 新密钥已生成" -ForegroundColor Green
    Write-Host ""

    # 设置环境变量
    Write-Host "正在设置环境变量..." -ForegroundColor Cyan
    if (Set-EncryptionEnvironment -SessionKey $sessionKey -TransportKey $transportKey -Scope "User") {
        Write-Host ""
        Write-Host "======================================" -ForegroundColor Cyan
        Write-Host "配置完成！" -ForegroundColor Green
        Write-Host "======================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "⚠️  重要提示:" -ForegroundColor Yellow
        Write-Host "   - 请妥善保管加密密钥" -ForegroundColor Yellow
        Write-Host "   - 密钥用于加密会话数据，丢失后无法解密" -ForegroundColor Yellow
        Write-Host "   - 建议立即备份密钥" -ForegroundColor Yellow
        Write-Host ""

        $backupNow = Read-Host "是否立即备份密钥? (Y/n)"
        if ($backupNow -ne 'n') {
            Write-Host ""
            Backup-EncryptionKeys
        }

        Write-Host ""
        Write-Host "配置说明:" -ForegroundColor Cyan
        Write-Host "  1. 重新启动终端以使用新的环境变量" -ForegroundColor White
        Write-Host "  2. 在config.json中启用加密功能:" -ForegroundColor White
        Write-Host @"
     {
       "security": {
         "enableSessionEncryption": true,
         "enableLogSanitization": true
       }
     }
"@ -ForegroundColor Gray
    }
}

# 主程序逻辑
if ($Backup) {
    Backup-EncryptionKeys
}
elseif ($GenerateOnly) {
    Write-Host "生成的加密密钥:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "会话加密密钥: $(New-EncryptionKey -Length 32)" -ForegroundColor Green
    Write-Host "传输加密密钥: $(New-EncryptionKey -Length 32)" -ForegroundColor Green
    Write-Host ""
    Write-Host "请手动设置到环境变量:" -ForegroundColor Yellow
    Write-Host '[Environment]::SetEnvironmentVariable("NANOBOT_ENCRYPTION_KEY", "<密钥>", "User")' -ForegroundColor Gray
    Write-Host '[Environment]::SetEnvironmentVariable("NANOBOT_TRANSPORT_KEY", "<密钥>", "User")' -ForegroundColor Gray
}
else {
    Start-ConfigurationWizard
}

Write-Host ""
Write-Host "按任意键退出..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

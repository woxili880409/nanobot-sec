# 生成nanobot加密密钥
# 确保输出编码为 UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$sessionKey = -join ((65..90) + (97..122) + (48..57) + 33,35,36,37,38,42 | Get-Random -Count 32 | ForEach-Object {[char]$_})
$transportKey = -join ((65..90) + (97..122) + (48..57) + 33,35,36,37,38,42 | Get-Random -Count 32 | ForEach-Object {[char]$_})

Write-Host "会话加密密钥: $sessionKey"
Write-Host "传输加密密钥: $transportKey"
Write-Host ""
Write-Host "请运行以下命令设置环境变量:"
Write-Host "[Environment]::SetEnvironmentVariable('NANOBOT_ENCRYPTION_KEY', '$sessionKey', 'User')"
Write-Host "[Environment]::SetEnvironmentVariable('NANOBOT_TRANSPORT_KEY', '$transportKey', 'User')"
Write-Host ""
Write-Host "按任意键退出..."
$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown') | Out-Null

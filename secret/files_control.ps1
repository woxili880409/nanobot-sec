# 设置配置文件权限（仅当前用户可读写）
$acl = Get-Acl "$env:USERPROFILE\.nanobot\config.json"
$accessRule = New-Object System.Security.AccessControl.FileSystemAccessRule(
    $env:USERNAME,
    "FullControl",
    "Allow"
)
$acl.SetAccessRule($accessRule)
# 禁用继承
$acl.SetAccessRuleProtection($true, $false)
Set-Acl "$env:USERPROFILE\.nanobot\config.json" $acl
# 设置环境变量（仅当前会话）
$env:NANOBOT_CHANNELS__QQ__APP_ID = "your_app_id"
$env:NANOBOT_CHANNELS__QQ__SECRET = "your_secret"
$env:NANOBOT_PROVIDERS__CUSTOM__API_KEY = "your_api_key"

# 永久设置（添加到系统环境变量）
[System.Environment]::SetEnvironmentVariable('NANOBOT_CHANNELS__QQ__APP_ID', 'your_app_id', 'User')
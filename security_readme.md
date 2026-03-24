# Nanobot 安全功能文档

## 概述

本文档总结了 Nanobot P0 阶段安全优化的所有变更和使用方法。这些优化旨在提高系统的安全性，包括会话加密、日志脱敏和密钥管理。

## 主要安全功能

### 1. 日志脱敏功能

**功能描述**：自动过滤日志中的敏感信息，防止敏感数据泄露。

**特性**：
- ✅ 可配置开关（默认开启）
- ✅ 支持多种敏感信息类型
- ✅ 支持自定义脱敏规则

**支持的敏感信息类型**：
- API密钥、Token、Secret
- 邮箱地址
- 电话号码（中国大陆、国际格式）
- IP地址
- Telegram Bot Token
- 身份证号
- 银行卡号

### 2. 会话加密功能

**功能描述**：使用 AES-256-GCM 算法加密会话数据，保护用户聊天记录的安全性。

**特性**：
- ✅ AES-256-GCM 强加密算法
- ✅ 支持加密/解密消息
- ✅ 系统消息保留明文（便于调试）
- ✅ 用户和助手消息自动加密
- ✅ 支持密钥管理和备份

### 3. 配置管理

**配置文件**：`config.json` 中添加安全配置部分

```json
{
  "security": {
    "enableLogSanitization": true,      // 启用日志脱敏（默认开启）
    "sanitizationPatterns": [],        // 自定义脱敏规则
    "enableSessionEncryption": false,   // 启用会话加密（默认关闭）
    "encryptionKey": "",               // 会话加密密钥（优先使用环境变量）
    "enableTransportEncryption": false,// 启用传输加密（默认关闭）
    "transportKey": "",               // 传输加密密钥（优先使用环境变量）
    "secureFilePermissions": true     // 设置敏感文件的安全权限（默认开启）
  }
}
```

### 4. 环境变量支持

系统优先使用环境变量中的密钥，增强安全性：

- `NANOBOT_ENCRYPTION_KEY`: 会话加密密钥
- `NANOBOT_TRANSPORT_KEY`: 传输加密密钥

## 使用方法

### 第一步：生成加密密钥

使用提供的密钥生成脚本：

```powershell
# 在项目根目录运行
.\secret\generate_keys.ps1
```

脚本将生成随机密钥并显示设置环境变量的命令。

### 第二步：设置环境变量

复制脚本输出的命令并执行：

```powershell
[Environment]::SetEnvironmentVariable('NANOBOT_ENCRYPTION_KEY', '你的密钥', 'User')
[Environment]::SetEnvironmentVariable('NANOBOT_TRANSPORT_KEY', '你的密钥', 'User')
```

### 第三步：启用加密功能

编辑 `config.json` 文件，启用加密功能：

```json
{
  "security": {
    "enableSessionEncryption": true,
    "enableLogSanitization": true
  }
}
```

### 第四步：运行程序

使用常规命令运行 nanobot：

```bash
# 启动网关
nanobot gateway

# 运行代理
nanobot agent
```

## 技术实现细节

### 核心文件结构

```
nanobot/
├── security/
│   ├── __init__.py          # 安全模块导出
│   ├── encryption.py        # 加密核心实现
│   └── logging.py           # 日志脱敏实现
├── config/
│   └── schema.py            # 安全配置schema
├── session/
│   └── manager.py           # 加密会话管理
└── cli/
    └── commands.py          # 安全功能集成
```

### 加密算法

- **算法**: AES-256-GCM
- **密钥长度**: 256位（32字节）
- **特点**:
  - 提供认证加密（AEAD）
  - 防止篡改
  - 支持消息认证

### 日志脱敏实现

使用正则表达式模式匹配敏感信息：

```python
# API密钥示例
(api[_-]?key|token|secret)=***REDACTED***

# 邮箱地址
***@***.***

# 电话号码
***-****-****

# IP地址
***.***.***.***
```

## 测试验证

项目包含完整的单元测试，验证所有安全功能：

```bash
# 运行安全测试
python -m pytest tests/test_security_encryption.py -v
```

测试覆盖：
- ✅ 数据加密和解密
- ✅ 会话消息加密
- ✅ 日志脱敏功能
- ✅ 密钥生成和管理
- ✅ 集成测试

## 安全性最佳实践

1. **密钥管理**:
   - 定期备份加密密钥
   - 不要将密钥硬编码在代码中
   - 使用环境变量存储密钥

2. **文件安全**:
   - 敏感文件设置严格的访问权限
   - 定期清理不需要的日志文件

3. **配置安全**:
   - 生产环境启用加密功能
   - 开发环境可选择性关闭加密便于调试

## 故障排除

### 常见问题

1. **密钥丢失**
   - 后果：无法解密现有会话数据
   - 解决方案：定期备份密钥，使用密钥备份脚本

2. **加密错误**
   - 检查环境变量是否正确设置
   - 验证 cryptography 库是否安装：`pip install cryptography`

3. **日志脱敏不生效**
   - 检查配置文件中 `enableLogSanitization` 是否为 `true`
   - 查看日志级别设置

## 更新记录

### v1.0.0 (2026-03-17)
- ✅ 实现日志脱敏功能
- ✅ 实现会话加密功能
- ✅ 添加安全配置schema
- ✅ 集成安全功能到主程序
- ✅ 添加密钥生成脚本
- ✅ 编写完整测试用例

## 支持与反馈

如有安全相关问题，请通过项目 issue 系统提交反馈。

---

**注意**: 本文档仅涵盖 P0 阶段的安全功能，后续阶段可能会添加更多安全特性。

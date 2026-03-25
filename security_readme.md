# Nanobot 安全功能文档

## 概述

本文档总结了 Nanobot P0 和 P1 阶段安全优化的所有变更和使用方法。这些优化旨在全面提升系统安全性，包括会话加密、日志脱敏、传输加密和文件权限控制。

## P0 阶段安全优化

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

**关键代码实现**：

```python
# nanobot/security/logging.py
class LogSanitizer:
    PATTERNS = [
        # API密钥、Token、Secret等
        (
            r'(api[_-]?key|apikey|token|secret|password)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{8,})["\']?',
            r'\1=***REDACTED***',
        ),
        # 邮箱地址
        (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'***@***.***',
        ),
        # 电话号码
        (
            r'\b(\+?86[-\s]?)?1[3-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'***-****-****',
        ),
    ]
    
    @classmethod
    def sanitize(cls, message: str) -> str:
        """脱敏日志消息"""
        if not message or not isinstance(message, str):
            return message
        sanitized = message
        for pattern, replacement in cls.PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized
```

### 2. 会话加密功能

**功能描述**：使用 AES-256-GCM 算法加密会话数据，保护用户聊天记录的安全性。

**特性**：
- ✅ AES-256-GCM 强加密算法
- ✅ 支持加密/解密消息
- ✅ 系统消息保留明文（便于调试）
- ✅ 用户和助手消息自动加密
- ✅ 支持密钥管理和备份

**关键代码实现**：

```python
# nanobot/security/encryption.py
class SessionEncryption:
    """会话数据加密管理器"""
    
    ENCRYPTED_ROLES = {"user", "assistant"}
    
    def encrypt_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """加密单个消息"""
        if not self.should_encrypt_message(msg):
            return msg
            
        msg_copy = msg.copy()
        content = msg_copy.get("content", "")
        if content:
            msg_copy["content"] = self.encryption.encrypt(content)
            msg_copy["_encrypted"] = True
            msg_copy["_encryption_version"] = "1.0"
        return msg_copy
        
    def decrypt_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """解密单个消息"""
        if msg.get("_encrypted", False):
            msg_copy = msg.copy()
            encrypted_content = msg_copy.get("content", "")
            if encrypted_content:
                msg_copy["content"] = self.encryption.decrypt(encrypted_content)
                del msg_copy["_encrypted"]
                del msg_copy["_encryption_version"]
            return msg_copy
        return msg
```

## P1 阶段安全优化

### 1. 传输加密功能

**功能描述**：为通道间的消息传输提供端到端加密，防止消息在传输过程中被截获和读取。

**特性**：
- ✅ 集成到 MessageBus 中，自动加密/解密
- ✅ 支持 InboundMessage 和 OutboundMessage
- ✅ 通过元数据标记加密状态
- ✅ 可配置开关（默认关闭）

**关键代码实现**：

```python
# nanobot/bus/queue.py
class MessageBus:
    def __init__(self, transport_encryption: Optional[TransportEncryption] = None):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self.transport_encryption = transport_encryption
        
    async def publish_inbound(self, msg: InboundMessage) -> None:
        """发布入站消息，自动加密"""
        if self.transport_encryption and self.transport_encryption.enabled:
            encrypted_content, updated_metadata = self.transport_encryption.encrypt_message(
                msg.content, msg.metadata.copy()
            )
            encrypted_msg = InboundMessage(
                channel=msg.channel,
                sender_id=msg.sender_id,
                chat_id=msg.chat_id,
                content=encrypted_content,
                metadata=updated_metadata,
            )
            await self.inbound.put(encrypted_msg)
        else:
            await self.inbound.put(msg)
            
    async def consume_inbound(self) -> InboundMessage:
        """消费入站消息，自动解密"""
        msg = await self.inbound.get()
        if self.transport_encryption and self.transport_encryption.enabled:
            decrypted_content = self.transport_encryption.decrypt_message(
                msg.content, msg.metadata
            )
            if decrypted_content != msg.content:
                return InboundMessage(
                    channel=msg.channel,
                    sender_id=msg.sender_id,
                    chat_id=msg.chat_id,
                    content=decrypted_content,
                    metadata=msg.metadata,
                )
        return msg
```

### 2. 文件权限控制功能

**功能描述**：自动设置敏感文件的安全权限，防止未授权访问。

**特性**：
- ✅ 跨平台支持（Windows/Unix）
- ✅ 自动扫描敏感文件和目录
- ✅ 可配置开关（默认开启）
- ✅ 支持权限验证和检查

**关键代码实现**：

```python
# nanobot/security/file_permissions.py
class FilePermissionManager:
    """文件权限管理器"""
    
    PROTECTED_PATTERNS = ["*.json", "*.key", "*.pem", "*.env", "*.txt", "*.log"]
    PROTECTED_DIRECTORIES = [".nanobot", "secret", "sessions", "workspace"]
    
    def set_secure_permissions(self, file_path: Path) -> bool:
        """设置文件的安全权限"""
        if os.name == 'nt':  # Windows系统
            logger.debug(f"Windows系统：跳过文件权限设置: {file_path}")
            return True
        else:  # Unix/Linux系统
            if file_path.is_file():
                file_path.chmod(0o600)  # 只有所有者可读写
            elif file_path.is_dir():
                file_path.chmod(0o700)  # 只有所有者可读写执行
            return True
            
    def protect_workspace(self, workspace_path: Path) -> int:
        """保护工作区中的所有敏感文件"""
        logger.info(f"开始保护工作区敏感文件: {workspace_path}")
        sensitive_files = self.scan_directory(workspace_path)
        protected_count = 0
        for file_path in sensitive_files:
            if self.set_secure_permissions(file_path):
                protected_count += 1
        logger.info(f"已保护 {protected_count} 个敏感文件")
        return protected_count
```

## 配置管理

### 配置文件

在 `config.json` 中添加安全配置部分：

```json
{
"security": {
    "enableLogSanitization": true,      // P0: 启用日志脱敏（默认开启）
    "sanitizationPatterns": [],        // P0: 自定义脱敏规则
    "enableSessionEncryption": false,   // P0: 启用会话加密（默认关闭）
    "encryptionKey": "",               // P0: 会话加密密钥（优先使用环境变量）
    "enableTransportEncryption": false,// P1: 启用传输加密（默认关闭）
    "transportKey": "",               // P1: 传输加密密钥（优先使用环境变量）
    "secureFilePermissions": true     // P1: 设置敏感文件的安全权限（默认开启）
}
}
```

### 环境变量支持

系统优先使用环境变量中的密钥，增强安全性：

- `NANOBOT_ENCRYPTION_KEY`: 会话加密密钥（P0）
- `NANOBOT_TRANSPORT_KEY`: 传输加密密钥（P1）

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

### 第三步：启用安全功能

编辑 `config.json` 文件，启用所需的安全功能：

#### 仅启用P0功能（基础安全）：
```json
{
"security": {
    "enableSessionEncryption": true,
    "enableLogSanitization": true
}
}
```

#### 启用全部安全功能：
```json
{
"security": {
    "enableSessionEncryption": true,
    "enableLogSanitization": true,
    "enableTransportEncryption": true,
    "secureFilePermissions": true
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
│   ├── __init__.py              # 安全模块导出
│   ├── encryption.py            # 加密核心实现（P0: 会话加密, P1: 传输加密）
│   ├── logging.py               # 日志脱敏实现（P0）
│   └── file_permissions.py      # 文件权限控制实现（P1）
├── bus/
│   └── queue.py                 # 消息总线集成传输加密（P1）
├── config/
│   └── schema.py                # 安全配置schema
├── session/
│   └── manager.py               # 加密会话管理（P0）
└── cli/
    └── commands.py              # 安全功能集成
```

### 加密算法

- **算法**: AES-256-GCM
- **密钥长度**: 256位（32字节）
- **特点**:
  - 提供认证加密（AEAD）
  - 防止篡改
  - 支持消息认证

## 测试验证

项目包含完整的单元测试，验证所有安全功能：

```bash
# 运行P0安全测试
python -m pytest tests/test_security_encryption.py -v

# 运行P1安全测试
python -m pytest tests/test_security_p1.py -v
```

测试覆盖：
- ✅ 数据加密和解密
- ✅ 会话消息加密
- ✅ 日志脱敏功能
- ✅ 传输加密功能
- ✅ 文件权限控制
- ✅ 跨平台兼容性
- ✅ 集成测试

## 安全性最佳实践

1. **密钥管理**:
   - 定期备份加密密钥
   - 不要将密钥硬编码在代码中
   - 使用环境变量存储密钥

2. **文件安全**:
   - 敏感文件设置严格的访问权限
   - 定期清理不需要的日志文件
   - 在Unix系统上使用600/700权限

3. **配置安全**:
   - 生产环境启用所有安全功能
   - 开发环境可选择性关闭加密便于调试
   - 定期检查文件权限

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

4. **传输加密失败**
   - 检查 `enableTransportEncryption` 是否启用
   - 验证 `NANOBOT_TRANSPORT_KEY` 环境变量

5. **文件权限设置失败**
   - Windows系统：跳过权限设置（不支持Unix风格权限）
   - Unix系统：检查用户权限是否足够

## 更新记录

### P0阶段 (2026-03-17)
- ✅ 实现日志脱敏功能
- ✅ 实现会话加密功能
- ✅ 添加安全配置schema
- ✅ 集成安全功能到主程序
- ✅ 添加密钥生成脚本
- ✅ 编写完整测试用例

### P1阶段 (2026-03-26)
- ✅ 实现传输加密功能
- ✅ 实现文件权限控制功能
- ✅ 集成传输加密到消息总线
- ✅ 添加跨平台文件权限支持
- ✅ 编写P1阶段测试用例

## 强制中止服务功能

**功能描述**：通过对话方式安全地强制中止正在运行的 nanobot gateway 服务。

**使用方法**：

1. **发起中止请求**：
   ```
   /shutdown
   ```

2. **二次确认**：系统会提示需要输入密码进行确认

3. **密码验证**：
   ```
   /shutdown confirm czzzho
   ```

**安全特性**：
- ✅ 需要二次确认防止误操作
- ✅ 需要密码验证（默认密码：czzzho）
- ✅ 安全关闭所有服务和连接
- ✅ 支持通过任何对话渠道触发

**注意事项**：
- 此功能仅在 gateway 模式下可用
- 一旦确认关闭，无法取消
- 建议在紧急情况下使用

## PowerShell 安全脚本

### 脚本概览

项目提供了多个 PowerShell 脚本用于安全配置和管理，位于 `secret/` 目录下。

### 1. setup_encryption.ps1

**功能描述**：完整的加密配置向导，用于生成和管理加密密钥。

**兼容性**：
- ✅ PowerShell 5.1+
- ✅ PowerShell 7.0+

**主要功能**：
- 生成安全的加密密钥
- 自动设置环境变量
- 备份现有密钥
- 显示当前配置状态

**使用方法**：

```powershell
# 运行配置向导
.\secret\setup_encryption.ps1

# 仅生成密钥，不设置环境变量
.\secret\setup_encryption.ps1 -GenerateOnly

# 备份现有密钥
.\secret\setup_encryption.ps1 -Backup
```

**关键特性**：
- 支持密钥备份和恢复
- 自动设置文件权限保护备份文件
- 提供交互式配置界面

### 2. generate_keys.ps1

**功能描述**：简单的密钥生成脚本，适合快速生成密钥。

**兼容性**：
- ✅ PowerShell 5.0+
- ✅ PowerShell 7.0+

**使用方法**：

```powershell
.\secret\generate_keys.ps1
```

**注意事项**：
- 生成密钥后需要手动设置环境变量
- 脚本会显示设置环境变量的命令
- 适合需要手动管理密钥的场景

### 3. security-check.ps1

**功能描述**：安全配置检查脚本，验证系统安全性。

**兼容性**：
- ✅ PowerShell 5.0+
- ✅ PowerShell 7.0+

**检查项目**：
- 配置文件权限安全性
- 工作区限制设置
- 依赖包安全更新
- 日志文件大小检查

**使用方法**：

```powershell
.\secret\security-check.ps1
```

### 4. files_control.ps1

**功能描述**：设置配置文件的安全权限。

**兼容性**：
- ✅ PowerShell 5.0+
- ✅ PowerShell 7.0+

**使用方法**：

```powershell
.\secret\files_control.ps1
```

**功能**：将配置文件权限设置为仅当前用户可访问。

### 5. start-secure.ps1

**功能描述**：安全启动脚本，在启动前检查安全配置。

**兼容性**：
- ✅ PowerShell 5.0+
- ✅ PowerShell 7.0+

**使用方法**：

```powershell
.\secret\start-secure.ps1
```

**安全检查**：
- 验证配置文件权限
- 检查工作区限制设置
- 安全启动 nanobot

### 6. secret_envs.ps1

**功能描述**：环境变量设置模板，用于配置敏感信息。

**兼容性**：
- ✅ PowerShell 5.0+
- ✅ PowerShell 7.0+

**使用方法**：
1. 编辑脚本，填入实际的敏感信息
2. 运行脚本设置环境变量

```powershell
# 编辑脚本配置敏感信息
notepad .\secret\secret_envs.ps1

# 运行脚本设置环境变量
.\secret\secret_envs.ps1
```

### 脚本比较

| 脚本名称 | PowerShell版本 | 主要功能 | 环境变量设置 |
|---------|--------------|---------|-------------|
| setup_encryption.ps1 | 5.1+ | 完整配置向导 | 自动设置 |
| generate_keys.ps1 | 5.0+ | 简单密钥生成 | 手动设置 |
| security-check.ps1 | 5.0+ | 安全检查 | - |
| files_control.ps1 | 5.0+ | 文件权限设置 | - |
| start-secure.ps1 | 5.0+ | 安全启动 | - |
| secret_envs.ps1 | 5.0+ | 环境变量模板 | 手动配置 |

### 推荐使用流程

1. **首次配置**：使用 `setup_encryption.ps1` 进行完整配置
2. **定期检查**：使用 `security-check.ps1` 检查安全状态
3. **密钥管理**：定期使用 `setup_encryption.ps1 -Backup` 备份密钥
4. **安全启动**：使用 `start-secure.ps1` 启动程序

## 支持与反馈

如有安全相关问题，请通过项目 issue 系统提交反馈。

---

**注意**: 本文档涵盖 P0 和 P1 阶段的所有安全功能，后续阶段可能会添加更多安全特性。

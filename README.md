<div align="center">
  <img src="nanobot_logo.png" alt="nanobot" width="500">
  <h1>nanobot: 超轻量级个人AI助手（优化版）</h1>
  <p>
    <a href="https://pypi.org/project/nanobot-ai/"><img src="https://img.shields.io/pypi/v/nanobot-ai" alt="PyPI"></a>
    <a href="https://pepy.tech/project/nanobot-ai"><img src="https://static.pepy.tech/badge/nanobot-ai" alt="Downloads"></a>
    <img src="https://img.shields.io/badge/python-≥3.11-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  </p>
</div>

🐈 **nanobot** 是一个超轻量级的个人AI助手，本项目基于 [HKUDS/nanobot](https://github.com/HKUDS/nanobot) 进行了安全优化和功能增强。

## 🚀 优化简介

本项目在原nanobot（版本：nanobot-ai 0.1.4.post5）基础上通过TRAE(https://www.trae.cn/)进行信息安全性分析，并基于其生成信息安全分析报告，进行了以下关键优化：

### 🔒 安全增强
- **日志脱敏功能**：自动过滤日志中的敏感信息（API密钥、邮箱、手机号、IP地址等）
- **会话加密**：使用AES-256-GCM算法加密用户聊天记录
- **传输加密**：通道间消息传输的端到端加密
- **文件权限控制**：自动设置敏感文件的安全权限
- **强制中止服务**：支持通过对话安全关闭服务

### 🛡️ 安全功能详情
- ✅ 支持多种敏感信息类型的自动识别和脱敏
- ✅ 支持自定义脱敏规则
- ✅ AES-256-GCM强加密算法保护会话数据
- ✅ 跨平台文件权限控制（Windows/Unix）
- ✅ 完整的密钥管理和备份机制

## 安全分析报告
## 🔍 项目信息安全分析报告
经过详细的代码审查，我确认了您的观察： nanobot项目目前确实以明文方式传输和存储大部分敏感信息 。以下是详细分析和改进方案：

## 📊 当前安全状况分析
### ✅ 现有安全机制
1. 网络层安全
   
   - 使用HTTPS协议进行外部API通信（LLM、WebSearch、WebFetch）
   - SSRF防护机制：阻止访问内网地址（ network.py ）
   - URL验证：仅允许http/https协议
2. 特定通道加密
   
   - Matrix通道支持端到端加密（E2EE）
   - 飞书通道支持encryptKey配置
### ⚠️ 安全风险点
|风险类别 |具体问题 |影响范围 |
|--|--|--|
|明文传输|用户消息、LLM响应、Web搜索结果全部明文传输 |所有通信通道 |
|明文存储|会话历史以JSONL格式明文存储在磁盘|session/manager.py |
|内存泄露|敏感数据在内存中以明文形式存在|AgentLoop、MessageBus|
|日志泄露|日志可能包含敏感信息|loguru日志系统|
|无访问控制|会话文件无加密保护 |文件系统|


## 🛡️ 改进方案
## 📋 实施建议
### 优先级排序
|风险等级 |改进项目 |预计工作量 |安全收益 |
|--|--|--|--| 
|P0| 会话数据加密 | 2-3天 | 🔴 高 |
|P0| 日志脱敏 | 1天 | 🔴 高 |
|P1| 传输层加密 | 3-4天 | 🟡 中 |
|P1| 文件权限控制 | 1-2天 | 🟡 中 |
|P2| 配置增强 | 1天 | 🟢 低 |

### 实施步骤
1. 第一阶段（P0）
   
   - 实施会话数据加密
   - 添加日志脱敏功能
   - 更新配置schema
2. 第二阶段（P1）
   
   - 实施传输层加密
   - 添加文件权限控制
   - 创建密钥管理脚本
3. 第三阶段（P2）
   
   - 完善配置选项
   - 添加安全审计日志
   - 编写安全文档
### 兼容性考虑
- 向后兼容 ：加密功能可选，默认关闭，不影响现有部署
- 迁移路径 ：提供工具迁移现有明文会话到加密格式
- 性能影响 ：加密/解密操作会增加约5-10%的处理时间
### 🔑 密钥管理最佳实践
1. 密钥生成 ：使用加密安全的随机数生成器
2. 密钥存储 ：
   - 优先使用环境变量
   - 避免硬编码在配置文件中
   - 使用系统密钥链（Windows Credential Manager）
3. 密钥轮换 ：定期更换加密密钥
4. 密钥备份 ：安全备份密钥，防止数据丢失
### 📝 总结
nanobot项目目前确实存在明文传输和存储敏感信息的安全风险。我提出的改进方案包括：
1. 会话数据加密 ：使用AES-256-GCM加密存储的会话历史
2. 传输层加密 ：为通道通信添加可选的端到端加密
3. 日志脱敏 ：自动过滤日志中的敏感信息
4. 配置增强 ：添加安全配置选项
5. 密钥管理 ：提供安全的密钥生成和管理工具
这些改进可以显著提升项目的安全性，同时保持向后兼容性。建议优先实施P0级别的改进（会话加密和日志脱敏），以获得最大的安全收益。

## 📋 文档链接
- [原始项目文档](org_readme.md) - 原nanobot项目的完整文档
- [安全功能文档](security_readme.md) - 详细的安全优化说明和使用指南

## 📦 安装

```bash
# 从源码安装
git clone https://github.com/your-username/nanobot.git
cd nanobot
pip install -e .
```

## 🚀 快速开始

### 1. 初始化

```bash
nanobot onboard
```

### 2. 配置安全功能

编辑 `~/.nanobot/config.json`，启用安全功能：

```json
{
"security": {
    "enableLogSanitization": true,
    "enableSessionEncryption": true,
    "enableTransportEncryption": true,
    "secureFilePermissions": true
}
}
```

### 3. 生成加密密钥

```powershell
# 运行密钥生成脚本
.\secret\generate_keys.ps1
```

### 4. 启动服务

```bash
# 启动网关
nanobot gateway

# 运行代理
nanobot agent
```

## 📖 详细文档

- **[原始项目文档](org_readme.md)**：包含完整的安装、配置和使用指南
- **[安全功能文档](security_readme.md)**：详细的安全优化说明、配置方法和最佳实践

## 📄 许可证

本项目基于 MIT 许可证开源，详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢 [HKUDS/nanobot](https://github.com/HKUDS/nanobot) 团队提供的优秀基础项目！
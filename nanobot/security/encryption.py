"""
数据加密模块
提供AES-256-GCM加密/解密功能，用于会话数据加密和传输加密
"""

import os
import base64
import json
from typing import Optional, Union, Any
from pathlib import Path

from loguru import logger

# 尝试导入加密库
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    logger.warning("cryptography库未安装，加密功能不可用。运行: pip install cryptography")


class DataEncryption:
    """
    数据加密类，使用AES-256-GCM加密算法

    特性：
    - 使用AES-256-GCM提供认证加密
    - 使用PBKDF2进行密钥派生
    - 支持随机nonce生成
    """

    # 固定盐值（实际应用中可以考虑随机生成并存储）
    SALT = b"nanobot_encryption_salt_v1"

    def __init__(self, master_key: Optional[str] = None):
        """
        初始化加密器

        Args:
            master_key: 主密钥，如果为None则从环境变量NANOBOT_ENCRYPTION_KEY读取

        Raises:
            ValueError: 未提供密钥且环境变量未设置
            ImportError: cryptography库未安装
        """
        if not CRYPTOGRAPHY_AVAILABLE:
            raise ImportError(
                "cryptography库未安装，无法使用加密功能。"
                "请运行: pip install cryptography"
            )

        if master_key is None:
            master_key = os.environ.get("NANOBOT_ENCRYPTION_KEY")
            if not master_key:
                raise ValueError(
                    "未提供加密密钥，请设置NANOBOT_ENCRYPTION_KEY环境变量"
                )

        # 使用PBKDF2从主密钥派生32字节(256位)加密密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.SALT,
            iterations=100000,
        )
        self.key = kdf.derive(master_key.encode("utf-8"))
        self.aesgcm = AESGCM(self.key)
        self.enabled = True

    def encrypt(self, plaintext: str) -> str:
        """
        加密文本数据

        Args:
            plaintext: 明文文本

        Returns:
            Base64编码的密文，格式: base64(nonce + ciphertext + tag)

        Raises:
            ValueError: 加密失败
        """
        if not self.enabled:
            return plaintext

        try:
            # 生成随机nonce (GCM模式推荐12字节)
            nonce = os.urandom(12)

            # 加密数据
            ciphertext = self.aesgcm.encrypt(
                nonce, plaintext.encode("utf-8"), None
            )

            # 组合nonce和密文，然后Base64编码
            combined = nonce + ciphertext
            return base64.b64encode(combined).decode("ascii")

        except Exception as e:
            raise ValueError(f"加密失败: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        解密文本数据

        Args:
            ciphertext: Base64编码的密文

        Returns:
            明文文本

        Raises:
            ValueError: 解密失败（包括认证失败）
        """
        if not self.enabled:
            return ciphertext

        try:
            # Base64解码
            combined = base64.b64decode(ciphertext.encode("ascii"))

            # 分离nonce和密文
            nonce = combined[:12]
            ciphertext = combined[12:]

            # 解密
            plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")

        except Exception as e:
            raise ValueError(f"解密失败: {e}")

    def encrypt_dict(self, data: dict) -> str:
        """
        加密字典数据

        Args:
            data: 要加密的字典

        Returns:
            Base64编码的加密JSON字符串
        """
        json_str = json.dumps(data, ensure_ascii=False)
        return self.encrypt(json_str)

    def decrypt_dict(self, ciphertext: str) -> dict:
        """
        解密字典数据

        Args:
            ciphertext: Base64编码的密文

        Returns:
            解密后的字典
        """
        json_str = self.decrypt(ciphertext)
        return json.loads(json_str)


class TransportEncryption:
    """
    传输层加密管理器
    为通道消息提供可选的端到端加密
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化传输加密

        Args:
            encryption_key: 加密密钥，如果为None则从环境变量读取
        """
        try:
            self.encryption = DataEncryption(encryption_key)
            self.enabled = True
        except (ValueError, ImportError) as e:
            logger.warning(f"传输加密初始化失败: {e}")
            self.enabled = False
            self.encryption = None

    def encrypt_message(
        self, content: str, metadata: Optional[dict[str, Any]] = None
    ) -> tuple[str, dict[str, Any]]:
        """
        加密消息内容

        Args:
            content: 消息内容
            metadata: 元数据

        Returns:
            (加密后的内容, 更新后的元数据)
        """
        if not self.enabled:
            return content, metadata or {}

        try:
            encrypted_content = self.encryption.encrypt(content)
            updated_metadata = (metadata or {}).copy()
            updated_metadata["_encrypted"] = True
            updated_metadata["_encryption_version"] = "1.0"
            updated_metadata["_encryption_algo"] = "AES-256-GCM"
            return encrypted_content, updated_metadata
        except Exception as e:
            logger.error(f"消息加密失败: {e}")
            return content, metadata or {}

    def decrypt_message(
        self, content: str, metadata: Optional[dict[str, Any]] = None
    ) -> str:
        """
        解密消息内容

        Args:
            content: 消息内容
            metadata: 元数据

        Returns:
            解密后的内容
        """
        if not self.enabled:
            return content

        if metadata and metadata.get("_encrypted", False):
            try:
                return self.encryption.decrypt(content)
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                return content

        return content


class SessionEncryption:
    """
    会话数据加密管理器
    专门用于加密会话历史记录
    """

    # 需要加密的角色
    ENCRYPTED_ROLES = {"user", "assistant"}

    def __init__(self, encryption_key: Optional[str] = None):
        """
        初始化会话加密

        Args:
            encryption_key: 加密密钥
        """
        try:
            self.encryption = DataEncryption(encryption_key)
            self.enabled = True
        except (ValueError, ImportError) as e:
            logger.warning(f"会话加密初始化失败: {e}")
            self.enabled = False
            self.encryption = None

    def should_encrypt_message(self, msg: dict[str, Any]) -> bool:
        """
        判断是否应该加密消息

        Args:
            msg: 消息字典

        Returns:
            是否加密
        """
        if not self.enabled:
            return False

        role = msg.get("role", "")
        return role in self.ENCRYPTED_ROLES

    def encrypt_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """
        加密单个消息

        Args:
            msg: 原始消息字典

        Returns:
            加密后的消息字典
        """
        if not self.should_encrypt_message(msg):
            return msg

        try:
            msg_copy = msg.copy()
            content = msg_copy.get("content", "")
            if content:
                msg_copy["content"] = self.encryption.encrypt(content)
                msg_copy["_encrypted"] = True
                msg_copy["_encryption_version"] = "1.0"
            return msg_copy
        except Exception as e:
            logger.error(f"消息加密失败: {e}")
            return msg

    def decrypt_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """
        解密单个消息

        Args:
            msg: 可能加密的消息字典

        Returns:
            解密后的消息字典
        """
        if not self.enabled:
            return msg

        if msg.get("_encrypted", False):
            try:
                msg_copy = msg.copy()
                encrypted_content = msg_copy.get("content", "")
                if encrypted_content:
                    msg_copy["content"] = self.encryption.decrypt(encrypted_content)
                    del msg_copy["_encrypted"]
                    del msg_copy["_encryption_version"]
                return msg_copy
            except Exception as e:
                logger.error(f"消息解密失败: {e}")
                return msg

        return msg


def generate_encryption_key(length: int = 32) -> str:
    """
    生成安全的加密密钥

    Args:
        length: 密钥长度（字符数）

    Returns:
        随机生成的密钥字符串
    """
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def setup_encryption_from_config(config: Any) -> tuple[Optional[SessionEncryption], Optional[TransportEncryption]]:
    """
    根据配置设置加密

    Args:
        config: 配置对象

    Returns:
        (会话加密实例, 传输加密实例)
    """
    session_encryption = None
    transport_encryption = None

    # 获取安全配置
    security_config = getattr(config, "security", None)
    if not security_config:
        return None, None

    # 会话加密
    if getattr(security_config, "enable_session_encryption", False):
        try:
            key = getattr(security_config, "encryption_key", None)
            session_encryption = SessionEncryption(key)
            logger.info("会话加密已启用")
        except Exception as e:
            logger.error(f"会话加密初始化失败: {e}")

    # 传输加密
    if getattr(security_config, "enable_transport_encryption", False):
        try:
            key = getattr(security_config, "transport_key", None)
            transport_encryption = TransportEncryption(key)
            logger.info("传输加密已启用")
        except Exception as e:
            logger.error(f"传输加密初始化失败: {e}")

    return session_encryption, transport_encryption

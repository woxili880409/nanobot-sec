"""
安全模块测试 - 加密和日志脱敏功能
"""

import os
import sys
import json
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from nanobot.security.encryption import (
    DataEncryption,
    SessionEncryption,
    TransportEncryption,
    generate_encryption_key,
)
from nanobot.security.logging import LogSanitizer, setup_secure_logging


class TestDataEncryption:
    """测试数据加密功能"""

    def test_encryption_decryption(self):
        """测试基本的加密和解密"""
        key = "test_key_12345678901234567890"
        encryption = DataEncryption(key)

        plaintext = "Hello, World! 这是一段测试文本。"
        ciphertext = encryption.encrypt(plaintext)

        # 验证密文不同于明文
        assert ciphertext != plaintext

        # 验证解密正确
        decrypted = encryption.decrypt(ciphertext)
        assert decrypted == plaintext

    def test_encrypt_dict(self):
        """测试字典加密"""
        key = "test_key_12345678901234567890"
        encryption = DataEncryption(key)

        data = {"role": "user", "content": "Hello", "timestamp": "2024-01-01"}
        ciphertext = encryption.encrypt_dict(data)

        # 验证解密正确
        decrypted = encryption.decrypt_dict(ciphertext)
        assert decrypted == data

    def test_different_keys_produce_different_ciphertexts(self):
        """测试不同密钥产生不同密文"""
        key1 = "test_key_12345678901234567890"
        key2 = "different_key_1234567890123456"

        encryption1 = DataEncryption(key1)
        encryption2 = DataEncryption(key2)

        plaintext = "Test message"
        ciphertext1 = encryption1.encrypt(plaintext)
        ciphertext2 = encryption2.encrypt(plaintext)

        assert ciphertext1 != ciphertext2

    def test_tampered_ciphertext_fails(self):
        """测试篡改的密文解密失败"""
        key = "test_key_12345678901234567890"
        encryption = DataEncryption(key)

        plaintext = "Test message"
        ciphertext = encryption.encrypt(plaintext)

        # 篡改密文
        tampered = ciphertext[:-5] + "XXXXX"

        # 解密应该失败
        with pytest.raises(ValueError):
            encryption.decrypt(tampered)


class TestSessionEncryption:
    """测试会话加密功能"""

    def test_should_encrypt_user_message(self):
        """测试用户消息应该被加密"""
        key = "test_key_12345678901234567890"
        encryption = SessionEncryption(key)

        user_msg = {"role": "user", "content": "Hello"}
        assert encryption.should_encrypt_message(user_msg) is True

    def test_should_encrypt_assistant_message(self):
        """测试助手消息应该被加密"""
        key = "test_key_12345678901234567890"
        encryption = SessionEncryption(key)

        assistant_msg = {"role": "assistant", "content": "Hi there"}
        assert encryption.should_encrypt_message(assistant_msg) is True

    def test_should_not_encrypt_system_message(self):
        """测试系统消息不应该被加密"""
        key = "test_key_12345678901234567890"
        encryption = SessionEncryption(key)

        system_msg = {"role": "system", "content": "You are a bot"}
        assert encryption.should_encrypt_message(system_msg) is False

    def test_message_encryption_roundtrip(self):
        """测试消息加密解密完整流程"""
        key = "test_key_12345678901234567890"
        encryption = SessionEncryption(key)

        original_msg = {"role": "user", "content": "Secret message", "timestamp": "2024-01-01"}

        # 加密
        encrypted_msg = encryption.encrypt_message(original_msg)
        assert encrypted_msg.get("_encrypted") is True
        assert encrypted_msg["content"] != original_msg["content"]

        # 解密
        decrypted_msg = encryption.decrypt_message(encrypted_msg)
        assert decrypted_msg["content"] == original_msg["content"]
        assert "_encrypted" not in decrypted_msg


class TestLogSanitizer:
    """测试日志脱敏功能"""

    def test_sanitize_api_key(self):
        """测试API密钥脱敏"""
        message = "api_key=sk-1234567890abcdef"
        sanitized = LogSanitizer.sanitize(message)
        assert "***REDACTED***" in sanitized
        assert "sk-1234567890abcdef" not in sanitized

    def test_sanitize_email(self):
        """测试邮箱地址脱敏"""
        message = "Contact me at user@example.com please"
        sanitized = LogSanitizer.sanitize(message)
        assert "***@***.***" in sanitized
        assert "user@example.com" not in sanitized

    def test_sanitize_phone(self):
        """测试电话号码脱敏"""
        message = "Call me at 13812345678"
        sanitized = LogSanitizer.sanitize(message)
        assert "***-****-****" in sanitized
        assert "13812345678" not in sanitized

    def test_sanitize_ip_address(self):
        """测试IP地址脱敏"""
        message = "Server at 192.168.1.1 is down"
        sanitized = LogSanitizer.sanitize(message)
        assert "***.***.***.***" in sanitized
        assert "192.168.1.1" not in sanitized

    def test_sanitize_url_params(self):
        """测试URL参数脱敏"""
        message = "https://api.example.com?api_key=secret123&user=john"
        sanitized = LogSanitizer.sanitize(message)
        assert "***REDACTED***" in sanitized
        assert "secret123" not in sanitized

    def test_sanitize_telegram_token(self):
        """测试Telegram Bot Token脱敏"""
        # 独立测试Telegram Token格式（不包含token=前缀）
        # Telegram Bot Token格式: <数字>:<字母数字混合，至少35字符>
        message = "bot token is 123456789:ABCdefGHIjklMNOpqrSTUvwxyz12345678901234567890 for my bot"
        sanitized = LogSanitizer.sanitize(message)
        assert "***BOT_TOKEN***" in sanitized
        assert "123456789:ABCdefGHIjklMNOpqrSTUvwxyz12345678901234567890" not in sanitized

    def test_no_false_positives(self):
        """测试不误伤正常文本"""
        message = "Hello world, this is a normal message"
        sanitized = LogSanitizer.sanitize(message)
        assert sanitized == message


class TestKeyGeneration:
    """测试密钥生成功能"""

    def test_generate_key_length(self):
        """测试生成密钥的长度"""
        key = generate_encryption_key(length=32)
        assert len(key) == 32

    def test_generate_key_randomness(self):
        """测试生成密钥的随机性"""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        assert key1 != key2


class TestIntegration:
    """集成测试"""

    def test_session_manager_with_encryption(self, tmp_path):
        """测试带加密的会话管理器"""
        from nanobot.session.manager import SessionManager, Session

        key = "test_key_12345678901234567890"
        encryption = SessionEncryption(key)
        manager = SessionManager(tmp_path, encryption=encryption)

        # 创建会话
        session = Session(key="test:session1")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there")

        # 保存
        manager.save(session)

        # 重新加载
        loaded_session = manager._load("test:session1")

        assert loaded_session is not None
        assert len(loaded_session.messages) == 2
        assert loaded_session.messages[0]["content"] == "Hello"
        assert loaded_session.messages[1]["content"] == "Hi there"

        # 验证文件内容已加密
        session_file = tmp_path / "sessions" / "test_session1.jsonl"
        with open(session_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 第一行是元数据（明文）
        metadata = json.loads(lines[0])
        assert metadata.get("encrypted") is True

        # 后续行是加密的消息
        for line in lines[1:]:
            msg = json.loads(line)
            if msg.get("_encrypted"):
                # 加密的消息内容应该是base64格式
                assert msg["content"] != "Hello"  # 不是明文
                assert msg["content"] != "Hi there"  # 不是明文


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])

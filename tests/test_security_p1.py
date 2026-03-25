"""
测试P1阶段安全功能：传输加密和文件权限控制
"""

import os
import stat
import tempfile
from pathlib import Path
import pytest

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.security.encryption import TransportEncryption
from nanobot.security.file_permissions import FilePermissionManager, get_file_permissions


class TestTransportEncryption:
    """测试传输加密功能"""
    
    def setup_method(self):
        """设置测试环境"""
        self.encryption_key = "test_encryption_key_for_testing_only"
        self.transport_encryption = TransportEncryption(self.encryption_key)
        
    def test_transport_encryption_init(self):
        """测试传输加密初始化"""
        assert self.transport_encryption.enabled == True
        assert self.transport_encryption.encryption is not None
        
    def test_encrypt_decrypt_message(self):
        """测试消息加密解密"""
        original_content = "这是一条测试消息"
        metadata = {"key": "value"}
        
        # 加密消息
        encrypted_content, updated_metadata = self.transport_encryption.encrypt_message(
            original_content, metadata
        )
        
        # 验证加密结果
        assert encrypted_content != original_content
        assert updated_metadata.get("_encrypted") == True
        assert updated_metadata.get("_encryption_version") == "1.0"
        assert updated_metadata.get("_encryption_algo") == "AES-256-GCM"
        
        # 解密消息
        decrypted_content = self.transport_encryption.decrypt_message(
            encrypted_content, updated_metadata
        )
        
        # 验证解密结果
        assert decrypted_content == original_content
        
    def test_message_bus_with_encryption(self):
        """测试消息总线的加密功能"""
        # 创建带加密的消息总线
        bus = MessageBus(transport_encryption=self.transport_encryption)
        
        # 创建测试消息
        inbound_msg = InboundMessage(
            channel="test_channel",
            sender_id="test_user",
            chat_id="test_chat",
            content="测试消息内容",
            metadata={"test": "metadata"}
        )
        
        outbound_msg = OutboundMessage(
            channel="test_channel",
            chat_id="test_chat",
            content="回复消息内容",
            metadata={"reply": "metadata"}
        )
        
        # 测试入站消息加密
        import asyncio
        asyncio.run(bus.publish_inbound(inbound_msg))
        
        # 消费消息并验证解密
        consumed_msg = asyncio.run(bus.consume_inbound())
        assert consumed_msg.content == "测试消息内容"
        assert consumed_msg.metadata.get("_encrypted") == True
        
        # 测试出站消息加密
        asyncio.run(bus.publish_outbound(outbound_msg))
        
        # 消费消息并验证解密
        consumed_outbound = asyncio.run(bus.consume_outbound())
        assert consumed_outbound.content == "回复消息内容"
        assert consumed_outbound.metadata.get("_encrypted") == True
        
    def test_message_bus_without_encryption(self):
        """测试消息总线不使用加密"""
        # 创建不带加密的消息总线
        bus = MessageBus()
        
        inbound_msg = InboundMessage(
            channel="test_channel",
            sender_id="test_user",
            chat_id="test_chat",
            content="未加密消息"
        )
        
        import asyncio
        asyncio.run(bus.publish_inbound(inbound_msg))
        
        consumed_msg = asyncio.run(bus.consume_inbound())
        assert consumed_msg.content == "未加密消息"
        assert "_encrypted" not in consumed_msg.metadata


class TestFilePermissions:
    """测试文件权限控制功能"""
    
    def setup_method(self):
        """设置测试环境"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = FilePermissionManager(enabled=True)
        
    def teardown_method(self):
        """清理测试环境"""
        import shutil
        shutil.rmtree(self.temp_dir)
        
    def test_set_secure_permissions(self):
        """测试设置文件安全权限"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test content")
        
        # 设置安全权限
        result = self.manager.set_secure_permissions(test_file)
        
        # 验证权限设置成功
        assert result == True
        
        # 验证文件权限为600（在Windows上跳过权限检查）
        if os.name != 'nt':  # 非Windows系统
            file_stat = test_file.stat()
            permissions = stat.S_IMODE(file_stat.st_mode)
            assert permissions == 0o600
        
    def test_set_directory_permissions(self):
        """测试设置目录安全权限"""
        # 创建测试目录
        test_dir = Path(self.temp_dir) / "test_dir"
        test_dir.mkdir()
        
        # 设置安全权限
        result = self.manager.set_secure_permissions(test_dir)
        
        # 验证权限设置成功
        assert result == True
        
        # 验证目录权限为700（在Windows上跳过权限检查）
        if os.name != 'nt':  # 非Windows系统
            dir_stat = test_dir.stat()
            permissions = stat.S_IMODE(dir_stat.st_mode)
            assert permissions == 0o700
        
    def test_is_sensitive_file(self):
        """测试判断敏感文件"""
        # 创建各种类型的文件
        test_files = [
            ("config.json", True),
            ("secret.key", True),
            ("data.txt", True),
            ("image.jpg", False),
            ("script.py", False),
        ]
        
        for filename, should_be_sensitive in test_files:
            file_path = Path(self.temp_dir) / filename
            file_path.write_text("test")
            
            is_sensitive = self.manager._is_sensitive_file(file_path)
            assert is_sensitive == should_be_sensitive
            
    def test_scan_directory(self):
        """测试扫描目录中的敏感文件"""
        # 创建敏感和非敏感文件
        sensitive_files = [
            "config.json",
            "secret.key",
            "credentials.txt",
        ]
        
        non_sensitive_files = [
            "image.jpg",
            "script.py",
        ]
        
        for filename in sensitive_files + non_sensitive_files:
            file_path = Path(self.temp_dir) / filename
            file_path.write_text("test")
            
        # 扫描目录
        found_files = self.manager.scan_directory(Path(self.temp_dir))
        
        # 验证只找到敏感文件
        found_filenames = [f.name for f in found_files]
        for sensitive_file in sensitive_files:
            assert sensitive_file in found_filenames
            
        for non_sensitive_file in non_sensitive_files:
            assert non_sensitive_file not in found_filenames
            
    def test_verify_permissions(self):
        """测试验证文件权限"""
        # 创建文件并设置权限
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test")
        
        # 设置安全权限
        self.manager.set_secure_permissions(test_file)
        
        # 验证权限安全
        assert self.manager.verify_permissions(test_file) == True
        
        # 修改权限为不安全的
        test_file.chmod(0o644)

        # 验证权限不安全（在Windows上跳过这个测试）
        if os.name != 'nt':  # 非Windows系统
            assert self.manager.verify_permissions(test_file) == False
        
    def test_get_file_permissions(self):
        """测试获取文件权限字符串"""
        test_file = Path(self.temp_dir) / "test.txt"
        test_file.write_text("test")
        
        # 设置权限
        test_file.chmod(0o600)
        
        # 获取权限字符串
        perm_str = get_file_permissions(test_file)
        
        if os.name == 'nt':  # Windows系统
            assert perm_str == "-rw-rw-rw-"
        else:  # Unix/Linux系统
            assert perm_str == "-rw-------"
            
            # 修改权限
            test_file.chmod(0o755)
            perm_str = get_file_permissions(test_file)
            assert perm_str == "-rwxr-xr-x"
        
    def test_protect_workspace(self):
        """测试保护工作区"""
        # 创建测试文件结构
        workspace = Path(self.temp_dir)
        
        # 创建敏感文件
        (workspace / "config.json").write_text("{}")
        (workspace / "secret.key").write_text("key")
        
        # 创建目录
        subdir = workspace / "subdir"
        subdir.mkdir()
        (subdir / "data.txt").write_text("data")
        
        # 保护工作区
        protected_count = self.manager.protect_workspace(workspace)
        
        # 验证所有敏感文件都被保护
        assert protected_count >= 3
        
        # 验证权限设置正确
        assert self.manager.verify_permissions(workspace / "config.json") == True
        assert self.manager.verify_permissions(workspace / "secret.key") == True
        assert self.manager.verify_permissions(subdir / "data.txt") == True
        
    def test_check_all_permissions(self):
        """测试检查所有权限"""
        # 创建测试文件
        test_file = Path(self.temp_dir) / "config.json"
        test_file.write_text("{}")
        
        # 设置安全权限
        self.manager.set_secure_permissions(test_file)
        
        # 检查权限
        insecure_files = self.manager.check_all_permissions(Path(self.temp_dir))
        assert len(insecure_files) == 0
        
        # 修改为不安全权限
        test_file.chmod(0o644)

        # 检查权限（在Windows上跳过这个测试）
        if os.name != 'nt':  # 非Windows系统
            insecure_files = self.manager.check_all_permissions(Path(self.temp_dir))
            assert len(insecure_files) == 1
            assert insecure_files[0] == test_file


if __name__ == "__main__":
    pytest.main([__file__])

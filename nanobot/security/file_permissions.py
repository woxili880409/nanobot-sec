"""
文件权限控制模块
提供敏感文件的权限管理功能，保护敏感数据安全
"""

import os
import stat
from pathlib import Path
from typing import List, Optional

from loguru import logger


class FilePermissionManager:
    """
    文件权限管理器
    用于设置和维护敏感文件的安全权限
    """
    
    # 需要保护的文件模式
    PROTECTED_PATTERNS = [
        "*.json",
        "*.key",
        "*.pem",
        "*.env",
        "*.txt",
        "*.log",
    ]
    
    # 需要保护的目录
    PROTECTED_DIRECTORIES = [
        ".nanobot",
        "secret",
        "sessions",
        "workspace",
    ]
    
    def __init__(self, enabled: bool = True):
        """
        初始化文件权限管理器
        
        Args:
            enabled: 是否启用权限控制
        """
        self.enabled = enabled
        
    def set_secure_permissions(self, file_path: Path) -> bool:
        """
        设置文件的安全权限
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功设置权限
        """
        if not self.enabled:
            return False
            
        if not file_path.exists():
            return False
            
        try:
            if os.name == 'nt':  # Windows系统
                # Windows不支持Unix风格的权限位，使用其他方式
                logger.debug(f"Windows系统：跳过文件权限设置: {file_path}")
                return True
            else:  # Unix/Linux系统
                if file_path.is_file():
                    # 设置文件权限为600（只有所有者可读写）
                    file_path.chmod(0o600)
                    logger.debug(f"已设置文件安全权限: {file_path}")
                elif file_path.is_dir():
                    # 设置目录权限为700（只有所有者可读写执行）
                    file_path.chmod(0o700)
                    logger.debug(f"已设置目录安全权限: {file_path}")
                return True
        except Exception as e:
            logger.warning(f"设置文件权限失败: {file_path}, 错误: {e}")
            return False
            
    def scan_directory(self, directory: Path, recursive: bool = True) -> List[Path]:
        """
        扫描目录中的敏感文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归扫描
            
        Returns:
            敏感文件列表
        """
        sensitive_files = []
        
        if not directory.exists() or not directory.is_dir():
            return sensitive_files
            
        try:
            if recursive:
                files = list(directory.rglob("*"))
            else:
                files = list(directory.iterdir())
                
            for file in files:
                if self._is_sensitive_file(file):
                    sensitive_files.append(file)
                    
        except Exception as e:
            logger.error(f"扫描目录失败: {directory}, 错误: {e}")
            
        return sensitive_files
        
    def _is_sensitive_file(self, file_path: Path) -> bool:
        """
        判断文件是否为敏感文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否为敏感文件
        """
        # 检查文件扩展名
        for pattern in self.PROTECTED_PATTERNS:
            if file_path.match(pattern):
                return True
                
        # 检查目录路径
        path_parts = file_path.parts
        for dir_name in self.PROTECTED_DIRECTORIES:
            if dir_name in path_parts:
                return True
                
        # 检查文件名是否包含敏感词
        sensitive_keywords = ["config", "secret", "key", "token", "password", "credential"]
        file_name_lower = file_path.name.lower()
        for keyword in sensitive_keywords:
            if keyword in file_name_lower:
                return True
                
        return False
        
    def protect_workspace(self, workspace_path: Path) -> int:
        """
        保护工作区中的所有敏感文件
        
        Args:
            workspace_path: 工作区路径
            
        Returns:
            成功设置权限的文件数量
        """
        if not self.enabled:
            return 0
            
        logger.info(f"开始保护工作区敏感文件: {workspace_path}")
        
        sensitive_files = self.scan_directory(workspace_path)
        protected_count = 0
        
        for file_path in sensitive_files:
            if self.set_secure_permissions(file_path):
                protected_count += 1
                
        logger.info(f"已保护 {protected_count} 个敏感文件")
        return protected_count
        
    def verify_permissions(self, file_path: Path) -> bool:
        """
        验证文件权限是否安全
        
        Args:
            file_path: 文件路径
            
        Returns:
            权限是否安全
        """
        if not file_path.exists():
            return False
            
        try:
            if os.name == 'nt':  # Windows系统
                # Windows不支持Unix风格的权限检查，默认认为安全
                return True
                
            file_stat = file_path.stat()
            permissions = stat.S_IMODE(file_stat.st_mode)
            
            if file_path.is_file():
                # 文件权限应该是600或更严格
                return permissions <= 0o600
            elif file_path.is_dir():
                # 目录权限应该是700或更严格
                return permissions <= 0o700
                
        except Exception as e:
            logger.error(f"验证文件权限失败: {file_path}, 错误: {e}")
            
        return False
        
    def check_all_permissions(self, directory: Path) -> List[Path]:
        """
        检查目录中所有敏感文件的权限
        
        Args:
            directory: 目录路径
            
        Returns:
            权限不安全的文件列表
        """
        insecure_files = []
        sensitive_files = self.scan_directory(directory)
        
        for file_path in sensitive_files:
            if not self.verify_permissions(file_path):
                insecure_files.append(file_path)
                
        return insecure_files


def setup_file_permissions(workspace_path: Path, enabled: bool = True) -> FilePermissionManager:
    """
    设置文件权限控制
    
    Args:
        workspace_path: 工作区路径
        enabled: 是否启用权限控制
        
    Returns:
        文件权限管理器实例
    """
    manager = FilePermissionManager(enabled=enabled)
    
    if enabled:
        manager.protect_workspace(workspace_path)
        
    return manager


def get_file_permissions(file_path: Path) -> str:
    """
    获取文件的权限字符串（如-rw-------）
    
    Args:
        file_path: 文件路径
        
    Returns:
        权限字符串
    """
    try:
        if os.name == 'nt':  # Windows系统
            # Windows不支持Unix风格的权限位，返回默认权限
            if file_path.is_dir():
                return 'drwxrwxrwx'
            else:
                return '-rw-rw-rw-'
                
        file_stat = file_path.stat()
        permissions = stat.S_IMODE(file_stat.st_mode)
        
        # 构建权限字符串
        perm_str = []
        
        # 文件类型
        if file_path.is_dir():
            perm_str.append('d')
        else:
            perm_str.append('-')
            
        # 所有者权限
        perm_str.append('r' if permissions & stat.S_IRUSR else '-')
        perm_str.append('w' if permissions & stat.S_IWUSR else '-')
        perm_str.append('x' if permissions & stat.S_IXUSR else '-')
        
        # 组权限
        perm_str.append('r' if permissions & stat.S_IRGRP else '-')
        perm_str.append('w' if permissions & stat.S_IWGRP else '-')
        perm_str.append('x' if permissions & stat.S_IXGRP else '-')
        
        # 其他用户权限
        perm_str.append('r' if permissions & stat.S_IROTH else '-')
        perm_str.append('w' if permissions & stat.S_IWOTH else '-')
        perm_str.append('x' if permissions & stat.S_IXOTH else '-')
        
        return ''.join(perm_str)
        
    except Exception:
        return '---------'

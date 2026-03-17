"""
日志安全模块
提供日志脱敏功能，防止敏感信息泄露
"""

import re
import sys
from typing import Callable, Optional
from loguru import logger


class LogSanitizer:
    """
    日志脱敏器
    自动过滤敏感信息，如API密钥、邮箱、电话等
    """

    # 敏感信息模式定义
    # 注意：顺序很重要，更具体的模式应该放在前面
    PATTERNS = [
        # Telegram Bot Token (更具体的模式，优先匹配)
        (
            r'\b\d{9,}:[a-zA-Z0-9_-]{35,}\b',
            r'***BOT_TOKEN***',
        ),
        # API密钥、Token、Secret等
        (
            r'(api[_-]?key|apikey|token|secret|password|passwd|pwd|auth|credential)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{8,})["\']?',
            r'\1=***REDACTED***',
        ),
        # 邮箱地址
        (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            r'***@***.***',
        ),
        # 电话号码（中国大陆、国际格式）
        (
            r'\b(\+?86[-\s]?)?1[3-9]\d{9}\b|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            r'***-****-****',
        ),
        # IP地址
        (
            r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b',
            r'***.***.***.***',
        ),
        # URL中的敏感参数
        (
            r'([?&](api[_-]?key|apikey|token|secret|password|auth)=)[^&\s]+',
            r'\1***REDACTED***',
        ),
        # 飞书App Secret
        (
            r'(app[_-]?secret|appsecret)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9]+)["\']?',
            r'\1=***REDACTED***',
        ),
        # 身份证号（中国大陆）
        (
            r'\b\d{17}[\dXx]|\d{15}\b',
            r'***ID***',
        ),
        # 银行卡号（简单匹配）
        (
            r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',
            r'****-****-****-****',
        ),
    ]

    @classmethod
    def sanitize(cls, message: str) -> str:
        """
        脱敏日志消息

        Args:
            message: 原始日志消息

        Returns:
            脱敏后的消息
        """
        if not message or not isinstance(message, str):
            return message

        sanitized = message
        for pattern, replacement in cls.PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def create_filter(cls) -> Callable:
        """
        创建loguru过滤器函数

        Returns:
            过滤器函数，可直接用于loguru配置
        """

        def filter_func(record):
            # 脱敏消息内容
            if "message" in record:
                record["message"] = cls.sanitize(record["message"])
            # 脱敏异常信息
            if "exception" in record and record["exception"]:
                try:
                    record["exception"] = cls.sanitize(str(record["exception"]))
                except:
                    pass
            return True

        return filter_func


class SecureLogFormatter:
    """
    安全日志格式化器
    在格式化时进行脱敏处理
    """

    def __init__(self, format_string: Optional[str] = None):
        self.format_string = format_string or (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

    def format(self, record):
        """格式化并脱敏日志记录"""
        # 脱敏消息
        if "message" in record:
            record["message"] = LogSanitizer.sanitize(record["message"])
        return self.format_string.format(**record)


def setup_secure_logging(
    enable_sanitization: bool = True,
    level: str = "INFO",
    sink=sys.stderr,
):
    """
    配置安全日志

    Args:
        enable_sanitization: 是否启用脱敏，默认为True
        level: 日志级别
        sink: 日志输出目标
    """
    # 移除默认处理器
    logger.remove()

    # 基础格式
    fmt = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # 配置处理器
    if enable_sanitization:
        # 启用脱敏
        logger.add(
            sink,
            format=fmt,
            level=level,
            filter=LogSanitizer.create_filter(),
            colorize=True,
        )
        logger.info("日志脱敏功能已启用")
    else:
        # 不启用脱敏
        logger.add(
            sink,
            format=fmt,
            level=level,
            colorize=True,
        )
        logger.info("日志脱敏功能已禁用")


def patch_logger_for_sanitization():
    """
    为现有logger添加脱敏功能（用于运行时动态启用）
    """
    # 获取当前所有处理器
    handlers = logger._core.handlers.copy()

    # 为每个处理器添加过滤器
    for handler_id, handler in handlers.items():
        # 添加脱敏过滤器
        handler._filter = LogSanitizer.create_filter()

    logger.info("已为现有日志处理器添加脱敏功能")

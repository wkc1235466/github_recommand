"""日志配置模块 - 使用 Python 标准库 logging"""

import sys
import logging
from pathlib import Path


# 日志格式
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"
CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_dir: str = "logs", debug: bool = False):
    """配置日志系统

    Args:
        log_dir: 日志文件存储目录
        debug: 是否开启调试级别日志
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 获取根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # 清除现有处理器
    root_logger.handlers.clear()

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(logging.Formatter(CONSOLE_FORMAT, DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # 文件处理器 - 所有日志
    file_handler = logging.FileHandler(
        log_path / "app.log",
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(file_handler)

    # 文件处理器 - 仅错误日志
    error_handler = logging.FileHandler(
        log_path / "error.log",
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(error_handler)

    # 抑制第三方库的 DEBUG 日志
    third_party_loggers = [
        "sqlalchemy",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "sqlalchemy.orm",
        "httpcore",
        "httpx",
        "urllib3",
        "asyncio",
        "aiosqlite",
        "charset_normalizer",
        "PIL",
        "matplotlib",
        "numba",
        "http11",
        "anyio",
    ]
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

    root_logger.info("日志系统初始化完成")
    return root_logger


# 创建默认日志实例
log = logging.getLogger(__name__)
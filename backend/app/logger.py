"""日志配置模块 - 使用 loguru"""

import sys
from pathlib import Path
from loguru import logger

# 移除默认处理器
logger.remove()

# 日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 控制台简洁格式
CONSOLE_FORMAT = (
    "<green>{time:HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<level>{message}</level>"
)


def setup_logging(log_dir: str = "logs", debug: bool = False):
    """配置日志系统

    Args:
        log_dir: 日志文件存储目录
        debug: 是否开启调试级别日志
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 控制台处理器
    logger.add(
        sys.stdout,
        format=CONSOLE_FORMAT,
        level="DEBUG" if debug else "INFO",
        colorize=True,
    )

    # 文件处理器 - 所有日志
    logger.add(
        log_path / "app.log",
        format=LOG_FORMAT,
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip",
        encoding="utf-8",
    )

    # 文件处理器 - 仅错误日志
    logger.add(
        log_path / "error.log",
        format=LOG_FORMAT,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        encoding="utf-8",
    )

    logger.info("日志系统初始化完成")
    return logger


# 创建默认日志实例
log = logger
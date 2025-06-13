import logging
from logging.handlers import RotatingFileHandler


def setup_logger(log_file='app.log', log_level=logging.INFO):
    # 创建一个名为 'app' 的根logger（在整个项目中保持唯一）
    logger = logging.getLogger('app')
    logger.setLevel(log_level)

    # 避免重复添加处理器
    if not logger.handlers:
        # 创建文件处理器
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setLevel(log_level)

        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)

        # 定义日志格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s '
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # 添加处理器到logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


# 初始化日志配置
logger = setup_logger()

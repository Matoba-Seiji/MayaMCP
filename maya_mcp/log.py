#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""日志模块。"""

# Import built-in modules
import os
import logging
import threading
import logging.handlers
import tempfile
from datetime import datetime

__all__ = ["LogManager", "log_file"]

LOG_SIZE = 1024 * 1024 * 100
BACKUP_COUNT = 10
FORMAT_STR = ""


def _get_temp_log_file_path():
    temp_dir = tempfile.gettempdir()
    date_code = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(temp_dir, "maya_mcp_%s.log" % date_code).replace("\\", "/")


def _remove_handlers_from_logger(logger, handler_type):
    for handler in list(logger.handlers):
        if isinstance(handler, handler_type):
            logger.removeHandler(handler)


def _add_stream_handler(logger):
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter(FORMAT_STR)
    formatter.datefmt = '%H:%M:%S'
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)


def _create_logger(logger_name):
    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    return logger


def _add_rotating_file_handler(logger, log_file):
    _remove_handlers_from_logger(logger, logging.handlers.RotatingFileHandler)
    log_dir = os.path.dirname(log_file)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=LOG_SIZE, backupCount=BACKUP_COUNT)
    formatter = logging.Formatter(FORMAT_STR)
    formatter.datefmt = '%H:%M:%S'
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class Logger(object):
    def __init__(self, logger):
        self.logger = logger

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message, send_to_tm=True):
        self.logger.error(message)


class LogManager(object):
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not hasattr(cls, "_instance"):
                cls._instance = super(LogManager, cls).__new__(cls)
        return cls._instance

    @staticmethod
    def get_logger(logger_name, logger_path=None, log_file="", level=logging.DEBUG, force_write=True):
        """获取一个 logger 实例。

        Args:
            logger_name: log 名称。
            logger_path: 当前 log 所处文件路径。
            log_file: log 存放文件路径。
            level: log 等级。
            force_write: 是否强制写出到 temp 路径。
        """
        global FORMAT_STR
        if logger_path:
            FORMAT_STR = "%(asctime)s - %(name)-3s - {} - %(levelname)-5s \n\t%(message)s\n".format(
                logger_path.replace("\\", "/"))
        else:
            FORMAT_STR = "%(asctime)s - %(name)-3s - %(filename)s - %(levelname)-5s \n\t%(message)s\n"
        log_file = (log_file or "").replace("\\", "/")

        logger = _create_logger(logger_name)
        logger.setLevel(level)
        logger.propagate = False
        _add_stream_handler(logger)

        if not log_file and force_write:
            log_file = _get_temp_log_file_path()
        if log_file:
            _add_rotating_file_handler(logger, log_file)

        return Logger(logger)


log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../MayaMCPServer.log"))

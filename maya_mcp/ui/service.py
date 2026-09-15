#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Maya MCP 监听服务控制层。

封装监听器的启动/停止/重启/状态查询，供菜单复用。
为避免与其它工程的同名包 `maya_mcp` 冲突，本模块不依赖包导入，
仅通过文件路径定位 connector 目录并按模块名导入监听器。
"""

import os
import sys
import socket

LISTENER_MODULE = "maya_server_listener"
DEFAULT_PORT = 50011
DEFAULT_HOST = "127.0.0.1"


def connector_dir():
    """返回监听器所在的 connector 目录绝对路径。"""
    ui_dir = os.path.dirname(os.path.abspath(__file__))
    maya_mcp_dir = os.path.dirname(ui_dir)
    return os.path.join(maya_mcp_dir, "connector")


def _ensure_path():
    cd = connector_dir()
    if cd not in sys.path:
        sys.path.append(cd)


def get_listener(create=False):
    """获取监听器模块。

    Args:
        create: 为 True 时若未导入则导入（导入会触发监听器自动启动）。
    """
    if LISTENER_MODULE in sys.modules:
        return sys.modules[LISTENER_MODULE]
    if not create:
        return None
    _ensure_path()
    import maya_server_listener  # noqa: 导入即自动 start_mcp_server()
    return maya_server_listener


def port():
    """返回监听端口。"""
    mod = get_listener(create=False)
    return int(getattr(mod, "PORT", DEFAULT_PORT)) if mod else DEFAULT_PORT


def host():
    mod = get_listener(create=False)
    return str(getattr(mod, "HOST", DEFAULT_HOST)) if mod else DEFAULT_HOST


def is_port_open(h=None, p=None, timeout=0.3):
    """通过 socket 连接探测端口是否在监听（与进程无关）。"""
    h = h or host()
    p = p or port()
    try:
        with socket.create_connection((h, p), timeout=timeout):
            return True
    except OSError:
        return False


def is_running():
    """监听是否在运行：优先看监听器内部标志，其次探测端口。"""
    mod = get_listener(create=False)
    if mod is not None and bool(getattr(mod, "_server_running", False)):
        return True
    return is_port_open()


def start():
    """启动监听（幂等）。返回 (success, message)。"""
    try:
        mod = get_listener(create=True)
        if hasattr(mod, "start_mcp_server"):
            mod.start_mcp_server()
        return True, f"监听已启动: {host()}:{port()}"
    except Exception as e:
        return False, f"启动失败: {e}"


def stop():
    """停止监听。返回 (success, message)。"""
    mod = get_listener(create=False)
    if mod is None or not hasattr(mod, "stop_mcp_server"):
        return False, "监听器尚未加载，无需停止。"
    try:
        mod.stop_mcp_server()
        return True, "监听已停止。"
    except Exception as e:
        return False, f"停止失败: {e}"


def restart():
    """重启监听。返回 (success, message)。"""
    try:
        mod = get_listener(create=True)
        if hasattr(mod, "restart_mcp_server"):
            mod.restart_mcp_server()
        return True, f"监听已重启: {host()}:{port()}"
    except Exception as e:
        return False, f"重启失败: {e}"

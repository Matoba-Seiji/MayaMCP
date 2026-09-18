#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Control the Maya-side MCP listener from the Maya UI."""

import os
import socket
import sys


LISTENER_MODULE = "maya_server_listener"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 50011


def connector_dir():
    ui_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(ui_dir), "connector")


def _ensure_path():
    path = connector_dir()
    if path not in sys.path:
        sys.path.append(path)


def get_listener(create=False):
    if LISTENER_MODULE in sys.modules:
        return sys.modules[LISTENER_MODULE]
    if not create:
        return None

    _ensure_path()
    import maya_server_listener
    return maya_server_listener


def port():
    listener = get_listener(create=False)
    return int(getattr(listener, "PORT", DEFAULT_PORT)) if listener else DEFAULT_PORT


def host():
    listener = get_listener(create=False)
    return str(getattr(listener, "HOST", DEFAULT_HOST)) if listener else DEFAULT_HOST


def is_port_open(host_name=None, port_number=None, timeout=0.3):
    host_name = host_name or host()
    port_number = port_number or port()
    try:
        with socket.create_connection((host_name, port_number), timeout=timeout):
            return True
    except OSError:
        return False


def is_running():
    listener = get_listener(create=False)
    if listener is not None and bool(getattr(listener, "_server_running", False)):
        return True
    return is_port_open()


def start():
    try:
        listener = get_listener(create=True)
        listener.start_mcp_server()
        return True, f"监听已启动: {host()}:{port()}"
    except Exception as error:
        return False, f"启动失败: {error}"


def stop():
    listener = get_listener(create=False)
    if listener is None:
        return False, "监听器尚未加载，无需停止。"
    try:
        listener.stop_mcp_server()
        return True, "监听已停止。"
    except Exception as error:
        return False, f"停止失败: {error}"


def restart():
    try:
        listener = get_listener(create=True)
        listener.restart_mcp_server()
        return True, f"监听已重启: {host()}:{port()}"
    except Exception as error:
        return False, f"重启失败: {error}"

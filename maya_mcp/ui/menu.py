#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Register the MayaMCP menu in Maya's main window."""

import importlib.util
import os

import maya.cmds as cmds
import maya.mel as mel


MENU_NAME = "MayaMCPMenu"
MENU_LABEL = "Maya MCP"

# 每个 Maya 进程只监听一个端口；两个实例分别固定 50016 / 50017。
# 50012 / 50013 已分配给 3dsMaxMCP 的两个实例，50011 等端口常被其他软件占用。
INSTANCE_PORTS = (50016, 50017)


def _load_sibling(name):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("mayamcp_" + name, path)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载模块: " + path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _service():
    return _load_sibling("service")


def create_menu():
    """Create or rebuild the MayaMCP menu."""
    if cmds.about(batch=True):
        return
    delete_menu()

    main_window = mel.eval("$tmp = $gMainWindow;")
    if not main_window:
        return

    main_menu = cmds.menu(MENU_NAME, label=MENU_LABEL, parent=main_window, tearOff=True)
    cmds.menuItem(
        label="启动监听（实例1·%d）" % INSTANCE_PORTS[0],
        command=lambda *args: _start(INSTANCE_PORTS[0]),
    )
    cmds.menuItem(
        label="启动监听（实例2·%d）" % INSTANCE_PORTS[1],
        command=lambda *args: _start(INSTANCE_PORTS[1]),
    )
    cmds.menuItem(label="停止监听", command=lambda *args: _stop())
    cmds.menuItem(label="重启监听", command=lambda *args: _restart())
    cmds.menuItem(divider=True)
    cmds.menuItem(label="查看监听状态", command=lambda *args: _status())
    return main_menu


def delete_menu():
    if cmds.menu(MENU_NAME, query=True, exists=True):
        cmds.deleteUI(MENU_NAME)


def _start(port=None):
    _ok, message = _service().start(port)
    print("[MayaMCP]", message)


def _stop():
    _ok, message = _service().stop()
    print("[MayaMCP]", message)


def _restart():
    _ok, message = _service().restart()
    print("[MayaMCP]", message)


def _status():
    service = _service()
    state = "监听中" if service.is_running() else "未启动"
    cmds.confirmDialog(
        title="Maya MCP",
        message=f"监听地址: {service.host()}:{service.port()}\n状态: {state}",
        button=["OK"],
    )

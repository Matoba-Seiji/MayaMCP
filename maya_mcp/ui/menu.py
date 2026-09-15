#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""在 Maya 顶部菜单栏注册 "Maya MCP" 菜单。"""

import os
import importlib.util

import maya.cmds as cmds
import maya.mel as mel

MENU_NAME = "MayaMCPMenu"
MENU_LABEL = "Maya MCP"


def _load_sibling(name):
    """按文件路径加载同目录模块，避免包名冲突。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("mayamcp_" + name, path)
    if spec is None or spec.loader is None:
        raise ImportError("无法加载模块: " + path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _service():
    return _load_sibling("service")


def create_menu():
    """创建/重建顶栏菜单。"""
    if cmds.about(batch=True):
        return
    delete_menu()

    gMainWindow = mel.eval("$tmp = $gMainWindow;")
    if not gMainWindow:
        return

    main_menu = cmds.menu(MENU_NAME, label=MENU_LABEL, parent=gMainWindow, tearOff=True)

    cmds.menuItem(label="启动监听", command=lambda *a: _start())
    cmds.menuItem(label="停止监听", command=lambda *a: _stop())
    cmds.menuItem(label="重启监听", command=lambda *a: _restart())
    cmds.menuItem(divider=True)
    cmds.menuItem(label="查看监听状态", command=lambda *a: _status())

    return main_menu


def delete_menu():
    """删除已存在的菜单。"""
    if cmds.menu(MENU_NAME, q=True, exists=True):
        cmds.deleteUI(MENU_NAME)


def _start():
    _ok, msg = _service().start()
    print("[MayaMCP]", msg)


def _stop():
    _ok, msg = _service().stop()
    print("[MayaMCP]", msg)


def _restart():
    _ok, msg = _service().restart()
    print("[MayaMCP]", msg)


def _status():
    svc = _service()
    running = svc.is_running()
    state = "监听中" if running else "未启动"
    cmds.confirmDialog(title="Maya MCP",
                       message=f"监听地址: {svc.host()}:{svc.port()}\n状态: {state}",
                       button=["OK"])

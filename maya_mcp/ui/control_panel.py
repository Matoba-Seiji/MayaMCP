#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Rigging MCP 简易状态控制面板。

显示监听端口状态，提供一键启动/停止/重启监听。
兼容 PySide2 / PySide6。
"""

import os
import sys
import time
import importlib.util
import traceback


try:
    from PySide6 import QtWidgets, QtCore
    import shiboken6 as shiboken
except ImportError:
    from PySide2 import QtWidgets, QtCore
    import shiboken2 as shiboken

import maya.OpenMayaUI as omui

WINDOW_OBJECT_NAME = "RiggingMCPControlPanel"
WINDOW_TITLE = "Rigging MCP 控制面板"


def _load_sibling(name):
    """按文件路径加载同目录模块，避免包名冲突。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name + ".py")
    spec = importlib.util.spec_from_file_location("riggingmcp_" + name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


service = _load_sibling("service")


def _project_root():
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _load_rigging_tool(module_name, function_name):
    root = _project_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    path = os.path.join(root, "maya_mcp", "maya_tools", "rigging", module_name + ".py")
    spec = importlib.util.spec_from_file_location("riggingmcp_tool_" + module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, function_name)


def _load_rigging_core(module_name, class_name):
    root = _project_root()
    if root not in sys.path:
        sys.path.insert(0, root)
    path = os.path.join(root, "maya_mcp", "maya_tools", "rigging", module_name + ".py")
    spec = importlib.util.spec_from_file_location("riggingmcp_core_" + module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)


def _maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    if ptr:
        return shiboken.wrapInstance(int(ptr), QtWidgets.QWidget)
    return None


class RiggingMCPPanel(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super(RiggingMCPPanel, self).__init__(parent or _maya_main_window())
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(520, 420)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Rigging MCP")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # 状态区
        status_box = QtWidgets.QGroupBox("监听服务状态")
        status_layout = QtWidgets.QGridLayout(status_box)
        status_layout.addWidget(QtWidgets.QLabel(f"监听地址 {service.host()}:{service.port()}"), 0, 0)
        self.indicator = QtWidgets.QLabel("● 检测中...")
        self.indicator.setStyleSheet("font-weight: bold;")
        status_layout.addWidget(self.indicator, 0, 1)
        layout.addWidget(status_box)

        # 按钮区
        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("启动监听")
        self.btn_stop = QtWidgets.QPushButton("停止监听")
        self.btn_restart = QtWidgets.QPushButton("重启监听")
        self.btn_refresh = QtWidgets.QPushButton("刷新")
        for b in (self.btn_start, self.btn_stop, self.btn_restart, self.btn_refresh):
            btn_layout.addWidget(b)
        layout.addLayout(btn_layout)

        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_restart.clicked.connect(self._on_restart)
        self.btn_refresh.clicked.connect(self.update_status)

        # 绑定模块占位 UI
        module_box = QtWidgets.QGroupBox("绑定模块")
        module_layout = QtWidgets.QGridLayout(module_box)

        module_layout.addWidget(QtWidgets.QLabel("生成控制器:"), 0, 0)
        self.adv_radio = QtWidgets.QRadioButton("ADV")
        self.hik_radio = QtWidgets.QRadioButton("HIK")
        self.adv_radio.setChecked(True)
        self.controller_type_group = QtWidgets.QButtonGroup(self)
        self.controller_type_group.addButton(self.adv_radio)
        self.controller_type_group.addButton(self.hik_radio)
        module_layout.addWidget(self.adv_radio, 0, 1)
        module_layout.addWidget(self.hik_radio, 0, 2)

        self.generate_controller_btn = QtWidgets.QPushButton("生成控制器")
        self.generate_controller_btn.setToolTip("按当前选择生成 ADV 或 HIK 控制器")
        self.generate_controller_btn.clicked.connect(self._on_generate_controller)
        module_layout.addWidget(self.generate_controller_btn, 0, 3)

        self.delete_controller_btn = QtWidgets.QPushButton("删除控制器")
        self.delete_controller_btn.setToolTip("删除当前场景中的 ADV 或 HIK 控制器")
        self.delete_controller_btn.clicked.connect(self._on_delete_controller)
        module_layout.addWidget(self.delete_controller_btn, 0, 4)
        layout.addWidget(module_box)

        # 日志
        self.console = QtWidgets.QPlainTextEdit()
        self.console.setReadOnly(True)
        self.console.setStyleSheet("font-family: Consolas, monospace; font-size: 14px;")
        layout.addWidget(self.console, 1)

        # 定时刷新状态
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(2000)
        self.timer.timeout.connect(self.update_status)
        self.timer.start()

        self.log("控制面板已就绪。")
        self.update_status()

    def log(self, text):
        self.console.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {text}")

    def update_status(self):
        running = service.is_running()
        if running:
            self.indicator.setText("● 监听中")
            self.indicator.setStyleSheet("color: #16a34a; font-weight: bold;")
        else:
            self.indicator.setText("● 未启动")
            self.indicator.setStyleSheet("color: #dc2626; font-weight: bold;")
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def _on_start(self):
        ok, msg = service.start()
        self.log(msg)
        self.update_status()

    def _on_stop(self):
        ok, msg = service.stop()
        self.log(msg)
        self.update_status()

    def _on_restart(self):
        ok, msg = service.restart()
        self.log(msg)
        self.update_status()

    def _set_controller_buttons_enabled(self, enabled):
        self.generate_controller_btn.setEnabled(enabled)
        self.delete_controller_btn.setEnabled(enabled)

    def _wait_cursor(self):
        wait_cursor = getattr(QtCore.Qt, "WaitCursor", None)
        if wait_cursor is None:
            wait_cursor = QtCore.Qt.CursorShape.WaitCursor
        return wait_cursor

    def _on_generate_controller(self):
        controller_type = "ADV" if self.adv_radio.isChecked() else "HIK"
        self._set_controller_buttons_enabled(False)
        QtWidgets.QApplication.setOverrideCursor(self._wait_cursor())
        try:
            self.log("开始生成 {0} 控制器...".format(controller_type))
            QtWidgets.QApplication.processEvents()
            if controller_type == "ADV":
                func = _load_rigging_tool("build_adv_controller", "build_adv_controller")
                result = func(generate_root=False)
            else:
                func = _load_rigging_tool("build_hik_controller", "build_hik_controller")
                result = func()
            self._handle_generate_result(controller_type, result)
        except Exception as exc:
            self.log("生成 {0} 控制器失败: {1}".format(controller_type, exc))
            self.log(traceback.format_exc())
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._set_controller_buttons_enabled(True)

    def _on_delete_controller(self):
        controller_type = "ADV" if self.adv_radio.isChecked() else "HIK"
        self._set_controller_buttons_enabled(False)
        QtWidgets.QApplication.setOverrideCursor(self._wait_cursor())
        try:
            self.log("开始删除 {0} 控制器...".format(controller_type))
            QtWidgets.QApplication.processEvents()
            if controller_type == "ADV":
                cls = _load_rigging_core("__fbx_to_adv_core", "FbxToADV")
                builder = cls()
                builder.delete_controller()
                summary = self._adv_delete_summary()
            else:
                cls = _load_rigging_core("__fbx_to_hik_core", "FbxToHIK")
                builder = cls()
                builder.delete_controller()
                summary = self._hik_delete_summary(builder.character_name)
            self.log("删除 {0} 控制器完成: {1}".format(controller_type, summary))
        except Exception as exc:
            self.log("删除 {0} 控制器失败: {1}".format(controller_type, exc))
            self.log(traceback.format_exc())
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._set_controller_buttons_enabled(True)

    @staticmethod
    def _adv_delete_summary():
        import maya.cmds as cmds
        names = ("FitSkeleton", "DeformationSystem", "MotionSystem", "ControlSet", "AllSet")
        return {name: cmds.objExists(name) for name in names}

    @staticmethod
    def _hik_delete_summary(character_name):
        import maya.cmds as cmds
        return {"character_name": character_name, "character_exists": cmds.objExists(character_name)}

    def _handle_generate_result(self, controller_type, result):
        success = bool(result.get("success")) if isinstance(result, dict) else False
        message = result.get("message", "") if isinstance(result, dict) else str(result)
        summary = result.get("created_summary", {}) if isinstance(result, dict) else {}
        prefix = "成功" if success else "失败"
        self.log("生成 {0} 控制器{1}: {2}".format(
            controller_type, prefix, message or "无返回信息"))
        if summary:
            self.log("结果: {0}".format(summary))



_instance = None


def show_window():
    """单例显示控制面板。"""
    global _instance
    if _instance is not None:
        try:
            _instance.show()
            _instance.raise_()
            _instance.activateWindow()
            return _instance
        except RuntimeError:
            _instance = None
    _instance = RiggingMCPPanel()
    _instance.show()
    return _instance

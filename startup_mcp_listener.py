# -*- coding: utf-8 -*-
"""Maya MCP 启动脚本。

在 Maya 中加载本文件即可启动 Socket 监听服务（默认 127.0.0.1:50011）。

三种用法均可:
1. Script Editor 的 Python 标签中执行:
    exec(open(r"C:/Users/yanchaofeng/Documents/GitHub/MayaMCP/startup_mcp_listener.py", encoding="utf-8").read())
2. 直接把本文件拖入 Maya 视口（拖拽执行，会调用 onMayaDroppedPythonFile）。
3. 在 userSetup.py 中导入本目录并调用，实现 Maya 启动时自动监听。

停止监听:
    stop_mcp_server()
"""

import os
import sys

# 工程根目录回退路径（exec(open().read()) 方式下 __file__ 不存在时使用）
_FALLBACK_ROOT = r"C:/Users/yanchaofeng/Documents/GitHub/MayaRiggingMCP"


def _resolve_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return _FALLBACK_ROOT


def _start():
    """启动监听服务（幂等，已运行则跳过）。"""
    this_dir = _resolve_root()
    listener_dir = os.path.join(this_dir, "maya_mcp", "connector")
    listener_file = os.path.join(listener_dir, "maya_server_listener.py")
    if not os.path.isfile(listener_file):
        raise RuntimeError(f"找不到监听脚本: {listener_file}")

    if listener_dir not in sys.path:
        sys.path.append(listener_dir)

    print(f"[MayaMCP] 正在启动监听脚本: {listener_file}")
    with open(listener_file, "r", encoding="utf-8") as f:
        code = f.read()
    # 在本模块全局命名空间执行，使 start_mcp_server / stop_mcp_server 可直接调用
    exec(compile(code, listener_file, "exec"), globals())


def onMayaDroppedPythonFile(*args, **kwargs):
    """Maya 拖拽执行 .py 时的回调入口（拖入视口时由 Maya 调用）。"""
    _start()


# import / exec(open().read()) 方式下，加载即启动
_start()

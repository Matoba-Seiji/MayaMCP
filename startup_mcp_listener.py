# -*- coding: utf-8 -*-
"""Start the Maya-side socket listener."""

import os
import sys

def _resolve_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        root = os.environ.get("MAYAMCP_ROOT")
        if root:
            return os.path.abspath(root)
        raise RuntimeError(
            "无法确定 MayaMCP 根目录；请设置 MAYAMCP_ROOT，或从 startup_mcp_listener.py 文件加载。"
        )


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

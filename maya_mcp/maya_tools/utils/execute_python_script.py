#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 在 Maya 中执行任意 Python 脚本


def execute_python_script(code: str) -> dict:
    """在 Maya 主线程中执行任意 Python 代码（已自动 import maya.cmds as cmds）。

    可将需要返回的内容赋值给变量 `result`，会随返回值带回。

    Args:
        code: 要执行的 Python 代码字符串。

    Returns:
        dict: success / result(str) / output(str) / message。

    示例调用:
        execute_python_script(code="result = cmds.ls(type='mesh')")
        execute_python_script(code="cmds.polyCube(); result = len(cmds.ls(geometry=True))")
    """
    import maya.cmds as cmds
    import io
    import contextlib
    import traceback

    try:
        ns = {"cmds": cmds}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            exec(code, ns)
        result = ns.get("result", None)
        return {
            "success": True,
            "result": None if result is None else (result if isinstance(result, (str, int, float, bool, list, dict)) else str(result)),
            "output": buf.getvalue(),
            "message": "Python 脚本执行成功。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"执行 Python 脚本失败: {str(e)}", "traceback": traceback.format_exc()}

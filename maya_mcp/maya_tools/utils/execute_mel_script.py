#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 在 Maya 中执行 MEL 脚本


def execute_mel_script(code: str) -> dict:
    """在 Maya 中执行 MEL 命令字符串并返回结果。

    Args:
        code: 要执行的 MEL 代码字符串。

    Returns:
        dict: success / result / message。

    示例调用:
        execute_mel_script(code="polyCube -w 2 -h 2 -d 2;")
        execute_mel_script(code="ls -type \"mesh\";")
    """
    import maya.mel as mel
    import traceback

    try:
        result = mel.eval(code)
        return {
            "success": True,
            "result": result if isinstance(result, (str, int, float, bool, list)) or result is None else str(result),
            "message": "MEL 脚本执行成功。",
        }
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"执行 MEL 脚本失败: {str(e)}", "traceback": traceback.format_exc()}

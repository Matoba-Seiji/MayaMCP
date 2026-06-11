#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Usage : MCP Tool - 打开 Maya 场景文件


def open_scene(file_path: str, force: bool = True) -> dict:
    """打开指定的 Maya 场景文件（.ma/.mb）。

    Args:
        file_path: 场景文件完整路径。
        force: 是否强制打开（不提示保存当前修改）。默认 True。

    Returns:
        dict: success / file_path / message。

    示例调用:
        open_scene(file_path="D:/scenes/test.mb")
    """
    import maya.cmds as cmds
    import os
    import traceback

    try:
        if not os.path.isfile(file_path):
            return {"success": False, "message": f"文件不存在: {file_path}"}
        cmds.file(file_path, open=True, force=bool(force))
        return {"success": True, "file_path": file_path, "message": f"已打开场景: {file_path}"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "message": f"打开场景失败: {str(e)}", "traceback": traceback.format_exc()}
